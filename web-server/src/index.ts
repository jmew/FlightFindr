import express from 'express';
import cors from 'cors';
import { chatHandler } from './api/chatHandler.js';
import { suggestionHandler } from './api/suggestionHandler.js';
import { multiCityHandler } from './api/multiCityHandler.js';
import { cancelHandler } from './api/cancelHandler.js';

async function main() {
  const app = express();
  const port = process.env.PORT || 3000;

  app.use(cors());
  app.use(express.json());

  if (!process.env['GEMINI_API_KEY']) {
    throw new Error(
      'The GEMINI_API_KEY environment variable is not set. Please set it to your API key.',
    );
  }

  app.get('/chat', chatHandler);
  app.post('/multi-city', multiCityHandler);
  app.get('/suggestions', suggestionHandler);
  app.get('/api/cancel', cancelHandler);

  // Add a health check route for Render
  app.get('/', (req, res) => {
    res.status(200).send('OK');
  });

  return new Promise<void>((resolve, reject) => {
    const server = app
      .listen(port, () => {
        console.log(`Server is listening on port ${port}`);
      })
      .on('error', (err) => {
        reject(err);
      });
    // Set a 5-minute timeout for all incoming requests.
    server.setTimeout(300000);
  });
}

main().catch((error) => {
  console.error('Failed to initialize and start the server:', error);
  process.exit(1);
});
