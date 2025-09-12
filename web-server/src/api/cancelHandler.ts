import type { Request, Response } from 'express';

// The cancellation logic is now handled within each request handler (e.g., chatHandler)
// by listening to the request's 'close' event. This endpoint is no longer needed.
export async function cancelHandler(req: Request, res: Response) {
  res.status(410).json({ message: 'This endpoint is deprecated and no longer functional.' });
}