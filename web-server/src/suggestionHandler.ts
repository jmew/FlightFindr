import type { Request, Response } from 'express';

export async function suggestionHandler(req: Request, res: Response) {
  return res.json({ suggestions: [] });
}