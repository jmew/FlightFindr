import type { Response } from 'express';
import type { Part } from '@google/genai';
import {
  GeminiEventType,
  executeToolCall,
  type ToolCallRequestInfo,
  type Config,
} from '@google/gemini-cli-core';

// Helper to format and send SSE messages
export const sendSseMessage = (
  res: Response,
  event: string,
  data: Record<string, unknown> | string,
) => {
  const payload = typeof data === 'string' ? data : JSON.stringify(data);
  res.write(`event: ${event}\n`);
  res.write(`data: ${payload}\n\n`);
};

export async function streamGeminiResponse(
  res: Response,
  client: ReturnType<Config['getGeminiClient']>, 
  config: Config,
  initialParts: Part[],
  abortController: AbortController
) {
  let currentParts = initialParts;
  let turnCount = 0;
  const maxTurns = 15;

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
}
