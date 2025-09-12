import type { Request, Response } from 'express';
import { getOrCreateClient } from '../services/sessionManager.js';
import { streamGeminiResponse, sendSseMessage } from '../utils/gemini-streamer.js';

export async function multiCityHandler(req: Request, res: Response) {
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
    const { config, client, abortController } = await getOrCreateClient(sessionId);
    sendSseMessage(res, 'thought', {
      subject: 'Building your multi-city trip...', 
    });
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

    req.on('close', () => {
      abortController!.abort();
    });

    await streamGeminiResponse(res, client, config, [{ text: message }], abortController!);

  } catch (error) {
    console.error('Error processing multi-city request:', error);
    const errorMessage =
      error instanceof Error ? error.message : 'An unknown error occurred.';
    
    if (errorMessage.includes('terminated')) {
        sendSseMessage(res, 'error', { error: 'The request timed out while processing the flight results. The session has been reset. Please try your search again.' });
    } else {
        sendSseMessage(res, 'error', { error: errorMessage });
    }
  } finally {
    res.end();
  }
}