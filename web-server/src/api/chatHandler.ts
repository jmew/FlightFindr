import type { Request, Response } from 'express';
import { getOrCreateClient } from '../services/sessionManager.js';
import { streamGeminiResponse } from '../utils/gemini-streamer.js';

export async function chatHandler(req: Request, res: Response) {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const sessionId = req.query['sessionId'] as string;
  if (!sessionId) {
    res.status(400).json({ error: 'sessionId is required.' });
    return;
  }

  try {
    const { config, client } = await getOrCreateClient(sessionId);
    const message = req.query['message'] as string;
    if (!message) {
      res.status(400).json({ error: 'Message is required.' });
      return;
    }

    const abortController = new AbortController();
    req.on('close', () => {
      console.log(
        `Client disconnected for session: ${sessionId}, aborting request.`,
      );
      abortController.abort();
    });

    await streamGeminiResponse(res, client, config, [{ text: message }], abortController);

  } catch (error) {
    console.error('Error processing chat message:', error);
    const errorMessage =
      error instanceof Error ? error.message : 'An unknown error occurred.';
    res.status(500).json({ error: errorMessage });
  }
}