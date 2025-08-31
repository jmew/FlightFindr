import {
  AuthType,
  Config,
  type ConfigParameters,
  DEFAULT_GEMINI_FLASH_MODEL,
  DEFAULT_GEMINI_EMBEDDING_MODEL,
  ApprovalMode,
} from '@google/gemini-cli-core';

type GeminiClient = ReturnType<Config['getGeminiClient']>;
const sessions = new Map<string, { config: Config; client: GeminiClient }>();

export async function getOrCreateClient(sessionId: string) {
  if (sessions.has(sessionId)) {
    console.log(`Reusing Gemini client for session: ${sessionId}`);
    return sessions.get(sessionId)!;
  }

  console.log(`Initializing Gemini client for session: ${sessionId}`);

  const configParams: ConfigParameters = {
    sessionId,
    model: DEFAULT_GEMINI_FLASH_MODEL,
    embeddingModel: DEFAULT_GEMINI_EMBEDDING_MODEL,
    targetDir: process.cwd(),
    cwd: process.cwd(),
    debugMode: false,
    approvalMode: ApprovalMode.YOLO,
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
      'the-point-finder': {
        httpUrl: 'http://localhost:9999/mcp',
        timeout: 160000,
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
