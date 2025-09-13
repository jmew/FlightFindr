import type { Request, Response } from 'express';
import { getOrCreateClient } from '../services/sessionManager.js';
import { streamGeminiResponse, sendSseMessage } from '../utils/gemini-streamer.js';

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

  const authHeader = req.headers.authorization;
  const isDevMode = process.env.NODE_ENV !== 'production';
  
  // In production, we require an auth token. In dev, it's optional.
  if (!isDevMode && (!authHeader || !authHeader.startsWith('Bearer '))) {
    res.status(401).json({ error: 'Unauthorized: Missing bearer token.' });
    return;
  }

  const encodedToken = authHeader?.split(' ')[1];
  let authToken: string | undefined;
  if (encodedToken) {
    authToken = Buffer.from(encodedToken, 'base64').toString('utf8');
  }

  try {
    const clientData = await getOrCreateClient(sessionId, authToken);
    if (!clientData) {
      res.status(401).json({ error: 'Unauthorized: Invalid token.' });
      return;
    }

    const { config, client, abortController } = clientData;
    const message = req.query['message'] as string;
    if (!message) {
      res.status(400).json({ error: 'Message is required.' });
      return;
    }

    req.on('close', () => {
      console.log(
        `Client disconnected for session: ${sessionId}, aborting request.`,
      );
      abortController.abort();
    });

    await streamGeminiResponse(res, client, config, [{ text: message }], abortController! );
    res.end();

  } catch (error) {
    console.error('Error processing chat message:', error);
    const errorMessage =
      error instanceof Error ? error.message : 'An unknown error occurred.';
    sendSseMessage(res, 'error', { error: errorMessage });
    res.end();
  }
}