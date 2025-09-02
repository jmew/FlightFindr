import argparse
import sys
import asyncio
from playwright.async_api import async_playwright
from scrapers import seats_aero, pointsyeah
from cash_price import get_flight_cash_prices, normalize_program_name, parse_time

async def main():
    """
    Main asynchronous function to run the flight deal finder.
    """
    parser = argparse.ArgumentParser(description="Find the best flight deals using points.")
    parser.add_argument("origin", nargs='+', help="One or more origin airport IATA codes (e.g., SFO JFK)")
    parser.add_argument("destination", nargs='+', help="One or more destination airport IATA codes (e.g., LAX LHR)")
    parser.add_argument("start_date", help="Start date for the travel search in YYYY-MM-DD format.")
    parser.add_argument("end_date", help="End date for the travel search in YYYY-MM-DD format.")
    
    # Optional filter arguments
    parser.add_argument("--programs", nargs='+', help="List of frequent flyer programs to filter by.")
    parser.add_argument("--alliances", nargs='+', help="List of airline alliances to filter by.")
    parser.add_argument("--transfer_partners", nargs='+', help="List of transfer partners to filter by.")
    parser.add_argument("--points_min", type=int, help="Minimum points required for a deal.")
    parser.add_argument("--points_max", type=int, help="Maximum points required for a deal.")
    parser.add_argument("--days", type=int, help="Number of days to search around the specified date.")
    parser.add_argument("--source", default="pointsyeah", choices=["seats.aero", "pointsyeah", "all"], help="The data source to use.")

    args = parser.parse_args()
    
    origin_airports = ",".join(args.origin)
    destination_airports = ",".join(args.destination)

    print(f"Searching for flights from {origin_airports} to {destination_airports} between {args.start_date} and {args.end_date} using {args.source}...")
    
    deals = []
    async with async_playwright() as playwright:
        # Initialize scrapers that need a playwright instance
        await seats_aero.initialize_scraper(playwright)
        await pointsyeah.initialize_scraper(playwright)

        try:
            if args.source == "seats.aero":
                deals = await seats_aero.scrape_seats_aero(
                    origin_airports, destination_airports, args.start_date, args.end_date,
                    programs=args.programs, alliances=args.alliances, transfer_partners=args.transfer_partners,
                    points_min=args.points_min, points_max=args.points_max, days=args.days
                )
            elif args.source == "pointsyeah":
                deals = await pointsyeah.scrape_pointsyeah(
                    origin_airports, destination_airports, args.start_date, args.end_date
                )
            elif args.source == "all":
                seats_aero_task = seats_aero.scrape_seats_aero(
                    origin_airports, destination_airports, args.start_date, args.end_date,
                    programs=args.programs, alliances=args.alliances, transfer_partners=args.transfer_partners,
                    points_min=args.points_min, points_max=args.points_max, days=args.days
                )
                pointsyeah_task = pointsyeah.scrape_pointsyeah(
                    origin_airports, destination_airports, args.start_date, args.end_date
                )
                results = await asyncio.gather(seats_aero_task, pointsyeah_task, return_exceptions=True)
                seats_aero_deals = results[0] if not isinstance(results[0], Exception) else []
                pointsyeah_deals = results[1] if not isinstance(results[1], Exception) else []
                deals = (seats_aero_deals or []) + (pointsyeah_deals or [])

        except Exception as e:
            print(f"Error scraping {args.source}: {e}", file=sys.stderr)
            deals = []
        finally:
            await seats_aero.close_scraper()
            await pointsyeah.close_scraper()

    if not deals:
        print("No deals found.")
        return

    # Deduplicate and merge deals
    merged_deals = {}
    for deal in deals:
        normalized_program = normalize_program_name(deal.get("program"))
        if not normalized_program:
            continue

        departure_time_str = deal.get("departure_time")
        arrival_time_str = deal.get("arrival_time")
        normalized_departure_time = parse_time(departure_time_str) if departure_time_str else None
        normalized_arrival_time = parse_time(arrival_time_str) if arrival_time_str else None
        deal_id = (deal.get("date"), deal.get("route"), normalized_program, normalized_departure_time, normalized_arrival_time)

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
    
    unique_deals = list(merged_deals.values())

    # Enrich deals with cash prices and CPP
    cash_price_tasks = []
    for deal in unique_deals:
        for cabin in ['economy', 'premium', 'business', 'first']:
            cash_price_tasks.append(get_flight_cash_prices(deal, cabin))
    
    await asyncio.gather(*cash_price_tasks)

    # Sort and print deals
    unique_deals.sort(key=lambda d: min((c.get('points', float('inf')) for c in (d.get(cab) for cab in ['economy', 'premium', 'business', 'first']) if c), default=float('inf')))

    for i, deal in enumerate(unique_deals):
        print(f"--- Deal #{i+1} ---")
        print(f"  Date: {deal['date']}")
        print(f"  Program: {deal['program']}")
        print(f"  Route: {deal['route']}")
        for cabin in ['economy', 'premium', 'business', 'first']:
            if deal.get(cabin):
                print(f"  {cabin.capitalize()}:")
                
                departure_time_str = deal[cabin].get('departure_time') or deal.get('departure_time')
                arrival_time_str = deal[cabin].get('arrival_time') or deal.get('arrival_time')
                
                if departure_time_str and arrival_time_str:
                    departure_time = parse_time(departure_time_str)
                    arrival_time = parse_time(arrival_time_str)
                    if departure_time and arrival_time:
                        print(f"    Time: {departure_time.strftime('%I:%M %p')} -> {arrival_time.strftime('%I:%M %p')}")

                print(f"    Points: {deal[cabin]['points']}")
                print(f"    Fees: {deal[cabin]['fees']}")
                if 'cheapest_cash_price' in deal[cabin] and deal[cabin]['cheapest_cash_price']:
                    cpp = deal[cabin].get('cheapest_cpp', 'N/A')
                    print(f"    Cheapest Cash Price: ${deal[cabin]['cheapest_cash_price']:.2f} ({cpp} CPP)")
                if 'exact_cash_price' in deal[cabin] and deal[cabin]['exact_cash_price'] != 'N/A' and deal[cabin]['exact_cash_price']:
                    cpp = deal[cabin].get('exact_cpp', 'N/A')
                    print(f"    Exact Match Cash Price: ${deal[cabin]['exact_cash_price']:.2f} ({cpp} CPP)")

        print("-" * 16)

    print("Search complete.")

if __name__ == "__main__":
    asyncio.run(main())
