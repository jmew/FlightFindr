import asyncio
import argparse
import uvicorn
from fastmcp import FastMCP
from fastmcp.tools import Tool
from scrapers import pointsyeah
import json
from typing import List, Optional, Dict, Any
from playwright.async_api import Playwright, async_playwright
import airportsdata

from scrapers.utils import PROGRAM_MAPPING

# --- Airport Data ---
airports: Optional[Dict[str, Any]] = None

def load_airport_data():
    """Loads the airport data into memory."""
    global airports
    if airports is None:
        print("Loading airport data...")
        airports = airportsdata.load('IATA')
        print("Airport data loaded.")

def normalize_program_name(program_name: Optional[str]) -> Optional[str]:
    """Normalizes airline program names for consistent matching."""
    if not program_name:
        return None
    
    lower_program_name = program_name.strip().lower()
    
    return PROGRAM_MAPPING.get(lower_program_name, program_name.title())

class FlightSearchMCP(FastMCP):
    def __init__(self):
        super().__init__()
        self.add_tool(Tool.from_function(
            self.check_flight_points_prices,
            description="Finds the best flight deals using points and cash from various sources.",
        ))

    def get_airport_info(self, iata_code: str) -> Dict[str, Any]:
        """Returns airport information for a given IATA code."""
        if not airports:
            return {"error": "Airport data not loaded"}
        return airports.get(iata_code, {"error": "Airport not found"})


    async def check_flight_points_prices(
        self,
        searches: List[Dict[str, Any]],
    ) -> str:
        """
        Checks for flight points prices across different platforms for a list of searches.
        Each search should be a dictionary with origin_airports, destination_airports, start_date, and end_date.
        """
        
        all_deals = []
        
        async def run_search(search_query: Dict[str, Any]):
            origin_str = ",".join(search_query['origin_airports'])
            dest_str = ",".join(search_query['destination_airports'])
            start_date = search_query['start_date']
            end_date = search_query['end_date']
            
            print(f"Searching for flights from {origin_str} to {dest_str} between {start_date} and {end_date}...")
            
            try:
                pointsyeah_deals = await pointsyeah.scrape_pointsyeah(origin_str, dest_str, start_date, end_date)
                for deal in pointsyeah_deals:
                    deal["source"] = "pointsyeah"
                return pointsyeah_deals
            except Exception as e:
                print(f"An unexpected error occurred during scraping: {e}")
                return []

        tasks = [run_search(search) for search in searches]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            all_deals.extend(result)

        if not all_deals:
            return json.dumps({"all_deals": [], "cheapest_deal": None}, indent=2)

        # Deduplicate and merge deals
        merged_deals = {}
        for deal in all_deals:
            normalized_program = normalize_program_name(deal.get("program"))
            if not normalized_program:
                continue

            deal_id = (
                deal.get("date"),
                deal.get("route"),
                normalized_program,
                deal.get("departure_time"),
                deal.get("arrival_time"),
            )

            if deal_id not in merged_deals:
                # Enrich with airport info
                origin_code, dest_code = deal.get("route", " -> ").split(" -> ")
                deal["origin_airport_info"] = self.get_airport_info(origin_code)
                deal["destination_airport_info"] = self.get_airport_info(dest_code)
                deal["program"] = normalized_program
                merged_deals[deal_id] = deal
            else:
                existing_deal = merged_deals[deal_id]
                for cabin in ["economy", "premium", "business", "first"]:
                    new_cabin_data = deal.get(cabin)
                    if not new_cabin_data or not new_cabin_data.get("points"):
                        continue

                    existing_cabin_data = existing_deal.get(cabin)
                    if (
                        not existing_cabin_data
                        or not existing_cabin_data.get("points")
                        or new_cabin_data["points"] < existing_cabin_data["points"]
                    ):
                        existing_deal[cabin] = new_cabin_data
                        if "source" in existing_deal and existing_deal["source"] != deal.get("source"):
                            existing_deal["source"] = "multiple"
        
        unique_deals = list(merged_deals.values())

        def get_best_points(deal):
            for cabin in ['economy', 'premium', 'business', 'first']:
                if deal.get(cabin) and deal[cabin].get('points'):
                    return deal[cabin]['points']
            return float('inf')

        unique_deals.sort(key=get_best_points)
        
        cheapest_deal = unique_deals[0] if unique_deals else None

        result = {
            "all_deals": unique_deals,
            "cheapest_deal": cheapest_deal,
        }

        return json.dumps(result, indent=2)

mcp_server = FlightSearchMCP()

# --- Lifecycle Management ---
playwright_instance: Optional[Playwright] = None

async def startup_event():
    """Initializes the playwright instance and scrapers."""
    global playwright_instance
    print("Server starting up, initializing scrapers...")
    load_airport_data()
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