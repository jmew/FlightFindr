import asyncio
import argparse
import uvicorn
from fastmcp import FastMCP
from fastmcp.tools import Tool
from scrapers import pointsyeah
import json
from typing import List, Optional
from cash_price import get_flight_cash_prices, normalize_program_name
from playwright.async_api import Playwright, async_playwright

class FlightSearchMCP(FastMCP):
    def __init__(self):
        super().__init__()
        tool = Tool.from_function(
            self.check_flight_points_prices,
            description="Finds the best flight deals using points and cash from various sources.",
        )
        self.add_tool(tool)

    async def check_flight_points_prices(
        self,
        origin_airports: List[str],
        destination_airports: List[str],
        start_date: str,
        end_date: str,
        programs: Optional[List[str]] = None,
        alliances: Optional[List[str]] = None,
        transfer_partners: Optional[List[str]] = None,
        points_min: Optional[int] = None,
        points_max: Optional[int] = None,
        days: Optional[int] = None,
    ) -> str:
        """
        Checks for flight points prices across different platforms.
        """
        origin_str = ",".join(origin_airports)
        dest_str = ",".join(destination_airports)

        print(f"Searching for flights from {origin_str} to {dest_str} between {start_date} and {end_date}...")

        all_deals = []
        try:
            pointsyeah_deals = await pointsyeah.scrape_pointsyeah(origin_str, dest_str, start_date, end_date)
            for deal in pointsyeah_deals:
                deal["source"] = "pointsyeah"
            all_deals.extend(pointsyeah_deals)
            print(f"Found {len(pointsyeah_deals)} deals on pointsyeah")
        except Exception as e:
            print(f"An unexpected error occurred during scraping: {e}")

        if not all_deals:
            return json.dumps({"all_deals": [], "cheapest_deal": None}, indent=2)

        # Deduplicate and merge deals
        merged_deals = {}
        for deal in all_deals:
            normalized_program = normalize_program_name(deal.get("program"))
            if not normalized_program:
                continue  # Skip deals without a program name

            deal_id = (deal.get("date"), deal.get("route"), normalized_program)

            if deal_id not in merged_deals:
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

        # Enrich deals with cash prices and CPP
        cash_price_tasks = []
        for deal in unique_deals:
            for cabin in ['economy', 'premium', 'business', 'first']:
                cash_price_tasks.append(get_flight_cash_prices(deal, cabin))
        
        await asyncio.gather(*cash_price_tasks)

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
    playwright_instance = await async_playwright().start()
    await pointsyeah.initialize_scraper(playwright_instance)
    print("Scrapers initialized.")

async def shutdown_event():
    """Closes the scrapers and playwright instance."""
    global playwright_instance
    print("Server shutting down, closing scrapers...")
    await pointsyeah.close_scraper()
    if playwright_instance:
        await playwright_instance.stop()
    print("Scrapers and Playwright closed.")

def main():
    parser = argparse.ArgumentParser(description="Run the Flight Search MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="http",
        help="The transport protocol to use.",
    )
    args = parser.parse_args()

    if args.transport == 'stdio':
        # Fallback for stdio mode, which doesn't use Uvicorn
        print("Running in stdio mode...")
        mcp_server.run(transport="stdio")
        return

    print("MCP Server: Starting with Uvicorn...")
    
    # Get the ASGI app from the FastMCP instance
    app = mcp_server.http_app()

    # Attach startup and shutdown event handlers
    app.add_event_handler("startup", startup_event)
    app.add_event_handler("shutdown", shutdown_event)

    # Configure and run the Uvicorn server
    config = uvicorn.Config(app, host="0.0.0.0", port=9999, log_level="info")
    server = uvicorn.Server(config)
    
    # Uvicorn's run() is blocking and will handle the main event loop
    server.run()
    
    print("MCP Server has shut down.")

if __name__ == "__main__":
    main()