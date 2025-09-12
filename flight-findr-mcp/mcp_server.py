import asyncio
import argparse
import uvicorn
from fastmcp import FastMCP
from fastmcp.tools import Tool
from scrapers.pointsyeah import PointsYeahScraper
import json
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, ValidationError
from google import genai
import os

# --- Token Counting and Truncation ---

# Configure the token counter
if 'GEMINI_API_KEY' in os.environ:
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    genai_client = genai.Client()
else:
    genai_client = None

TOKEN_LIMIT = 1048576
MIN_DEALS_PER_ROUTE = 10

def count_tokens(text: str) -> int:
    """Counts the number of tokens in a given text using the Gemini API."""
    if not genai_client:
        print("(Token Count) GenAI client not configured, falling back to char estimate.")
        return len(text) // 4
    try:
        response = genai_client.models.count_tokens(
            model="gemini-2.5-pro", contents=text
        )
        return response.total_tokens
    except Exception as e:
        print(f"(Token Count) API error: {e}. Falling back to char estimate.")
        return len(text) // 4

def get_min_points_for_deal(deal: List) -> float:
    """Helper to extract the minimum points from a deal's complex structure."""
    min_points = float('inf')
    try:
        for option in deal[1]:
            for cabin_deal in option[3]:
                min_points = min(min_points, cabin_deal[1])
    except (IndexError, TypeError): pass
    return min_points

def truncate_deals_if_needed(deals_json: str) -> str:
    """Checks token count and truncates deals to fit the token limit using a binary search approach."""
    try:
        initial_token_count = count_tokens(deals_json)
        if initial_token_count <= TOKEN_LIMIT:
            return deals_json

        print(f"Warning: Initial token count ({initial_token_count}) exceeds limit. Applying truncation.")
        data = json.loads(deals_json)
        original_deal_count = len(data.get('deals', []))

        deals_by_route: Dict[str, List] = {}
        for deal in data['deals']:
            try:
                route_key = f"{deal[0][0][2]}-{deal[0][-1][3]}"
                if route_key not in deals_by_route:
                    deals_by_route[route_key] = []
                deals_by_route[route_key].append(deal)
            except (IndexError, TypeError):
                continue
        
        for route in deals_by_route:
            deals_by_route[route].sort(key=get_min_points_for_deal)

        # Binary search for the optimal percentage of deals to keep
        best_keep_percent = 0.0
        low = 0.0
        high = 1.0
        
        while high - low >= 0.01:
            mid_percent = (low + high) / 2
            if mid_percent == 0: break # Avoid getting stuck

            temp_deals = []
            for deals in deals_by_route.values():
                initial_count = len(deals)
                keep_count = max(MIN_DEALS_PER_ROUTE, int(initial_count * mid_percent))
                if initial_count < MIN_DEALS_PER_ROUTE:
                    keep_count = initial_count
                temp_deals.extend(deals[:keep_count])
            
            data['deals'] = temp_deals
            current_token_count = count_tokens(json.dumps(data))

            if current_token_count <= TOKEN_LIMIT:
                best_keep_percent = mid_percent
                low = mid_percent # Try to include more deals
            else:
                high = mid_percent # Need to include fewer deals

        # Finalize the response with the best percentage found
        if best_keep_percent == 0:
            # This means even the minimum number of deals was too large.
            return json.dumps({
                "error": "The smallest possible flight data response still exceeded the token limit.",
                "warning": "Please try a more specific search with fewer routes or a smaller date range."
            })

        final_deals = []
        for deals in deals_by_route.values():
            initial_count = len(deals)
            keep_count = max(MIN_DEALS_PER_ROUTE, int(initial_count * best_keep_percent))
            if initial_count < MIN_DEALS_PER_ROUTE:
                keep_count = initial_count
            final_deals.extend(deals[:keep_count])

        data['deals'] = final_deals
        data['warning'] = f"Response truncated due to excessive length. Showing the best {len(final_deals)} of {original_deal_count} deals found."
        final_json = json.dumps(data)
        final_token_count = count_tokens(final_json)

        print(f"Truncation successful. Kept {len(final_deals)} of {original_deal_count} deals. Final token count: {final_token_count}")
        return final_json

    except Exception as e:
        print(f"An unexpected error occurred during truncation: {e}")
        # Return a simple string error that the Gemini Core library can handle.
        return "Error: An unexpected error occurred while processing the flight data. The data may have been too large to handle."

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
        self.current_search_task: Optional[asyncio.Task] = None
        
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

        self.current_search_task = asyncio.current_task()
        try:
            validated_jobs = []
            for job in jobs:
                if job.get("job_type") == "matrix":
                    validated_jobs.append(MatrixJob(**job).dict())
                elif job.get("job_type") == "multicity":
                    validated_jobs.append(MultiCityJob(**job).dict())
                else:
                    raise ValueError(f"Unknown job_type: {job.get('job_type')}")
            
            results_json = await self.scraper.search_flights(validated_jobs)

            return truncate_deals_if_needed(results_json)

        except asyncio.CancelledError:
            print("Search task cancelled.")
            return json.dumps({"error": "Search cancelled."})
        except (ValidationError, ValueError) as e:
            return json.dumps({"error": f"Invalid job object: {e}"})
        finally:
            self.current_search_task = None

mcp_server = FlightSearchMCP()

# --- Lifecycle Management ---
async def startup_event():
    """Initializes the scraper instance."""
    print("Server starting up, initializing scrapers...")
    mcp_server.scraper = await PointsYeahScraper.create()
    print("Scrapers initialized.")

async def shutdown_event():
    """Closes the scraper instance."""
    print("Executing shutdown event...")
    if mcp_server.current_search_task:
        print("Cancelling active search task...")
        mcp_server.current_search_task.cancel()
        await asyncio.sleep(0)

    if mcp_server.scraper:
        await mcp_server.scraper.close()
    print("Shutdown event complete.")

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
    server.install_signal_handlers = lambda: None
    
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
        print("\nMain process received KeyboardInterrupt.")
    
    print("MCP Server has shut down.")

if __name__ == "__main__":
    main()