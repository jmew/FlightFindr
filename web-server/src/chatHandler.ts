import type { Request, Response } from 'express';
import type { Part } from '@google/genai';
import {
  GeminiEventType,
  executeToolCall,
  type ToolCallRequestInfo,
} from '@google/gemini-cli-core';
import { getOrCreateClient } from './sessionManager.js';

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

export async function chatHandler(req: Request, res: Response) {
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
    const message = req.query['message'] as string;
    if (!message) {
      sendSseMessage(res, 'error', { error: 'Message is required.' });
      res.end();
      return;
    }

    const today = new Date().toLocaleDateString('en-CA');
    const messageWithDate = `Today's date is ${today}. ${message}`;

    let currentParts: Part[] = [{ text: messageWithDate }];
    const abortController = new AbortController();

    req.on('close', () => {
      console.log(
        `Client disconnected for session: ${sessionId}, aborting request.`, 
      );
      abortController.abort();
    });

    let turnCount = 0;
    const maxTurns = 10;

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
        for (const requestInfo of toolCallRequests) {
          const toolResponse = await executeToolCall(
            config,
            requestInfo,
            abortController.signal,
          );
          console.log('Tool response:', JSON.stringify(toolResponse, null, 2));
          if (toolResponse?.responseParts) {
            toolResponseParts.push(toolResponse.responseParts);
          }
          sendSseMessage(res, 'tool_result', {
            callId: requestInfo.callId,
            name: requestInfo.name,
            result: toolResponse.resultDisplay,
            error: toolResponse.error?.message,
          });
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
    console.error('Error processing chat message:', error);
    const errorMessage =
      error instanceof Error ? error.message : 'An unknown error occurred.';
    sendSseMessage(res, 'error', { error: errorMessage });
    res.end();
  }
}
