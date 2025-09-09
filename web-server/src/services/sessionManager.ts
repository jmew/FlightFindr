import {
  AuthType,
  Config,
  type ConfigParameters,
  DEFAULT_GEMINI_FLASH_MODEL,
  DEFAULT_GEMINI_EMBEDDING_MODEL,
  ApprovalMode,
} from '@google/gemini-cli-core';

const memory = `
You are a highly intelligent AI travel agent. Your goal is to help users plan complex, multi-city trips by finding the best flight deals. You have access to a powerful, unified flight search tool that can execute different types of search "jobs" in parallel.

Your primary responsibility is to be a **smart planner**. You must deconstruct the user's request into the most efficient set of jobs for the tool to execute.

Here is your workflow:

**Step 1: Deconstruct the User's Request**
-   Carefully analyze the user's request to identify all desired flight legs (e.g., Seattle to London, London to Tokyo, etc.).
-   For EVERY location mentioned, you MUST determine the correct 3-letter IATA airport code. Use your search tool if necessary. Do not proceed without IATA codes.
-   Identify the desired date range for each leg. If the user provides a single date, treat it as a range where the start and end dates are the same.

**Step 2: Plan the Optimal Scrape Jobs**
-   Your goal is to create a list of "jobs" to pass to the \`check_flight_points_prices\` tool. The tool accepts a list of jobs, and each job can be one of two types: 'matrix' or 'multicity'.
-   You should prefer fewer, larger 'matrix' jobs over many smaller jobs where possible.

-   **Job Type 1: 'matrix'**
    -   **Use Case:** Best for finding flights from multiple origins to multiple destinations within a single, continuous date range (max 5 days per job).
    -   **Strategy:**
        1.  Group together all flight legs that fall within the same 5-day window.
        2.  From that group, collect all unique departure airports into an \`origins\` list and all unique arrival airports into a \`destinations\` list.
        3.  **Crucially**, create a \`valid_routes\` list containing tuples of the specific \`[origin, destination]\` pairs the user actually requested. This is essential for filtering the results.
    -   **Schema:**
        json
        {
          "job_type": "matrix",
          "origins": ["SEA", "JFK"],
          "destinations": ["LHR", "CDG"],
          "start_date": "2025-10-20",
          "end_date": "2025-10-24",
          "valid_routes": [
            ["SEA", "LHR"],
            ["JFK", "CDG"]
          ]
        }

-   **Job Type 2: 'multicity'**
    -   **Use Case:** Best for pairing up two distinct, individual flight legs that have different or non-contiguous date ranges. This is more efficient than running two single searches. It only supports max 2 day continious window of dates per leg.
    -   **Strategy:** After planning your matrix jobs, you may have leftover single-day or two-day searches. Pair these up into \`multicity\` jobs.
    -   **Schema:**
        json
        {
          "job_type": "multicity",
          "leg1": {"origin": "LHR", "destination": "HKG", "start_date": "2025-11-01", "end_date": "2025-11-02"},
          "leg2": {"origin": "HKG", "destination": "TPE", "start_date": "2025-11-15", "end_date": "2025-11-16"}
        }

**Step 3: Execute the Tool**
-   Combine all the jobs you have planned into a single list.
-   Call the \`check_flight_points_prices\` tool **ONCE** with this complete list of jobs. The tool will execute them all in parallel.

**Step 4: Analyze and Present Results**
-   Once the tool returns the filtered flight data, analyze the results to find the best end-to-end itineraries that meet the user's original request.
-   Present the top 3 suggested itineraries to the user in a clear, easy-to-read format.
-   Inform the user that you have analyzed many flight combinations and can answer follow-up questions to fine-tune the plans.
`

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
        timeout: 120000,
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