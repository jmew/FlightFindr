import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright, Page, Browser, Playwright, TimeoutError
import json
import asyncio
import os
from typing import List, Dict, Any, Optional
from scrapers.utils import parse_time, fetch_cash_prices, PROGRAM_MAPPING
from datetime import datetime, timedelta
import airportsdata
import json


# --- Airport Data ---
airports: Optional[Dict[str, Any]] = None

def load_airport_data():
    """Loads the airport data into memory."""
    global airports
    if airports is None:
        print("Loading airport data...")
        airports = airportsdata.load('IATA')
        print("Airport data loaded.")

def get_airport_info(iata_code: str) -> Dict[str, Any]:
    """Returns airport information for a given IATA code."""
    if not airports:
        return {"error": "Airport data not loaded"}
    return airports.get(iata_code, {"error": "Airport not found"})

def normalize_program_name(program_name: Optional[str]) -> Optional[str]:
    """Normalizes airline program names for consistent matching."""
    if not program_name:
        return None
    
    lower_program_name = program_name.strip().lower()
    
    return PROGRAM_MAPPING.get(lower_program_name, program_name.title())

async def check_flight_points_prices(
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
            pointsyeah_deals = await scrape_pointsyeah(origin_str, dest_str, start_date, end_date)
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
            deal["origin_airport_info"] = get_airport_info(origin_code)
            deal["destination_airport_info"] = get_airport_info(dest_code)
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


async def scrape_cash_prices_for_all_cabins(origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    # Generate a list of dates between start_date and end_date
    dates = []
    current_date = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    while current_date <= end:
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    cash_price_tasks = []
    for cabin in ['economy', 'premium', 'business', 'first']:
        cash_price_tasks.append(fetch_cash_prices(origin, destination, dates, cabin))
    return await asyncio.gather(*cash_price_tasks)


class PointsYeahScraper:
    """
    A class to manage a persistent browser session for scraping PointsYeah.com,
    optimizing performance by logging in only once.
    """
    def __init__(self, playwright: Playwright, headless: bool = True):
        self.playwright: Playwright = playwright
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start(self):
        """Initializes the browser and logs in."""
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ]
        )
        self.page = await self._create_new_page()

    async def _create_new_page(self) -> Page:
        """Creates a new page with anti-bot detection scripts and resource blocking."""
        # Determine the absolute path to the auth_state.json file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        auth_file_path = os.path.join(script_dir, "auth_state.json")

        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light',
            storage_state=auth_file_path
        )
        page = await context.new_page()

        async def intelligent_block(route):
            if "flight/search/fetch_result" in route.request.url or "flight/search/create_task" in route.request.url:
                await route.continue_()
            elif route.request.resource_type in ["image", "font", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", intelligent_block)
        
        stealth_script = '''
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.navigator.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        '''
        await page.add_init_script(stealth_script)
        return page

    async def scrape(self, origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Scrapes pointsyeah.com for flight deals."""
        if not self.page:
            raise Exception("Scraper not initialized properly.")

        best_deals: Dict[Any, Any] = {}
        loop = asyncio.get_running_loop()
        search_done_future = loop.create_future()

        async def handle_response(response):
            if "flight/search/fetch_result" in response.url:
                try:
                    data = await response.json()
                    if data.get("data", {}).get("status") == "done":
                        if not search_done_future.done():
                            search_done_future.set_result(True)
                        return

                    results = data.get("data", {}).get("result")
                    if data.get("success") and results:
                        self._process_deals(results, best_deals)
                except Exception as e:
                    if not search_done_future.done():
                        search_done_future.set_exception(e)

        self.page.on("response", handle_response)

        try:
            search_url = self._build_search_url(origin, destination, start_date, end_date)
            points_task = asyncio.create_task(self.page.goto(search_url, timeout=90000, wait_until='domcontentloaded'))
            cash_task = asyncio.create_task(scrape_cash_prices_for_all_cabins(origin, destination, start_date, end_date))

            await asyncio.wait_for(search_done_future, timeout=120)
            print("Search complete (detected 'done' signal).")

            # Wait for both tasks to complete
            processed_deals_list, cash_prices_list = await asyncio.gather(
                asyncio.create_task(asyncio.sleep(0, result=list(best_deals.values()))),
                cash_task
            )

        except asyncio.TimeoutError:
            print("Timed out waiting for the 'done' signal from the server.")
            return []
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            return []
        finally:
            self.page.remove_listener("response", handle_response)

        # Match cash prices to deals
        for deal in processed_deals_list:
            for cabin_prices in cash_prices_list:
                cabin = cabin_prices['cabin']
                if not deal.get(cabin) or not deal[cabin].get('points'):
                    continue

                flights = cabin_prices['flights']
                if not flights:
                    continue

                # Cheapest cash price
                cheapest_flight = min(flights, key=lambda x: x['price'])
                cheapest_price = cheapest_flight['price']
                points = deal[cabin]['points']
                cheapest_cpp = (cheapest_price / points) * 100 if points > 0 else 0
                deal[cabin]['cheapest_cash_price'] = cheapest_price
                deal[cabin]['cheapest_cpp'] = round(cheapest_cpp, 2)

                # Find exact match
                exact_match_flight = None
                award_departure_time = parse_time(deal.get('departure_time'))
                award_flight_numbers = deal.get('flight_numbers', [])
                award_stops = deal.get('stops', [])

                for flight in flights:
                    if not flight.get('flights'):
                        continue
                    
                    cash_departure_time = parse_time(flight['flights'][0]['departure_airport'].get('time'))
                    cash_flight_numbers = [f.get('flight_number').replace(' ', '') for f in flight.get('flights', [])]
                    cash_layovers = [l.get('id') for l in flight.get('layovers', [])]
                    award_flight_numbers_normalized = [fn.replace(' ', '') for fn in award_flight_numbers]

                    # Match departure time (hour and minute)
                    time_match = award_departure_time and cash_departure_time and award_departure_time.hour == cash_departure_time.hour and award_departure_time.minute == cash_departure_time.minute
                    
                    # Match flight numbers
                    numbers_match = set(award_flight_numbers_normalized) == set(cash_flight_numbers)

                    # Match layovers
                    layovers_match = set(award_stops) == set(cash_layovers)

                    if time_match and numbers_match and layovers_match:
                        exact_match_flight = flight
                        break
            
                if exact_match_flight:
                    exact_price = exact_match_flight['price']
                    exact_cpp = (exact_price / points) * 100 if points > 0 else 0
                    deal[cabin]['exact_cash_price'] = exact_price
                    deal[cabin]['exact_cpp'] = round(exact_cpp, 2)
                    deal[cabin]['cash_flight_details'] = exact_match_flight
                else:
                    deal[cabin]['exact_cash_price'] = 'N/A'
                    deal[cabin]['exact_cpp'] = 'N/A'
                    deal[cabin]['cash_flight_details'] = None

        # Filter out deals that don't match the requested origin and destination
        filtered_deals = []
        for deal in processed_deals_list:
            deal_origin, deal_destination = deal['route'].split(' -> ')
            if deal_origin == origin and deal_destination == destination:
                filtered_deals.append(deal)

        return filtered_deals

    def _build_search_url(self, origin: str, destination: str, start_date: str, end_date: str) -> str:
        multiday = "true" if start_date != end_date else "false"
        depart_date_sec = end_date if multiday == "true" else start_date
        return (
            f"https://www.pointsyeah.com/search?cabins=Economy%2CPremium+Economy%2CBusiness%2CFirst"
            f"&cabin=Economy"
            f"&banks=Amex%2CCapital+One%2CChase"
            f"&airlineProgram=AR%2CAM%2CAC%2CKL%2CAS%2CAV%2CDL%2CEK%2CEY%2CAY%2CIB%2CB6%2CLH%2CQF%2CSK%2CSQ%2CNK%2CTP%2CTK%2CUA%2CVS"
            f"&tripType=1"
            f"&adults=1"
            f"&children=0"
            f"&departure={origin}"
            f"&arrival={destination}"
            f"&departDate={start_date}"
            f"&departDateSec={depart_date_sec}"
            f"&multiday={multiday}"
        )

    def _process_deals(self, deals_chunk: List[Dict[str, Any]], best_deals: Dict[Any, Any]):
        for deal in deals_chunk:
            if not deal.get("routes"): continue
            program_name, deal_date = deal.get("program"), deal.get("date")

            for route in deal["routes"]:
                booking_url = route.get("url", "") # Explicitly get URL from the route
                payment = route.get("payment", {})
                cabin, points = payment.get("cabin", "").lower(), payment.get("miles")
                if not cabin or points is None: continue
                segments = route.get("segments", [])
                if not segments: continue
                
                valid_segments = [s for s in segments if s.get("flight_number")]
                if not valid_segments:
                    continue

                # Get the correct arrival airport from the last segment
                departure_airport = valid_segments[0].get('da')
                arrival_airport = valid_segments[-1].get('aa')
                route_str = f"{departure_airport} -> {arrival_airport}"

                stops = [s.get('aa') for s in valid_segments[:-1]]
                airlines = list(set([s.get('flight_number')[:2] for s in valid_segments if s.get('flight_number')]))

                # Check for overnight layovers and calculate layover duration
                overnight_layover = False
                layover_duration = 0
                if len(valid_segments) > 1:
                    for i in range(len(valid_segments) - 1):
                        arrival_time = datetime.fromisoformat(valid_segments[i].get('at'))
                        departure_time = datetime.fromisoformat(valid_segments[i+1].get('dt'))
                        if arrival_time.date() != departure_time.date():
                            overnight_layover = True
                        layover_duration += (departure_time - arrival_time).total_seconds() / 60

                flight_numbers = [s.get("flight_number") for s in valid_segments if s.get("flight_number")]
                departure_time, arrival_time = valid_segments[0].get("dt"), valid_segments[-1].get("at")
                deal_key = (program_name, deal_date, route_str, departure_time, arrival_time)

                # Extract transfer info
                transfer_info = route.get("transfer", [])
                bonus_info = None
                if transfer_info:
                    for transfer in transfer_info:
                        if transfer.get("bonus_percentage", 0) > 0:
                            bonus_info = {
                                "bank": transfer.get("bank"),
                                "percentage": transfer.get("bonus_percentage"),
                                "end_date": transfer.get("bonus_end_date")
                            }
                            break # Assume one bonus is enough to highlight

                if deal_key not in best_deals:
                    best_deals[deal_key] = {
                        "program": program_name, "route": route_str, "date": deal_date,
                        "departure_time": departure_time, "arrival_time": arrival_time,
                        "duration_minutes": route.get("duration", 0),
                        "direct": len(valid_segments) == 1,
                        "stops": stops,
                        "airlines": airlines,
                        "overnight_layover": overnight_layover,
                        "layover_duration": layover_duration,
                        "economy": None, "premium": None,
                        "business": None, "first": None,
                        "flight_numbers": flight_numbers
                    }
                
                cabin_key = "premium" if "premium" in cabin else "business" if "business" in cabin else "first" if "first" in cabin else "economy"
                current_best = best_deals[deal_key].get(cabin_key)

                if current_best is None or points < current_best['points']:
                    best_deals[deal_key][cabin_key] = {
                        "points": points, 
                        "fees": f"${payment.get('tax')} {payment.get('currency')}",
                        "seats": payment.get("seats"),
                        "booking_url": booking_url,
                        "transfer_info": transfer_info,
                        "bonus": bonus_info
                    }

    async def close(self):
        """Closes the browser."""
        print("Closing browser...")
        if self.browser:
            await self.browser.close()

# --- Global scraper instance management ---
scraper_instance: Optional[PointsYeahScraper] = None

async def initialize_scraper(playwright: Playwright):
    """Initializes the global scraper instance."""
    global scraper_instance
    if scraper_instance is None:
        print("Initializing PointsYeah scraper at server startup...")
        load_airport_data()
        scraper_instance = PointsYeahScraper(playwright)
        await scraper_instance.start()
        print("PointsYeah scraper initialized successfully.")
    else:
        print("PointsYeah scraper already initialized.")

async def close_scraper():
    """Closes the global scraper instance."""
    global scraper_instance
    if scraper_instance:
        print("Closing PointsYeah scraper at server shutdown...")
        await scraper_instance.close()
        scraper_instance = None

async def scrape_pointsyeah(origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Main function to scrape PointsYeah."""
    global scraper_instance
    if scraper_instance is None:
        raise Exception("PointsYeah scraper has not been initialized.")
    
    return await scraper_instance.scrape(origin, destination, start_date, end_date)

async def main_test():
    playwright = await async_playwright().start()
    try:
        await initialize_scraper(playwright)
        
        deals = await scrape_pointsyeah("SEA", "JFK", "2025-10-04", "2025-10-04")
        if deals:
            print(f"Found {len(deals)} deals.")
            # output_filename = "deals.json"

            # # Write the deals to the JSON file
            # with open(output_filename, 'w') as f:
            #     json.dump(deals, f, indent=2)

    finally:
        await close_scraper()
        await playwright.stop()


if __name__ == '__main__':
    asyncio.run(main_test())