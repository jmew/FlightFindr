/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { OAuth2Client } from 'google-auth-library';
import * as http from 'http';
import * as url from 'url';
import * as path from 'path';
import { promises as fs } from 'fs';
import open from 'open';

const OAUTH_CLIENT_ID =
  '304334704110-1cs4bm3etic6t9ahtg79inthpva80brn.apps.googleusercontent.com';
const OAUTH_CLIENT_SECRET = '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';
const OAUTH_SCOPE = [
  'https://www.googleapis.com/auth/cloud-platform',
  'https://www.googleapis.com/auth/userinfo.email',
  'https://www.googleapis.com/auth/userinfo.profile',
];

const homeDir = process.env.HOME || process.env.USERPROFILE;
const OAUTH_CREDS_PATH = path.join(homeDir!, '.config', 'gcloud', 'gemini-credentials.json');


const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://localhost:3000';

export function getOAuthClient() {
  return new OAuth2Client({
    clientId: OAUTH_CLIENT_ID,
    clientSecret: OAUTH_CLIENT_SECRET,
  });
}

export function startLogin(): string {
    const client = getOAuthClient();
    // This URI must match the one registered in Google Cloud Console and the one in our callback route.
    const redirectUri = `${BACKEND_BASE_URL}/auth/google/callback`;

    const authUrl = client.generateAuthUrl({
        redirect_uri: redirectUri,
        access_type: 'offline',
        scope: OAUTH_SCOPE,
        response_type: 'code',
    });

    return authUrl;
}

export async function exchangeCodeForToken(code: string): Promise<any> {
    const client = getOAuthClient();
    const redirectUri = `${BACKEND_BASE_URL}/auth/google/callback`;
    const { tokens } = await client.getToken({
        code,
        redirect_uri: redirectUri,
    });

    return tokens;
}

export async function verifyToken(accessToken: string): Promise<boolean> {
    try {
        const response = await fetch(`https://www.googleapis.com/oauth2/v3/tokeninfo?access_token=${accessToken}`);
        if (!response.ok) {
            return false;
        }
        const data = await response.json();
        // Ensure the token is active and for our client ID
        return data.aud === OAUTH_CLIENT_ID && data.expires_in > 0;
    } catch (error) {
        console.error('Token verification failed:', error);
        return false;
    }
}

export async function getStoredToken() {
    try {
        const creds = await fs.readFile(OAUTH_CREDS_PATH, 'utf-8');
        return JSON.parse(creds);
    } catch (e) {
        return null;
    }
}
