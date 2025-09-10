import type { Request, Response } from 'express';
import { getSession } from '../services/sessionManager.js';

export async function cancelHandler(req: Request, res: Response) {
  const sessionId = req.query['sessionId'] as string;
  if (!sessionId) {
    return res.status(400).json({ error: 'sessionId is required.' });
  }

  const session = getSession(sessionId);
  if (session?.abortController) {
    console.log(`Cancellation requested for session: ${sessionId}`);
    session.abortController.abort();
    res.status(200).json({ message: 'Cancellation requested.' });
  } else {
    res.status(404).json({ error: 'Session not found or not in a cancellable state.' });
  }
}
