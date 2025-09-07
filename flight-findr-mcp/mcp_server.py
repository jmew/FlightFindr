import asyncio
import argparse
import uvicorn
from fastmcp import FastMCP
from fastmcp.tools import Tool
from scrapers.pointsyeah import PointsYeahScraper
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ValidationError

class FlightSearch(BaseModel):
    origin_airports: List[str]
    destination_airports: List[str]
    start_date: str
    end_date: str

class FlightSearchMCP(FastMCP):
    def __init__(self):
        super().__init__()
        self.scraper: Optional[PointsYeahScraper] = None
        
        self.add_tool(Tool.from_function(
            self.check_flight_points_prices,
            description="""Finds the best flight deals using points and cash from various sources. It accepts the following schema:
                "parameters": {
                    "type": "object",
                    "properties": {
                        "searches": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "origin_airports": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "destination_airports": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "start_date": {"type": "string"},
                                    "end_date": {"type": "string"}
                                },
                                "required": ["origin_airports", "destination_airports", "start_date", "end_date"]
                            }
                        }
                    },
                    "required": ["searches"]
                }
            """,
        ))

    async def check_flight_points_prices(
        self,
        searches: List[Dict[str, Any]],
    ) -> str:
        """
        Checks for flight points prices across different platforms for a list of searches.
        """
        if not self.scraper:
            return json.dumps({"error": "Scraper not initialized"})
        
        if not isinstance(searches, list):
             return json.dumps({"error": "Invalid input, 'searches' must be a list of search objects."})

        try:
            # Validate input with Pydantic
            validated_searches = [FlightSearch(**search) for search in searches]
            search_dicts = [search.dict() for search in validated_searches]
            return await self.scraper.search_flights(search_dicts)
        except ValidationError as e:
            return json.dumps({"error": f"Invalid search object: {e}"})

mcp_server = FlightSearchMCP()

# --- Lifecycle Management ---
async def startup_event():
    """Initializes the scraper instance."""
    print("Server starting up, initializing scrapers...")
    mcp_server.scraper = await PointsYeahScraper.create()
    print("Scrapers initialized.")

async def shutdown_event():
    """Closes the scraper instance."""
    if mcp_server.scraper:
        await mcp_server.scraper.close()

async def main_async(args):
    """Runs startup, the server, and shutdown."""
    if args.transport == 'stdio':
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