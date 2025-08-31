import express from 'express';
import cors from 'cors';
import { chatHandler } from './chatHandler.js';
import { suggestionHandler } from './suggestionHandler.js';

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
  app.get('/suggestions', suggestionHandler);

  // Add a health check route for Render
  app.get('/', (req, res) => {
    res.status(200).send('OK');
  });

  return new Promise<void>((resolve, reject) => {
    app
      .listen(port, () => {
        console.log(`Server is listening on port ${port}`);
      })
      .on('error', (err) => {
        reject(err);
      });
  });
}

main().catch((error) => {
  console.error('Failed to initialize and start the server:', error);
  process.exit(1);
});
