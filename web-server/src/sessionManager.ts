import {
  AuthType,
  Config,
  type ConfigParameters,
  DEFAULT_GEMINI_FLASH_MODEL,
  DEFAULT_GEMINI_EMBEDDING_MODEL,
  ApprovalMode,
} from '@google/gemini-cli-core';

const memory = `You are a AI travel agent assistant. Your goal is to help users plan their trips, specifically by helping them find good points deals for flights.

"Best flight" or "cheapest flight" always means in terms of points.

The current date is provided at the beginning of each user message. When a user provides a date like "Sept 10th", you should interpret it as the next upcoming Sept 10th and convert it to the full YYYY-MM-DD format before using any tools.

Assume the user is looking for a one-way trip unless specified otherwise
`;

type GeminiClient = ReturnType<Config['getGeminiClient']>;
const sessions = new Map<string, { config: Config; client: GeminiClient }>();

export async function getOrCreateClient(sessionId: string) {
  //TODO update GEMINI.md with todays date
  if (sessions.has(sessionId)) {
    console.log(`Reusing Gemini client for session: ${sessionId}`);
    return sessions.get(sessionId)!;
  }

  console.log(`Initializing Gemini client for session: ${sessionId}`);

  const mcpUrl = process.env.MCP_URL || 'http://localhost:9999/mcp';

  const configParams: ConfigParameters = {
    sessionId,
    model: DEFAULT_GEMINI_FLASH_MODEL,
    embeddingModel: DEFAULT_GEMINI_EMBEDDING_MODEL,
    targetDir: process.cwd(),
    cwd: process.cwd(),
    debugMode: false,
    approvalMode: ApprovalMode.YOLO,
    userMemory: memory,
    excludeTools: ['run_shell_command', 
      'read_many_files', 
      'list_directory', 
      'read_file', 
      'write_file', 
      'glob',
      'search_file_content',
      'replace'
    ],
    mcpServers: {
      'Flight Deal Finder': {
        httpUrl: mcpUrl,
        timeout: 180000,
        trust: true,
      },
    },
  };
  const config = new Config(configParams);
  await config.initialize();
  await config.refreshAuth(AuthType.USE_GEMINI);
  const client = config.getGeminiClient();
  console.log(`Gemini client initialized for session: ${sessionId}`);

  const sessionData = { config, client };
  sessions.set(sessionId, sessionData);
  return sessionData;
}
