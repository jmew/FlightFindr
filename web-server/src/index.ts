import express from 'express';
import cors from 'cors';
import { chatHandler } from './api/chatHandler.js';
import { suggestionHandler } from './api/suggestionHandler.js';
import { multiCityHandler } from './api/multiCityHandler.js';
import { cancelHandler } from './api/cancelHandler.js';
import { startLogin, exchangeCodeForToken } from './services/authService.js';

async function main() {
  const app = express();
  const port = process.env.PORT || 3000;

  app.use(cors());
  app.use(express.json());

  // This check is important for the default API Key flow
  if (!process.env['GEMINI_API_KEY']) {
    console.warn(
      'The GEMINI_API_KEY environment variable is not set. Users will be required to log in.',
    );
  }

  // --- API Routes ---
  app.get('/chat', chatHandler);
  app.post('/multi-city', multiCityHandler);
  app.get('/suggestions', suggestionHandler);

  // --- Auth Routes ---
  app.get('/auth/google', (req, res) => {
      try {
          const authUrl = startLogin();
          res.redirect(authUrl);
      } catch (error) { 
          console.error('Error starting login flow:', error);
          res.status(500).send('Authentication failed to initiate.');
      }
  });

  app.get('/auth/google/callback', async (req, res) => {
      const code = req.query.code as string;
      if (!code) {
          return res.status(400).send('Missing authorization code.');
      }
      try {
          const tokens = await exchangeCodeForToken(code);
          // Send back a script to the popup window to pass the token to the parent
          res.send(`
              <script>
                  window.opener.postMessage(${JSON.stringify(tokens)}, 'http://localhost:5173');
                  window.close();
              </script>
          `);
      } catch (error) {
          console.error('Error exchanging code for token:', error);
          res.status(500).send('Failed to exchange authorization code for a token.');
      }
  });

  // Add a health check route
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