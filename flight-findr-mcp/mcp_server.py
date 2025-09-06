import asyncio
import argparse
import uvicorn
from fastmcp import FastMCP
from fastmcp.tools import Tool
from scrapers import pointsyeah
import json
from typing import List, Optional, Dict, Any
from playwright.async_api import Playwright, async_playwright


class FlightSearchMCP(FastMCP):
    def __init__(self):
        super().__init__()
        self.add_tool(Tool.from_function(
            self.check_flight_points_prices,
            description="Finds the best flight deals using points and cash from various sources.",
        ))


    async def check_flight_points_prices(
        self,
        searches: List[Dict[str, Any]],
    ) -> str:
        """
        Checks for flight points prices across different platforms for a list of searches.
        Each search should be a dictionary with origin_airports, destination_airports, start_date, and end_date.
        """
        return await pointsyeah.check_flight_points_prices(searches)

mcp_server = FlightSearchMCP()

# --- Lifecycle Management ---
playwright_instance: Optional[Playwright] = None

async def startup_event():
    """Initializes the playwright instance and scrapers."""
    global playwright_instance
    print("Server starting up, initializing scrapers...")
    playwright_instance = await async_playwright().start()
    await pointsyeah.initialize_scraper(playwright_instance)
    print("Scrapers initialized.")

async def shutdown_event():
    """Closes the global scraper instance."""
    global scraper_instance
    if scraper_instance:
        print("Closing PointsYeah scraper at server shutdown...")
        await scraper_instance.close()
        scraper_instance = None

async def main_async(args):
    """Runs startup, the server, and shutdown."""
    if args.transport == 'stdio':
        # Fallback for stdio mode, which doesn't use Uvicorn
        print("Running in stdio mode...")
        await startup_event()
        try:
            mcp_server.run(transport="stdio")
        finally:
            await shutdown_event()
        return

    # HTTP mode
    await startup_event()
    
    app = mcp_server.http_app()
    config = uvicorn.Config(app, host="0.0.0.0", port=9999, log_level="info", timeout_keep_alive=300)
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    finally:
        await shutdown_event()

def main():
    parser = argparse.ArgumentParser(description="Run the Flight Search MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="http",
        help="The transport protocol to use.",
    )
    args = parser.parse_args()
    
    print(f"MCP Server: Starting in {args.transport} mode...")
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    
    print("MCP Server has shut down.")

if __name__ == "__main__":
    main()