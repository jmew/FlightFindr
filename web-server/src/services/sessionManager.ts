import {
  Config,
  type ConfigParameters,
  DEFAULT_GEMINI_MODEL,
  ApprovalMode,
  AuthType,
  GeminiClient,
} from '@google/gemini-cli-core';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as crypto from 'crypto';
import { fileURLToPath } from 'url';

type GeminiSession = {
  config: Config;
  client: GeminiClient;
  abortController: AbortController | null;
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// We don't use a long-lived session map anymore for authenticated users
// to ensure credentials are never mixed up.

export async function getOrCreateClient(sessionId: string, authToken?: string): Promise<GeminiSession | null> {
  const isDevMode = process.env.NODE_ENV !== 'production';
  const useApiKey = isDevMode && !authToken;

  const systemPromptPath = path.join(__dirname, 'system_prompt.md');
  const memory = fs.readFileSync(systemPromptPath, 'utf-8');
  const mcpUrl = process.env.MCP_URL || 'http://localhost:9999/mcp';

  const configParams: ConfigParameters = {
    sessionId,
    model: DEFAULT_GEMINI_MODEL,
    targetDir: process.cwd(),
    cwd: process.cwd(),
    debugMode: false,
    approvalMode: ApprovalMode.YOLO,
    userMemory: memory,
    excludeTools: ['run_shell_command', 'read_many_files', 'list_directory', 'read_file', 'write_file', 'glob', 'replace'],
    mcpServers: {
      'Flight Deal Finder': {
        httpUrl: mcpUrl,
        timeout: 340000,
        trust: true,
      },
    },
  };

  const config = new Config(configParams);
  await config.initialize();

  if (useApiKey) {
    console.log('Using API Key for dev mode');
    await config.refreshAuth(AuthType.USE_GEMINI);
    const client = config.getGeminiClient();
    return { config, client, abortController: new AbortController() };
  }

  // --- Per-Request OAuth Flow ---
  if (!authToken) {
    return null; // Production requires a token
  }

  const tempCredPath = path.join(os.tmpdir(), `gemini-creds-${crypto.randomUUID()}.json`);
  let originalCredsEnv = process.env.GOOGLE_APPLICATION_CREDENTIALS;

  try {
    fs.writeFileSync(tempCredPath, authToken);
    process.env.GOOGLE_APPLICATION_CREDENTIALS = tempCredPath;

    // The library will now automatically pick up the temporary credential file.
    await config.refreshAuth(AuthType.LOGIN_WITH_GOOGLE);
    
    const client = config.getGeminiClient();
    return { config, client, abortController: new AbortController() };

  } catch (e) {
    console.error("Failed to create client with user's token", e);
    return null;
  } finally {
    // **Crucially, clean up the temporary file and restore the environment.**
    if (fs.existsSync(tempCredPath)) {
      fs.unlinkSync(tempCredPath);
    }
    process.env.GOOGLE_APPLICATION_CREDENTIALS = originalCredsEnv;
  }
}
