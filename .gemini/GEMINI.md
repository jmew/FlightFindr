### Project Overview

This is a full-stack application designed to find flight deals using points. It consists of three main services:
-   `web-frontend`: A React-based user interface.
-   `web-server`: A Node.js/Express backend that orchestrates calls to the Gemini API.
-   `flight-findr-mcp`: A Python-based MCP server that performs the actual web scraping.

### Development Workflow

To run the services locally for development:

-   **Frontend:** Navigate to `web-frontend/` and run `npm run dev`. This uses Vite and supports hot-reloading.
-   **Backend:** Navigate to `web-server/` and run `npm run dev`. This uses `tsx` to watch for changes and automatically restart the server.
-   **Scraper (MCP Server):** The most reliable way to test the scraper is to run its test script directly. From the project root, run:
    ```bash
    flight-findr-mcp/venv/bin/python flight-findr-mcp/scrapers/pointsyeah.py
    ```

### Deployment

-   The services are designed to be deployed to **Google Cloud Run**.
-   Deployment is automated via **Google Cloud Build triggers** that watch the `main` branch of the GitHub repository.
-   Each service (`web-server`, `flight-findr-mcp`) has its own `cloudbuild.yaml` file that defines its build and deploy steps.
-   **IMPORTANT:** The `GEMINI_API_KEY` is a secret. It is configured as a **Substitution Variable** in the Cloud Build trigger for the `web-server` and should **NEVER** be committed to the `cloudbuild.yaml` file.

### Key Learnings & Conventions

This project has specific behaviors and solutions that are critical to its operation.

#### `deals.json` Data Structure

The `deals.json` file, which is the output of the scraper, uses a hyper-compact data structure to save space. The data is an array of deals, where each deal is an array itself containing the segments, booking options, and total duration.

-   **`legend`**: A dictionary that maps short keys to full field names. This is used for decompression on the frontend.
-   **`deals`**: A list of flight deal arrays. Each array contains: `[segments, options, duration_minutes]`.
-   **`segments`**: A list of flight segments, where each segment is an array of its properties (e.g., flight number, airports, times).
-   **`options`**: A list of booking options for the given segments. Each option is an array containing the program, transfer partners, URL parameters, and available cabins.

#### Frontend Architecture

The `web-frontend` is a React application built with Vite. It follows a modern, modular, and feature-based architecture.

*   **Component Structure:** Components in `src/components` are organized by feature (`chat`, `deals`, `common`, `home`). This makes the codebase easier to navigate and scale.
    *   `common`: Contains shared, reusable components like `Logo` and `FullScreenModal`.
    *   `chat`: Contains all components related to the chat interface.
    *   `deals`: Contains components for displaying flight deals, including the filters and the table.
    *   `home`: Contains components for the initial welcome screen.

*   **Styling:** The project uses **CSS Modules** for component styling. Each component has a corresponding `.module.css` file, which scopes the styles locally to prevent conflicts. Global styles that are used across the application are defined in `src/App.css`.

*   **State Management:** The primary application state for the chat interface is managed by the `useChat` custom hook (`src/hooks/useChat.ts`). This hook encapsulates the logic for handling messages, loading states, and user input.

*   **Data Flow & API Interaction:**
    *   All communication with the backend API is handled by functions in `src/services/api.ts`.
    *   The raw, compressed flight deal data from the backend is processed and decompressed by functions in `src/utils/data-processing.ts`.
    *   The `useChat` hook orchestrates this flow: it calls the API service, receives the raw data, uses the data processing utility to transform it into a usable format (`CompactFlightDeal[]`), and then updates the state to render the components.

#### Web Server Architecture

The `web-server` is a Node.js/Express application written in TypeScript. It follows a modular structure to separate concerns.

*   **Code Organization:** The `src` directory is organized by feature:
    *   `api`: Contains the route handlers for the Express application (`chatHandler.ts`, `multiCityHandler.ts`, etc.).
    *   `services`: Contains services that are used by the handlers, such as `sessionManager.ts`.
    *   `utils`: Contains utility functions, such as the `gemini-streamer.ts` for handling SSE.
*   **Streaming Logic:** The logic for handling Server-Sent Events (SSE) and streaming responses from the Gemini API is encapsulated in the `streamGeminiResponse` function in `src/utils/gemini-streamer.ts`. This keeps the API handlers clean and focused on request/response logic.
*   **Error Handling:** All API handlers have `try...catch` blocks to ensure that errors are caught and sent to the client in a consistent JSON format.

#### Scraper (flight-findr-mcp) Architecture

The `flight-findr-mcp` module is a Python-based scraper server that uses Playwright. It has been architected for high efficiency by moving planning logic to the Gemini agent and allowing the scraper to focus purely on parallelized execution.

*   **Unified Job-Based Architecture:** The scraper exposes a single, powerful tool (`check_flight_points_prices`) that accepts a list of structured "jobs." The Gemini agent acts as a smart planner, analyzing a user's request and breaking it down into an optimal combination of `matrix` and `multicity` jobs.

*   **Parallel Execution:** The MCP server receives this list of jobs and executes them concurrently, using a pool of browser contexts to maximize parallelism and speed.

*   **Matrix & Multi-City Searches:**
    *   **Matrix:** This job type is used for searching many origins and destinations over a contiguous 5-day date range. The agent provides a list of `valid_routes` to ensure the scraper can filter the matrix results down to only the specific flights the user requested.
    *   **Multi-City:** This job type is used to efficiently pair up two distinct flight legs into a single browser session.

This separation of concerns (Agent plans, Tool executes) makes the system highly flexible and performant.

#### PointsYeah Cash Price Matching

To enrich the award flight data with real-time cash prices, the scraper employs a highly efficient, two-stage process to match points deals with cash fares:

1.  **Upfront Batch Scraping:** Before searching for any award flights, the scraper identifies all unique flight legs (e.g., SEA-JFK) and their full date ranges from the user's request. It then scrapes all potential cash prices for these routes from Google Flights in a single, concurrent batch.

2.  **Optimized Lookup Map:** The collected cash flights are processed into an efficient lookup map (a dictionary). The key for this map is a tuple of a flight's unique properties: `(origin, destination, date, hour, minute, num_stops)`.

3.  **Instantaneous Matching:** As the scraper finds award flights from PointsYeah, it constructs a corresponding lookup key for each one. It uses this key to perform a direct, instantaneous lookup in the cash price map. If a match is found, a final verification of layover airports is performed before the cash price is added to the deal data.

This map-based approach is extremely performant and avoids slow, nested loops, allowing thousands of deals to be cross-referenced with their cash equivalents in milliseconds.

#### Scraper Search Completion

To detect when a flight search is complete, the scraper now waits for a specific network response containing `{"data": {"status": "done"}}`. This is much more reliable than waiting for UI elements like progress bars. This logic is located in the `scrape()` method of `pointsyeah.py`.

#### Server Timeouts on Cloud Platforms

Long-running scraper requests (> 60 seconds) will cause timeouts on cloud platforms like Render or Cloud Run due to load balancer or server defaults. The fix is two-fold and located in the `web-server`:

1.  The Node.js HTTP server timeout is explicitly increased to 5 minutes in `src/index.ts`.
2.  A keep-alive ping (SSE comment) is sent every 15 seconds during a tool call in `src/chatHandler.ts` to keep the browser-to-server connection from being closed by network infrastructure.

#### MCP Server Lifecycle

The `fastmcp` library does not appear to support the ASGI `lifespan` protocol for startup/shutdown events. Therefore, the `mcp_server.py` manages the Playwright lifecycle manually within its `main_async` function, starting the browser before the server runs and using a `try...finally` block to guarantee it closes on shutdown.

#### Production vs. Development Authentication

The application uses two different authentication strategies depending on the environment. This is critical for the OAuth flow to work correctly when the frontend and backend are deployed to different domains (e.g., GitHub Pages and Google Cloud Run).

*   **Production Mode:** In the deployed environment, the frontend and backend must know each other's public URLs. This is configured via environment variables.
    *   **Frontend (`web-frontend`):** The `VITE_API_BASE_URL` variable tells the frontend the location of the backend. This is set in the `.github/workflows/deploy-frontend.yml` file and should be configured as a **Repository Secret** in GitHub Actions.
    *   **Backend (`web-server`):** The backend needs two variables set in its Google Cloud Run service configuration:
        *   `BACKEND_BASE_URL`: The public URL of the `web-server` itself. This is used to construct the correct OAuth `redirect_uri`.
        *   `FRONTEND_BASE_URL`: The public URL of the deployed frontend. This is used to securely send the authentication token back to the frontend using `postMessage`.

*   **Development Mode:** When running locally (`npm run dev`), the code automatically falls back to default `localhost` URLs for both the frontend and backend, and the Vite proxy handles the cross-origin requests. To test the full OAuth flow locally, append `?force_oauth=true` to the URL (e.g., `http://localhost:5173/?force_oauth=true`).

#### Per-Request Backend Authentication

To support multiple concurrent users securely, the `web-server` is architected to be stateless regarding user credentials. It does **not** use the Gemini CLI library's default filesystem-based token cache. Instead, for each authenticated API request, it creates a temporary credential file in memory from the user's token, points the Gemini library to it via an environment variable (`GOOGLE_APPLICATION_CREDENTIALS`), initializes the client for that single request, and then immediately deletes the temporary file in a `finally` block. This ensures that each user's credentials are used to make calls on their behalf and are strictly isolated from all other users.


### **CRITICAL: Final Verification Steps**

1.  **Scraper:** Before claiming any task involving the `flight-findr-mcp` scraper is complete, you **must** run the local test script to verify your changes have not caused a regression.
    ```bash
    flight-findr-mcp/venv/bin/python flight-findr-mcp/scrapers/pointsyeah.py
    ```
2.  **Frontend/Backend:** After making changes to `web-frontend` or `web-server`, you **must** run `cd web-frontend (or web-server) && npm run build` within the respective directory to ensure there are no build or type errors.

### Committing Changes

After any change is confirmed to be working correctly (especially after a successful local test or build), stage all the changes with git to save the progress. Only stage it, do NOT commit it. This creates a stable checkpoint and is a critical best practice.

When committing changes, especially with multi-line commit messages, it's best to use a temporary file to avoid shell quoting issues.

1.  **Write the commit message to a temporary file:**
    ```bash
    # Use the write_file tool
    write_file(
        file_path=".git/commit_msg.txt",
        content="<your commit message>"
    )
    ```

2.  **Commit using the file:**
    ```bash
    # Use the run_shell_command tool
    run_shell_command(
        command="git commit -F .git/commit_msg.txt"
    )
    ```

3.  **Remove the temporary file:**
    ```bash
    # Use the run_shell_command tool
    run_shell_command(
        command="rm .git/commit_msg.txt"
    )
    ```

### Last Notes
Do not make any changes to the async main_test() function in pointsyeah.py unless instructed to do so

Do not change the pointsyeah base url parameters from the following:

&banks=Amex%2CCapital+One%2CChase
&airlineProgram=AR%2CAM%2CAC%2CKL%2CAS%2CAV%2CDL%2CEK%2CEY%2CAY%2CIB%2CB6%2CQF%2CSQ%2CTP%2CTK%2CUA%2CVS

If you make a change to the "memory" in sessionManager.ts , if you have a ` symbol, always escape it with a slash