import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright, Page, Browser, Playwright, TimeoutError
import json
import asyncio
import os
from typing import List, Dict, Any, Optional
from scrapers.utils import parse_time, get_flight_cash_prices
from datetime import datetime
from fast_flights import get_flights, FlightData, Passengers



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
            await self.page.goto(search_url, timeout=90000, wait_until='domcontentloaded')
            await asyncio.wait_for(search_done_future, timeout=120)
            print("Search complete (detected 'done' signal).")
        except asyncio.TimeoutError:
            print("Timed out waiting for the 'done' signal from the server.")
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
        finally:
            self.page.remove_listener("response", handle_response)
        
        processed_deals = list(best_deals.values())

        # Commenting this out for now becvause its slow
        # cash_price_tasks = []
        # for deal in processed_deals:
        #     for cabin in ['economy', 'premium', 'business', 'first']:
        #         cash_price_tasks.append(get_flight_cash_prices(deal, cabin))
        
        # await asyncio.gather(*cash_price_tasks)

        return processed_deals

    def _build_search_url(self, origin: str, destination: str, start_date: str, end_date: str) -> str:
        multiday = "true" if start_date != end_date else "false"
        depart_date_sec = end_date if multiday == "true" else start_date
        return (
            f"https://www.pointsyeah.com/search?cabins=Economy%2CPremium+Economy%2CBusiness%2CFirst"
            f"&cabin=Economy"
            f"&banks=Amex%2CCapital+One%2CChase%2CBilt"
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
            route_str = f"{deal.get('departure')} -> {deal.get('arrival')}"

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
        
        deals = await scrape_pointsyeah("SEA", "GEG", "2025-10-04", "2025-10-04")
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