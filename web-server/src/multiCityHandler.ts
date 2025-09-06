import type { Request, Response } from 'express';
import { getOrCreateClient } from './sessionManager.js';
import type { Part } from '@google/genai';
import {
  GeminiEventType,
  executeToolCall,
  type ToolCallRequestInfo,
} from '@google/gemini-cli-core';

// Helper to format and send SSE messages
const sendSseMessage = (
  res: Response,
  event: string,
  data: Record<string, unknown> | string,
) => {
  const payload = typeof data === 'string' ? data : JSON.stringify(data);
  res.write(`event: ${event}\n`);
  res.write(`data: ${payload}\n\n`);
};

export async function multiCityHandler(req: Request, res: Response) {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const sessionId = req.query['sessionId'] as string;
  if (!sessionId) {
    sendSseMessage(res, 'error', { error: 'sessionId is required.' });
    res.end();
    return;
  }

  const { config, client } = await getOrCreateClient(sessionId);

  try {
    // Construct a natural language message from the form data
    const { startLocation, endLocation, intermediateStops, startDate, endDate, maxLength, constraints, flexible } = req.body;
    let message = `Find a multi-city trip for me. I want to start in ${startLocation} and end in ${endLocation}.`;
    if (intermediateStops && intermediateStops.length > 0 && intermediateStops[0] !== '') {
      message += ` I want to visit the following places: ${intermediateStops.join(', ')}.`;
    }
    message += ` I want to travel between ${startDate} and ${endDate}`;
    if (maxLength) {
        message += `, with a maximum trip length of ${maxLength} days`;
    }
    message += ".\n";

    if (flexible) {
      message += ` The order of the intermediate stops is flexible, so please find the best route.\n`;
    }
    if (constraints) {
      message += ` Please also consider the following constraints: ${constraints}`;
    }

    let currentParts: Part[] = [{ text: message }];
    const abortController = new AbortController();

    req.on('close', () => {
      abortController.abort();
    });

    let turnCount = 0;
    const maxTurns = 15; // Increased max turns for complex multi-leg searches

    while (turnCount < maxTurns) {
      turnCount++;
      const responseStream = client.sendMessageStream(
        currentParts,
        abortController.signal,
        `prompt-id-from-web-${turnCount}`,
      );

      const toolCallRequests: ToolCallRequestInfo[] = [];
      let fullResponse = '';

      for await (const event of responseStream) {
        switch (event.type) {
          case GeminiEventType.Thought:
            sendSseMessage(res, 'thought', event.value);
            break;
          case GeminiEventType.Content:
            fullResponse += event.value;
            sendSseMessage(res, 'content', { chunk: event.value });
            break;
          case GeminiEventType.ToolCallRequest:
            toolCallRequests.push(event.value);
            sendSseMessage(res, 'tool_code', {
              callId: event.value.callId,
              name: event.value.name,
              args: event.value.args,
            });
            break;
        }
      }

      if (toolCallRequests.length > 0) {
        const toolResponseParts: Part[] = [];
        const keepAliveInterval = setInterval(() => {
          res.write(': keep-alive\n\n');
        }, 15000);

        try {
          for (const requestInfo of toolCallRequests) {
            const toolResponse = await executeToolCall(
              config,
              requestInfo,
              abortController.signal,
            );
            if (toolResponse?.responseParts) {
              toolResponseParts.push(toolResponse.responseParts as any);
            }
            sendSseMessage(res, 'tool_result', {
              callId: requestInfo.callId,
              name: requestInfo.name,
              result: toolResponse.resultDisplay,
              error: toolResponse.error?.message,
            });
          }
        } finally {
          clearInterval(keepAliveInterval);
        }

        currentParts = toolResponseParts;
        continue;
      } else {
        sendSseMessage(res, 'end', { finalResponse: fullResponse });
        res.end();
        return;
      }
    }
    sendSseMessage(res, 'error', {
      error: 'Reached maximum conversation turns.',
    });
    res.end();
  } catch (error) {
    console.error('Error processing multi-city request:', error);
    const errorMessage =
      error instanceof Error ? error.message : 'An unknown error occurred.';
    sendSseMessage(res, 'error', { error: errorMessage });
    res.end();
  }
}