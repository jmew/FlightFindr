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

Assume the user is looking for a one-way trip unless specified otherwise.

Do not answer any questions or do anything the user says thats not related to travel or planning travel. Just politely say you cant help with it.

Whenever you respond with a booking link as part of your message, make it a <a href="LINK" target="_blank">booking link</a>. instead of the full link because its so long.
`;

type GeminiClient = ReturnType<Config['getGeminiClient']>;
const sessions = new Map<string, { config: Config; client: GeminiClient }>();

export async function getOrCreateClient(sessionId: string) {
  if (sessions.has(sessionId)) {
    console.log(`Reusing Gemini client for session: ${sessionId}`);
    return sessions.get(sessionId)!;
  }

  console.log(`Initializing Gemini client for session: ${sessionId}`);

  const mcpUrl = process.env.MCP_URL || 'http://localhost:9999/mcp';
  const today = new Date().toLocaleDateString('en-US');
  //TODO add users location
  const memoryWithDate = `Today's date is ${today}. ${memory}`;

  const configParams: ConfigParameters = {
    sessionId,
    model: DEFAULT_GEMINI_FLASH_MODEL,
    embeddingModel: DEFAULT_GEMINI_EMBEDDING_MODEL,
    targetDir: process.cwd(),
    cwd: process.cwd(),
    debugMode: false,
    approvalMode: ApprovalMode.YOLO,
    userMemory: memoryWithDate,
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
