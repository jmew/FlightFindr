import {
  AuthType,
  Config,
  type ConfigParameters,
  DEFAULT_GEMINI_MODEL,
  ApprovalMode,
} from '@google/gemini-cli-core';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

type GeminiClient = ReturnType<Config['getGeminiClient']>;
const sessions = new Map<string, { 
  config: Config; 
  client: GeminiClient; 
  abortController: AbortController | null; 
}>();

export function getSession(sessionId: string) {
  return sessions.get(sessionId);
}

export function deleteSession(sessionId: string) {
  console.log(`Deleting session: ${sessionId}`);
  sessions.delete(sessionId);
}

export async function getOrCreateClient(sessionId: string) {
  if (sessions.has(sessionId)) {
    console.log(`Reusing Gemini client for session: ${sessionId}`);
    const session = sessions.get(sessionId)!;
    // Create a new abort controller for the new request, but keep the old config/client
    session.abortController = new AbortController();
    return session;
  }

  console.log(`Initializing Gemini client for session: ${sessionId}`);

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
    // Allow the model to use the search tool
    excludeTools: ['run_shell_command', 
      'read_many_files', 
      'list_directory', 
      'read_file', 
      'write_file', 
      'glob',
      'replace'
    ],
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
  await config.refreshAuth(AuthType.USE_GEMINI);
  const client = config.getGeminiClient();
  console.log(`Gemini client initialized for session: ${sessionId}`);

  const sessionData = { config, client, abortController: new AbortController() };
  sessions.set(sessionId, sessionData);
  return sessionData;
}