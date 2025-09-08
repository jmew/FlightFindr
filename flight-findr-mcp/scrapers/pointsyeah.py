import os
import sys
from playwright.async_api import async_playwright, Page, Browser, Playwright
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
import re
from typing import List, Dict, Any, Optional
from scrapers.utils import parse_time, fetch_cash_prices, PROGRAM_MAPPING
from datetime import datetime, timedelta

KEY_LEGEND = {
    # Deal fields
    "program": "pr",
    "route": "rt",
    "departure_time": "dt",
    "arrival_time": "at",
    "duration_minutes": "dm",
    "stops": "s",
    "airlines": "al",
    "overnight_layover": "ol",
    "layover_duration": "ld",
    "flight_numbers": "fn",
    "booking_url": "bu",
    "transfer_info": "ti",
    "layover_lengths": "ll",
    "economy": "e",
    "premium": "p",
    "business": "b",
    "first": "f",

    # Cabin fields
    "points": "pt",
    "fees": "fe",
    "bonus": "bn",
    "exact_cash_price": "ecp",
    "exact_cpp": "epp",

    # Slimmer Transfer info fields
    "bank": "bk",
    "bonus_percentage": "bp",
    "bonus_end_date": "bed",

    # Bank name mappings
    "c": "Chase Ultimate Rewards",
    "a": "American Exp Membership Rewards",
    "co": "Capital One",
    "t": "Citi Thank You Points",
}

def clean_and_compress_dict(data, legend):
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if v is not None and v != "" and v != []:
                new_key = legend.get(k, k)
                cleaned_v = clean_and_compress_dict(v, legend)
                if cleaned_v is not None and cleaned_v != "" and cleaned_v != []:
                    new_dict[new_key] = cleaned_v
        return new_dict if new_dict else None
    elif isinstance(data, list):
        return [clean_and_compress_dict(i, legend) for i in data]
    else:
        return data

def parse_layover_lengths(layover_str: str) -> List[int]:
    if not layover_str:
        return []
    
    durations = []
    # Regex to find durations like "1 hr 41 min", "2 hr", "55 min"
    pattern = r'(\d+)\s+hr(?:\s+(\d+)\s+min)?|(\d+)\s+min'
    matches = re.findall(pattern, layover_str)
    
    for match in matches:
        hr1, min1, min2 = match
        hours = int(hr1) if hr1 else 0
        minutes = int(min1) if min1 else int(min2) if min2 else 0
        total_minutes = hours * 60 + minutes
        durations.append(total_minutes)
        
    return durations

class PointsYeahScraper:
    def __init__(self, playwright: Playwright, headless: bool = True):
        self.playwright: Playwright = playwright
        self.headless = headless
        self.browser: Optional[Browser] = None

    @classmethod
    async def create(cls, headless: bool = True):
        playwright = await async_playwright().start()
        scraper = cls(playwright, headless)
        await scraper.start()
        return scraper

    async def start(self):
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

    async def close(self):
        print("Closing browser...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def search_flights(self, searches: List[Dict[str, Any]]) -> str:
        all_deals = []
        
        search_tasks = []
        for search in searches:
            origin = ",".join(search['origin_airports'])
            destination = ",".join(search['destination_airports'])
            start_date_str = search['start_date']
            end_date_str = search['end_date']

            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
            
            if (end_date - start_date).days > 4:
                current_start_date = start_date
                while current_start_date < end_date:
                    current_end_date = current_start_date + timedelta(days=4)
                    if current_end_date > end_date:
                        current_end_date = end_date
                    
                    search_tasks.append(
                        self._scrape_one_search(
                            origin,
                            destination,
                            current_start_date.strftime('%Y-%m-%d'),
                            current_end_date.strftime('%Y-%m-%d')
                        )
                    )
                    current_start_date = current_end_date
            else:
                search_tasks.append(
                    self._scrape_one_search(
                        origin,
                        destination,
                        start_date_str,
                        end_date_str
                    )
                )
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"A search task failed: {result}")
            else:
                all_deals.extend(result)

        if not all_deals:
            return json.dumps({"legend": KEY_LEGEND, "all_deals": []}, indent=2)

        merged_deals = {}
        for deal in all_deals:
            deal_id = (
                deal.get("program"),
                deal.get("route"),
                deal.get("departure_time"),
                deal.get("arrival_time"),
            )

            if deal_id not in merged_deals:
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
                        or new_cabin_data["points"] < existing_cabin_data.get("points")
                    ):
                        existing_deal[cabin] = new_cabin_data
        
        unique_deals = list(merged_deals.values())

        cleaned_deals = clean_and_compress_dict(unique_deals, KEY_LEGEND)

        result = {
            "legend": KEY_LEGEND,
            "all_deals": cleaned_deals,
        }

        return json.dumps(result, indent=2)

    async def _scrape_one_search(self, origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        page = await self._create_new_page()

        print(f"Searching for flights from {origin} to {destination} between {start_date} and {end_date}...")
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

        page.on("response", handle_response)

        try:
            search_url = self._build_search_url(origin, destination, start_date, end_date)
            points_task = asyncio.create_task(page.goto(search_url, timeout=90000, wait_until='domcontentloaded'))
            cash_task = asyncio.create_task(self._scrape_cash_prices(origin, destination, start_date, end_date))

            await asyncio.wait_for(search_done_future, timeout=240)
            print("Search complete (detected 'done' signal).")

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
            page.remove_listener("response", handle_response)
            await page.context.close()

        self._match_cash_prices(processed_deals_list, cash_prices_list)

        return [
            deal for deal in processed_deals_list
            if deal['route'].split(' -> ')[0] in origin and deal['route'].split(' -> ')[1] in destination
        ]

    def _process_deals(self, deals_chunk: List[Dict[str, Any]], best_deals: Dict[Any, Any]):
        bank_legend = {
            "Chase Ultimate Rewards": "c",
            "American Exp Membership Rewards": "a",
            "Capital One": "co",
            "Citi Thank You Points": "t",
        }
        for deal in deals_chunk:
            if not deal.get("routes"): continue
            program_name = deal.get("program")
            normalized_program = self._normalize_program_name(program_name)
            if not normalized_program:
                continue

            for route in deal["routes"]:
                booking_url = route.get("url", "")
                payment = route.get("payment", {})
                cabin, points = payment.get("cabin", "").lower(), payment.get("miles")
                if not cabin or points is None: continue
                
                valid_segments = [s for s in route.get("segments", []) if s.get("flight_number")]
                if not valid_segments: continue

                departure_airport = valid_segments[0].get('da')
                arrival_airport = valid_segments[-1].get('aa')
                route_str = f"{departure_airport} -> {arrival_airport}"
                
                departure_time, arrival_time = valid_segments[0].get("dt"), valid_segments[-1].get("at")
                deal_key = (normalized_program, route_str, departure_time, arrival_time)

                if deal_key not in best_deals:
                    origin_code, dest_code = route_str.split(" -> ")
                    stops = [s.get('aa') for s in valid_segments[:-1]]
                    
                    overnight_layover = False
                    layover_duration = 0
                    if len(valid_segments) > 1:
                        for i in range(len(valid_segments) - 1):
                            arr_time = datetime.fromisoformat(valid_segments[i].get('at'))
                            dep_time = datetime.fromisoformat(valid_segments[i+1].get('dt'))
                            if arr_time.date() != dep_time.date():
                                overnight_layover = True
                            layover_duration += (dep_time - arr_time).total_seconds() / 60
                    
                    transfer_info_raw = route.get("transfer") or []
                    transfer_info = [
                        bank_legend.get(t.get("bank")) for t in transfer_info_raw 
                        if t.get("bank") and t.get("bank") not in ["Bilt", "WF"] and bank_legend.get(t.get("bank"))
                    ]

                    best_deals[deal_key] = {
                        "program": normalized_program,
                        "route": route_str,
                        "departure_time": departure_time,
                        "arrival_time": arrival_time,
                        "duration_minutes": route.get("duration", 0),
                        "stops": stops,
                        "airlines": list(set([s.get('flight_number')[:2] for s in valid_segments if s.get('flight_number')])),
                        "overnight_layover": overnight_layover,
                        "layover_duration": layover_duration,
                        "flight_numbers": [s.get("flight_number") for s in valid_segments if s.get("flight_number")],
                        "booking_url": booking_url,
                        "transfer_info": transfer_info,
                        "layover_lengths": None,
                        "economy": None, "premium": None, "business": None, "first": None
                    }

                cabin_key = "premium" if "premium" in cabin else "business" if "business" in cabin else "first" if "first" in cabin else "economy"
                current_best = best_deals[deal_key].get(cabin_key)

                if current_best is None or points < current_best.get('points', float('inf')):
                    bonus_info = next((
                        {"bank": t.get("bank"), "percentage": t.get("bonus_percentage"), "end_date": t.get("bonus_end_date")}
                        for t in transfer_info_raw if t.get("bonus_percentage", 0) > 0
                    ), None)

                    best_deals[deal_key][cabin_key] = {
                        "points": points,
                        "fees": f"${payment.get('tax')}",
                        "bonus": bonus_info
                    }

    def _match_cash_prices(self, deals: List[Dict[str, Any]], cash_prices_data: List[Dict[str, Any]]):
        if not deals or not any(c.get('flights') for c in cash_prices_data):
            return

        for deal in deals:
            award_departure_time_str = deal.get('departure_time')
            if not award_departure_time_str:
                continue
            award_departure_datetime = datetime.fromisoformat(award_departure_time_str)
            award_departure_time = award_departure_datetime.time()
            award_departure_date = award_departure_datetime.date()

            for cabin_prices in cash_prices_data:
                cabin = cabin_prices['cabin']
                deal_cabin_key = 'premium' if cabin == 'premium-economy' else cabin

                if not deal.get(deal_cabin_key) or not deal[deal_cabin_key].get('points'):
                    continue

                flights = cabin_prices.get('flights', [])
                if not flights:
                    continue
                
                points = deal[deal_cabin_key]['points']

                award_num_stops = len(deal.get('stops', []))
                award_stops = deal.get('stops', [])

                exact_match_flight = None
                if award_departure_time:
                    for flight in flights:
                        cash_departure_time = parse_time(flight.get('departure'))
                        if not cash_departure_time:
                            continue
                        
                        cash_departure_date_str = flight.get('date')
                        if not cash_departure_date_str:
                            continue
                        cash_departure_date = datetime.fromisoformat(cash_departure_date_str).date()

                        date_match = (award_departure_date == cash_departure_date)
                        time_match = (award_departure_time.hour == cash_departure_time.hour and
                                      award_departure_time.minute == cash_departure_time.minute)
                        stops_match = (award_num_stops == flight.get('stops'))
                        
                        layover_match = False
                        if not stops_match:
                            pass
                        elif award_num_stops == 0:
                            layover_match = True
                        else:
                            cash_layover_details = flight.get('layover_details')
                            if cash_layover_details:
                                cash_stop_airports = re.findall(r'[A-Z]{3}', cash_layover_details)
                                if set(award_stops) == set(cash_stop_airports):
                                    layover_match = True

                        if date_match and time_match and stops_match and layover_match:
                            exact_match_flight = flight
                            break
                
                if exact_match_flight:
                    layover_details = exact_match_flight.get("layover_details")
                    if layover_details:
                        deal["layover_lengths"] = parse_layover_lengths(layover_details)
                    
                    try:
                        exact_price_str = exact_match_flight['price'].replace('$', '').replace(',', '')
                        exact_price = float(exact_price_str)
                        deal[deal_cabin_key]['exact_cash_price'] = exact_price
                        deal[deal_cabin_key]['exact_cpp'] = round((exact_price / points) * 100, 2) if points > 0 else 0
                    except (ValueError, TypeError, KeyError):
                        pass # Omit if not available

    async def _scrape_cash_prices(self, origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        dates = []
        current_date = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        while current_date <= end:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        cash_price_tasks = [fetch_cash_prices(origin, destination, dates, cabin) for cabin in ['economy', 'premium-economy', 'business', 'first']]
        return await asyncio.gather(*cash_price_tasks)

    async def _create_new_page(self) -> Page:
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

    @staticmethod
    def _normalize_program_name(program_name: Optional[str]) -> Optional[str]:
        if not program_name:
            return None
        lower_program_name = program_name.strip().lower()
        return PROGRAM_MAPPING.get(lower_program_name, program_name.title())

async def main_test():
    """Test function to run the scraper for a sample search."""
    scraper = None
    try:
        scraper = await PointsYeahScraper.create()
        searches = [
            #{"origin_airports": ["SEA"], "destination_airports": ["JFK"], "start_date": "2025-10-04", "end_date": "2025-10-04"},
            {"origin_airports": ["SEA"], "destination_airports": ["LHR"], "start_date": "2025-10-04", "end_date": "2025-10-10"},
            {"origin_airports": ["LHR"], "destination_airports": ["HKG"], "start_date": "2025-10-08", "end_date": "2025-10-14"},
            {"origin_airports": ["HKG"], "destination_airports": ["SEA"], "start_date": "2025-10-10", "end_date": "2025-10-18"},
        ]
        deals_json = await scraper.search_flights(searches)
        
        deals_data = json.loads(deals_json)
        print(f"Found {len(deals_data.get('all_deals', []))} deals.")
        with open("deals.json", 'w') as f:
            json.dump(deals_data, f, indent=2)

    finally:
        if scraper:
            await scraper.close()

if __name__ == '__main__':
    asyncio.run(main_test())