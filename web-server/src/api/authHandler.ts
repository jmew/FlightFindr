import { Router, Request, Response } from 'express';
import { startLogin, exchangeCodeForToken } from '../services/authService.js';

const router = Router();

const FRONTEND_BASE_URL = process.env.FRONTEND_BASE_URL || 'http://localhost:5173';

// Redirects the user to the Google OAuth consent screen.
router.get('/google', (req, res) => {
  const authUrl = startLogin();
  res.redirect(authUrl);
});

// Handles the callback from Google after the user has authenticated.
router.get('/google/callback', async (req: Request, res: Response) => {
  const code = req.query.code as string;

  if (!code) {
    return res.status(400).send('Missing authorization code.');
  }

  try {
    const tokens = await exchangeCodeForToken(code);

    // After successfully exchanging the code for tokens, send an HTML page
    // with a script to the popup window. This script will store the tokens
    // and then close the popup.
    res.send(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Authentication Successful</title>
        </head>
        <body>
          <script>
            // Send the tokens to the main window that opened the popup
            window.opener.postMessage({
              type: 'auth-success',
              tokens: ${JSON.stringify(tokens)}
            }, '${FRONTEND_BASE_URL}');

            // Close the popup window
            window.close();
          </script>
          <p>Authentication successful! You can close this window.</p>
        </body>
      </html>
    `);
  } catch (error) {
    console.error('Failed to exchange code for token:', error);
    res.status(500).send('Authentication failed.');
  }
});

export default router;
