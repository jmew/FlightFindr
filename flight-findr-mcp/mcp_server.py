import asyncio
import argparse
import uvicorn
from fastmcp import FastMCP
from fastmcp.tools import Tool
from scrapers.pointsyeah import PointsYeahScraper
import json
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, ValidationError

class MatrixJob(BaseModel):
    job_type: str
    origins: List[str]
    destinations: List[str]
    start_date: str
    end_date: str
    valid_routes: List[Tuple[str, str]]

class MultiCityLeg(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str

class MultiCityJob(BaseModel):
    job_type: str
    leg1: MultiCityLeg
    leg2: MultiCityLeg

class FlightSearchMCP(FastMCP):
    def __init__(self):
        super().__init__()
        self.scraper: Optional[PointsYeahScraper] = None
        
        self.add_tool(Tool.from_function(
            self.check_flight_points_prices,
            description="""Finds flight deals. Accepts a list of "jobs" to run in parallel.

Schema for a 'matrix' job (many origins/destinations in one date range):
{
  "job_type": "matrix",
  "origins": ["SEA", "JFK"],
  "destinations": ["LHR", "CDG"],
  "start_date": "2025-10-20",
  "end_date": "2025-10-24",
  "valid_routes": [["SEA", "LHR"], ["JFK", "CDG"]]
}

Schema for a 'multicity' job (two distinct legs):
{
  "job_type": "multicity",
  "leg1": {"origin": "LHR", "destination": "HKG", "start_date": "2025-11-01", "end_date": "2025-11-02"},
  "leg2": {"origin": "HKG", "destination": "TPE", "start_date": "2025-11-15", "end_date": "2025-11-16"}
}
            """,
        ))

    async def check_flight_points_prices(
        self,
        jobs: List[Dict[str, Any]],
    ) -> str:
        """
        Executes a list of flight search jobs in parallel.
        """
        if not self.scraper:
            return json.dumps({"error": "Scraper not initialized"})
        
        if not isinstance(jobs, list):
             return json.dumps({"error": "Invalid input, 'jobs' must be a list of job objects."})

        try:
            # Validate input with Pydantic
            validated_jobs = []
            for job in jobs:
                if job.get("job_type") == "matrix":
                    validated_jobs.append(MatrixJob(**job).dict())
                elif job.get("job_type") == "multicity":
                    validated_jobs.append(MultiCityJob(**job).dict())
                else:
                    raise ValueError(f"Unknown job_type: {job.get('job_type')}")
            
            return await self.scraper.search_flights(validated_jobs)
        except (ValidationError, ValueError) as e:
            return json.dumps({"error": f"Invalid job object: {e}"})

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