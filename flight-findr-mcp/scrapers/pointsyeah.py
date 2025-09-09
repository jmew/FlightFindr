import os
import sys
from playwright.async_api import async_playwright, Page, Browser, Playwright
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from scrapers.utils import parse_time, fetch_cash_prices, PROGRAM_MAPPING, LEGEND
from datetime import datetime, timedelta
import pytz
import airportsdata
import functools

class PointsYeahScraper:
    def __init__(self, playwright: Playwright, headless: bool = True):
        self.playwright: Playwright = playwright
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.LEGEND = LEGEND
        self.PROGRAM_CODES = {self._normalize_program_name(v): k for k, v in self.LEGEND["programs"].items()}
        self.BANK_CODES = {v: k for k, v in self.LEGEND["banks"].items()}
        self.CABIN_CODES_REVERSE = {v: k for k, v in self.LEGEND["cabin_codes"].items()}
        self.airports = airportsdata.load('IATA')

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
        if not self.browser:
            return json.dumps({"error": "Browser not initialized"})

        # 1. Aggregate and run all cash price searches
        cash_price_tasks = []
        unique_cash_searches = set()
        for search in searches:
            origin = ",".join(search['origin_airports'])
            destination = ",".join(search['destination_airports'])
            start_date_str = search['start_date']
            end_date_str = search['end_date']
            
            cash_search_tuple = (origin, destination, start_date_str, end_date_str)
            if cash_search_tuple not in unique_cash_searches:
                cash_price_tasks.append(self._scrape_cash_prices(origin, destination, start_date_str, end_date_str))
                unique_cash_searches.add(cash_search_tuple)
        
        all_cash_prices_results = await asyncio.gather(*cash_price_tasks, return_exceptions=True)
        
        valid_cash_results = [r for r in all_cash_prices_results if not isinstance(r, Exception)]

        # 2. Create and run points searches
        script_dir = os.path.dirname(os.path.abspath(__file__))
        auth_file_path = os.path.join(script_dir, "auth_state.json")
        context_options = {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "viewport": {'width': 1920, 'height': 1080},
            "locale": 'en-US',
            "timezone_id": 'America/New_York',
            "color_scheme": 'light',
            "storage_state": auth_file_path
        }
        context = await self.browser.new_context(**context_options)
        
        search_args_list = []
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
                    
                    search_args_list.append(
                        (origin, destination, current_start_date.strftime('%Y-%m-%d'), current_end_date.strftime('%Y-%m-%d'))
                    )
                    current_start_date = current_end_date
            else:
                search_args_list.append(
                    (origin, destination, start_date_str, end_date_str)
                )
        
        CONCURRENCY_LIMIT = 3
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def scrape_with_semaphore(origin, dest, start, end):
            async with semaphore:
                return await self._scrape_one_search(context, origin, dest, start, end)

        search_tasks = [scrape_with_semaphore(origin, dest, start, end) for origin, dest, start, end in search_args_list]
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        await context.close()

        # 3. Process points results
        all_deals_dict: Dict[tuple, Tuple[int, dict]] = {}
        for result in results:
            if isinstance(result, Exception):
                print(f"A search task failed: {result}")
                continue
            
            for segments_key, (duration, program_options) in result.items():
                if segments_key not in all_deals_dict:
                    all_deals_dict[segments_key] = (duration, {})
                
                existing_duration, existing_options = all_deals_dict[segments_key]

                for program_code, option_data in program_options.items():
                    if program_code not in existing_options:
                        existing_options[program_code] = option_data
                    else:
                        # Merge cabins, keeping the cheaper one
                        existing_cabins = existing_options[program_code]['cabins']
                        new_cabins = option_data['cabins']
                        for cabin_code, cabin_deal in new_cabins.items():
                            if cabin_code not in existing_cabins or cabin_deal[0] < existing_cabins[cabin_code][0]:
                                existing_cabins[cabin_code] = cabin_deal
        
        # 4. Match cash prices
        self._match_cash_prices(all_deals_dict, valid_cash_results)

        # 5. Format and return
        if not all_deals_dict:
            return json.dumps({"legend": self.LEGEND, "deals": []}, indent=2)

        final_deals = []
        for segments, (duration, program_options) in all_deals_dict.items():
            options_list = []
            for option_data in program_options.values():
                options_list.append([
                    option_data['program'],
                    option_data['transfer_partners'],
                    option_data['url_params'],
                    option_data['cabins']
                ])
            final_deals.append([list(segments), options_list, duration])

        result = {
            "legend": self.LEGEND,
            "deals": final_deals,
        }

        return json.dumps(result, indent=2)

    async def _scrape_one_search(self, context: Any, origin: str, destination: str, start_date: str, end_date: str) -> Dict[Any, Any]:
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
            asyncio.create_task(page.goto(search_url, timeout=90000, wait_until='domcontentloaded'))

            await asyncio.wait_for(search_done_future, timeout=150)
            print("Search complete (detected 'done' signal).")

            filtered_deals = {}
            for segments, (duration, program_options) in best_deals.items():
                origin_code = segments[0][1]
                dest_code = segments[-1][2]
                if origin_code in origin and dest_code in destination:
                    filtered_deals[segments] = (duration, program_options)

            return filtered_deals

        except asyncio.TimeoutError:
            print("Timed out waiting for the 'done' signal from the server.")
            # there might be partial deals still that were parsed with the timeout, so use those partial data
            filtered_deals = {}
            for segments, (duration, program_options) in best_deals.items():
                origin_code = segments[0][1]
                dest_code = segments[-1][2]
                if origin_code in origin and dest_code in destination:
                    filtered_deals[segments] = (duration, program_options)

            return filtered_deals
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            return {}
        finally:
            page.remove_listener("response", handle_response)
            await page.close()

    @functools.lru_cache(maxsize=None)
    def _get_program_code(self, code: Optional[str], program: Optional[str]) -> Optional[str]:
        program_code = code
        if not program_code:
            program_name = program
            normalized_program = self._normalize_program_name(program_name)
            if not normalized_program:
                return None
            program_code = self.PROGRAM_CODES.get(normalized_program)
        return program_code

    @functools.lru_cache(maxsize=None)
    def _get_timezone(self, airport_code: str) -> Optional[pytz.BaseTzInfo]:
        try:
            tz_str = self.airports[airport_code]['tz']
            return pytz.timezone(tz_str)
        except (KeyError, pytz.UnknownTimeZoneError):
            return None

    def _calculate_duration(self, valid_segments: List[Dict[str, Any]], route: Dict[str, Any]) -> int:
        dep_tz = self._get_timezone(valid_segments[0]['da'])
        arr_tz = self._get_timezone(valid_segments[-1]['aa'])

        if not dep_tz or not arr_tz:
            return route.get("duration", 0)

        dep_time_naive = datetime.fromisoformat(valid_segments[0]['dt'])
        arr_time_naive = datetime.fromisoformat(valid_segments[-1]['at'])

        dep_time_aware = dep_tz.localize(dep_time_naive)
        arr_time_aware = arr_tz.localize(arr_time_naive)

        return round((arr_time_aware - dep_time_aware).total_seconds() / 60)

    def _extract_segments_data(self, valid_segments: List[Dict[str, Any]]) -> Tuple[Tuple[Any, ...], ...]:
        segments_data = []
        for i, s in enumerate(valid_segments):
            layover_mins = 0
            if i < len(valid_segments) - 1:
                arr_time = datetime.fromisoformat(s.get('at'))
                dep_time = datetime.fromisoformat(valid_segments[i+1].get('dt'))
                layover_mins = round((dep_time - arr_time).total_seconds() / 60)
            
            flight_number = s.get('flight_number')
            da = s.get('da')
            aa = s.get('aa')
            dt = s.get('dt')
            at = s.get('at')

            segment_tuple = (
                flight_number, da, aa,
                dt, at, layover_mins
            )
            segments_data.append(segment_tuple)
        return tuple(segments_data)

    def _get_booking_option(self, route: Dict[str, Any], program_code: str) -> Dict[str, Any]:
        bank_legend_short = {
            "Chase Ultimate Rewards": "chase",
            "American Exp Membership Rewards": "amex",
            "Capital One": "c1",
            "Citi Thank You Points": "citi",
            "Bilt": "bilt"
        }
        transfer_info_raw = route.get("transfer") or []
        transfer_partners = sorted([
            bank_legend_short.get(t.get("bank")) for t in transfer_info_raw 
            if t.get("bank") and bank_legend_short.get(t.get("bank"))
        ])
        booking_url = route.get("url", "")
        url_params = booking_url.split('?')[1] if '?' in booking_url else ""
        return {
            "program": program_code,
            "transfer_partners": transfer_partners,
            "url_params": url_params,
            "cabins": {}
        }

    def _process_deals(self, deals_chunk: List[Dict[str, Any]], best_deals: Dict[Any, Any]):
        for deal in deals_chunk:
            if not deal.get("routes"): continue
            
            program_code = self._get_program_code(deal.get("code"), deal.get("program"))
            if not program_code: continue

            for route in deal["routes"]:
                payment = route.get("payment", {})
                cabin, points = payment.get("cabin", "").lower(), payment.get("miles")
                if not cabin or points is None: continue
                
                valid_segments = [s for s in route.get("segments", []) if s.get("flight_number")]
                if not valid_segments: continue

                try:
                    duration_minutes = self._calculate_duration(valid_segments, route)
                    segments_key = self._extract_segments_data(valid_segments)

                    if segments_key not in best_deals:
                        best_deals[segments_key] = (duration_minutes, {})
                    
                    options_dict = best_deals[segments_key][1]
                    option_data = options_dict.get(program_code)

                    if not option_data:
                        option_data = self._get_booking_option(route, program_code)
                        options_dict[program_code] = option_data

                    cabin_code = "Y"
                    if "premium" in cabin: cabin_code = "W"
                    elif "business" in cabin: cabin_code = "J"
                    elif "first" in cabin: cabin_code = "F"
                    
                    cabin_deal_data = [points, payment.get('tax'), None, None]

                    existing_cabin_deal = option_data["cabins"].get(cabin_code)
                    if not existing_cabin_deal or points < existing_cabin_deal[0]:
                        option_data["cabins"][cabin_code] = cabin_deal_data
                except TypeError as e:
                    print(f"Error processing deal: {e}")
                    print(f"Problematic segments: {valid_segments}")

    def _match_cash_prices(self, deals_dict: Dict[Any, Any], cash_searches_results: List[Dict[str, Any]]):
        if not deals_dict or not cash_searches_results:
            return

        cash_flights_map = {}
        for cash_search in cash_searches_results:
            if isinstance(cash_search, Exception): continue

            origin = cash_search.get('origin')
            destination = cash_search.get('destination')
            cabin_prices_data = cash_search.get('cabin_prices', [])

            for cabin_prices in cabin_prices_data:
                cabin = cabin_prices.get('cabin', '')
                cash_cabin_code = "Y"
                if "premium" in cabin: cash_cabin_code = "W"
                elif "business" in cabin: cash_cabin_code = "J"
                elif "first" in cabin: cash_cabin_code = "F"

                for flight in cabin_prices.get('flights', []):
                    try:
                        departure_time_obj = parse_time(flight.get('departure'))
                        if not departure_time_obj: continue

                        date_str = flight.get('date')
                        if not date_str: continue
                        departure_date = datetime.fromisoformat(date_str).date()

                        num_stops = flight.get('stops', -1)
                        
                        # Use the origin/destination from the preserved context
                        key = (origin, destination, departure_date, departure_time_obj.hour, departure_time_obj.minute, num_stops)
                        
                        if key not in cash_flights_map:
                            cash_flights_map[key] = []
                        cash_flights_map[key].append({**flight, 'cabin_code': cash_cabin_code})
                    except (ValueError, TypeError):
                        continue

        for segments, (duration, program_options) in deals_dict.items():
            if not segments: continue
            
            first_segment = segments[0]
            last_segment = segments[-1]
            
            award_origin = first_segment[1]
            award_destination = last_segment[2]
            award_departure_time_str = first_segment[3]
            if not award_departure_time_str: continue
            
            award_departure_datetime = datetime.fromisoformat(award_departure_time_str)
            award_departure_time = award_departure_datetime.time()
            award_departure_date = award_departure_datetime.date()
            
            award_stops_airports = [s[2] for s in segments[:-1]]
            award_num_stops = len(award_stops_airports)

            lookup_key = (award_origin, award_destination, award_departure_date, award_departure_time.hour, award_departure_time.minute, award_num_stops)
            
            potential_matches = cash_flights_map.get(lookup_key, [])
            if not potential_matches: continue

            for cash_flight in potential_matches:
                layover_match = False
                if award_num_stops == 0:
                    layover_match = True
                else:
                    cash_layover_details = cash_flight.get('layover_details')
                    if cash_layover_details:
                        cash_stop_airports = re.findall(r'[A-Z]{3}', cash_layover_details)
                        if set(award_stops_airports) == set(cash_stop_airports):
                            layover_match = True
                
                if layover_match:
                    try:
                        price_str = cash_flight['price'].replace('$', '').replace(',', '')
                        price = float(price_str)
                        cash_cabin_code = cash_flight['cabin_code']
                        
                        for program_code, option_data in program_options.items():
                            if cash_cabin_code in option_data['cabins']:
                                cabin_deal = option_data['cabins'][cash_cabin_code]
                                points = cabin_deal[0]
                                cabin_deal[2] = price
                                cabin_deal[3] = round((price / points) * 100, 2) if points > 0 else 0
                    except (ValueError, TypeError, KeyError):
                        continue

    async def _scrape_cash_prices(self, origin: str, destination: str, start_date: str, end_date: str) -> Dict[str, Any]:
        dates = []
        current_date = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        while current_date <= end:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        cash_price_tasks = [fetch_cash_prices(origin, destination, dates, cabin) for cabin in ['economy', 'premium-economy', 'business', 'first']]
        results = await asyncio.gather(*cash_price_tasks)
        return {"origin": origin, "destination": destination, "cabin_prices": results}

    def _build_search_url(self, origin: str, destination: str, start_date: str, end_date: str) -> str:
        multiday = "true" if start_date != end_date else "false"
        depart_date_sec = end_date if multiday == "true" else start_date
        return (
            f"https://www.pointsyeah.com/search?cabins=Economy%2CPremium+Economy%2CBusiness%2CFirst"
            f"&cabin=Economy"
            f"&banks=Amex%2CCapital+One%2CChase"
            f"&airlineProgram=AR%2CAM%2CAC%2CKL%2CAS%2CAV%2CDL%2CEK%2CEY%2CAY%2CIB%2CB6%2CQF%2CSQ%2CTP%2CTK%2CUA%2CVS"
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
    @functools.lru_cache(maxsize=None)
    def _normalize_program_name(program_name: Optional[str]) -> Optional[str]:
        if not program_name:
            return None
        lower_program_name = program_name.strip().lower()
        return PROGRAM_MAPPING.get(lower_program_name, program_name.strip())

import time
async def main_test():
    """Test function to run the scraper for a sample search."""
    scraper = None
    try:
        scraper = await PointsYeahScraper.create()
        searches = [
            # {"origin_airports": ["SEA"], "destination_airports": ["JFK"], "start_date": "2025-10-04", "end_date": "2025-10-04"},
            #Test for multi-city, commented out for now
            {"origin_airports": ["SEA"], "destination_airports": ["LHR"], "start_date": "2025-10-04", "end_date": "2025-10-10"},
            {"origin_airports": ["LHR"], "destination_airports": ["HKG"], "start_date": "2025-10-08", "end_date": "2025-10-14"},
            {"origin_airports": ["HKG"], "destination_airports": ["SEA"], "start_date": "2025-10-10", "end_date": "2025-10-18"},
        ]
        start_time = time.perf_counter()
        deals_json = await scraper.search_flights(searches)
        
        deals_data = json.loads(deals_json)
        print(f"Found {len(deals_data.get('deals', []))} deals.")
        end_time = time.perf_counter()
        
        flight_count = 0
        for deal in deals_data.get('deals', []):
            options = deal[1]
            for option in options:
                cabins = option[3]
                flight_count += len(cabins)
        print(f"Found {flight_count} individual flight options.")

        duration = end_time - start_time

        print(f"The search took {duration} seconds.")

        # with open("deals.json", 'w') as f:
        #     json.dump(deals_data, f, indent=2)

    finally:
        if scraper:
            await scraper.close()

if __name__ == '__main__':
    asyncio.run(main_test())