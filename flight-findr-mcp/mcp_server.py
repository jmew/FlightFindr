import asyncio
import argparse
from fastmcp import FastMCP
from fastmcp.tools import Tool
from scrapers import seats_aero, pointsyeah
import json
from typing import List, Optional
from cash_price import get_flight_cash_prices, normalize_program_name

class FlightSearchMCP(FastMCP):
    def __init__(self):
        super().__init__()
        tool = Tool.from_function(
            self.check_flight_points_prices,
            description="Finds the best flight deals using points and cashfrom various sources.",
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

        Args:
            origin_airports: List of origin airport IATA codes (e.g., ["SFO", "JFK"]).
            destination_airports: List of destination airport IATA codes (e.g., ["LAX", "LHR"]).
            start_date: Start date for the travel search in YYYY-MM-DD format.
            end_date: End date for the travel date range in YYYY-MM-DD format.
            programs: List of frequent flyer programs to filter by.
            alliances: List of airline alliances to filter by.
            transfer_partners: List of transfer partners to filter by.
            points_min: Minimum points required for a deal.
            points_max: Maximum points required for a deal.
            days: Number of days to search around the specified date.

        Returns:
            A JSON string with all available deals and the cheapest deal found.
        """
        loop = asyncio.get_event_loop()
        origin_str = ",".join(origin_airports)
        dest_str = ",".join(destination_airports)

        print(f"Searching for flights from {origin_str} to {dest_str} between {start_date} and {end_date}...")

        # Run scrapers in parallel
        seats_aero_task = loop.run_in_executor(
            None,
            seats_aero.scrape_seats_aero,
            origin_str,
            dest_str,
            start_date,
            end_date,
            programs,
            alliances,
            transfer_partners,
            points_min,
            points_max,
            days,
        )
        pointsyeah_task = pointsyeah.scrape_pointsyeah(origin_str, dest_str, start_date, end_date)

        all_deals = []
        try:
            # Await both tasks concurrently
            results = await asyncio.gather(seats_aero_task, pointsyeah_task, return_exceptions=True)
            
            seats_aero_deals = results[0]
            if isinstance(seats_aero_deals, Exception):
                print(f"Error scraping seats.aero: {seats_aero_deals}")
                seats_aero_deals = []
            for deal in seats_aero_deals:
                deal["source"] = "seats.aero"
            all_deals.extend(seats_aero_deals)
            print(f"Found {len(seats_aero_deals)} deals on seats.aero")

            pointsyeah_deals = results[1]
            if isinstance(pointsyeah_deals, Exception):
                print(f"Error scraping pointsyeah: {pointsyeah_deals}")
                pointsyeah_deals = []
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
                # Merge cabin data, keeping the best (lowest points)
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
                        # If sources differ, mark as 'multiple'
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

import atexit

mcp_server = FlightSearchMCP()

def cleanup():
    """Synchronous cleanup function to be called on exit."""
    print("Shutting down scrapers...")
    try:
        asyncio.run(pointsyeah.close_scraper())
    except Exception as e:
        print(f"Error closing PointsYeah scraper: {e}")

def main():
    print("MCP Server: Starting...")
    parser = argparse.ArgumentParser(description="Run the Flight Search MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="The transport protocol to use.",
    )
    args = parser.parse_args()

    print(f"MCP Server: Transport selected: {args.transport}")

    # Register the cleanup function to be called on exit
    atexit.register(cleanup)

    # Initialize the scraper using a temporary event loop
    try:
        asyncio.run(pointsyeah.initialize_scraper())
    except Exception as e:
        print(f"Failed to initialize scraper: {e}")
        return

    if args.transport == "stdio":
        mcp_server.run(transport="stdio")
    elif args.transport == "http":
        print("MCP Server: Starting HTTP server on localhost:9999...")
        mcp_server.run(transport="http", host="0.0.0.0", port=9999)
    
    print("MCP Server: mcp_server.run() has completed.")

if __name__ == "__main__":
    main()