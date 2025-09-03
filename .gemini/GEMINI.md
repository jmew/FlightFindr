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

2.  **Scraper Search Completion:**
    *   To detect when a flight search is complete, the scraper now waits for a specific network response containing `{"data": {"status": "done"}}`.
    *   This is much more reliable than waiting for UI elements like progress bars. This logic is located in the `scrape()` method of `pointsyeah.py`.

3.  **Server Timeouts on Cloud Platforms:**
    *   Long-running scraper requests (> 60 seconds) will cause timeouts on cloud platforms like Render or Cloud Run due to load balancer or server defaults.
    *   The fix is two-fold and located in the `web-server`:
        1.  The Node.js HTTP server timeout is explicitly increased to 5 minutes in `src/index.ts`.
        2.  A keep-alive ping (SSE comment) is sent every 15 seconds during a tool call in `src/chatHandler.ts` to keep the browser-to-server connection from being closed by network infrastructure.

4.  **MCP Server Lifecycle:**
    *   The `fastmcp` library does not appear to support the ASGI `lifespan` protocol for startup/shutdown events.
    *   Therefore, the `mcp_server.py` manages the Playwright lifecycle manually within its `main_async` function, starting the browser before the server runs and using a `try...finally` block to guarantee it closes on shutdown.

### **CRITICAL: Final Verification Steps**

1.  **Scraper:** Before claiming any task involving the `flight-findr-mcp` scraper is complete, you **must** run the local test script to verify your changes have not caused a regression.
    ```bash
    flight-findr-mcp/venv/bin/python flight-findr-mcp/scrapers/pointsyeah.py
    ```
2.  **Frontend/Backend:** After making changes to `web-frontend` or `web-server`, you **must** run `npm run build` within the respective directory to ensure there are no build or type errors.

### Committing Changes

After any change is confirmed to be working correctly (especially after a successful local test or build), stage all the changes with git to save the progress. This creates a stable checkpoint and is a critical best practice.