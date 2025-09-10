import os
import sys
from playwright.async_api import async_playwright, Browser, Playwright
from playwright_stealth import Stealth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
import re
import random
from typing import List, Dict, Any, Optional, Tuple
from scrapers.utils import parse_time, fetch_cash_prices, normalize_program_name, LEGEND
from datetime import datetime, timedelta
import pytz
import airportsdata
import functools

class PointsYeahScraper:
    CONCURRENCY_LIMIT = 3

    def __init__(self, playwright: Playwright, headless: bool = True):
        self.playwright: Playwright = playwright
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.LEGEND = LEGEND
        self.PROGRAM_CODES = {normalize_program_name(v): k for k, v in self.LEGEND["programs"].items()}
        self.BANK_CODES = {v: k for k, v in self.LEGEND["banks"].items()}
        self.CABIN_CODES_REVERSE = {v: k for k, v in self.LEGEND["cabin_codes"].items()}
        self.airports = airportsdata.load('IATA')

    # The 'create' classmethod is no longer needed with the new structure.

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
        # No need to stop playwright here, 'async with' handles it.

    async def search_flights(self, jobs: List[Dict[str, Any]]) -> str:
        if not self.browser:
            return json.dumps({"error": "Browser not initialized"})

        cash_price_tasks = []
        unique_cash_searches = set()
        for job in jobs:
            if job.get("job_type") == "matrix":
                origins, destinations = job.get("origins", []), job.get("destinations", [])
                start_date_str, end_date_str = job.get("start_date"), job.get("end_date")
                for o in origins:
                    for d in destinations:
                        cash_search_tuple = (o, d, start_date_str, end_date_str)
                        if cash_search_tuple not in unique_cash_searches:
                            cash_price_tasks.append(self._scrape_cash_prices(o, d, start_date_str, end_date_str))
                            unique_cash_searches.add(cash_search_tuple)
            elif job.get("job_type") == "multicity":
                for leg in ["leg1", "leg2"]:
                    if leg_data := job.get(leg):
                        cash_search_tuple = (leg_data["origin"], leg_data["destination"], leg_data["start_date"], leg_data["end_date"])
                        if cash_search_tuple not in unique_cash_searches:
                            cash_price_tasks.append(self._scrape_cash_prices(leg_data["origin"], leg_data["destination"], leg_data["start_date"], leg_data["end_date"]))
                            unique_cash_searches.add(cash_search_tuple)

        async def run_points_searches():
            script_dir = os.path.dirname(os.path.abspath(__file__))
            auth_file_path = os.path.join(script_dir, "auth_state.json")
            context_options = {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "viewport": {'width': 1920, 'height': 1080}, "locale": 'en-US',
                "timezone_id": 'America/New_York', "color_scheme": 'light',
                "storage_state": auth_file_path
            }
            
            contexts = [await self.browser.new_context(**context_options) for _ in range(self.CONCURRENCY_LIMIT)]
            semaphore = asyncio.Semaphore(self.CONCURRENCY_LIMIT)

            async def scrape_with_semaphore(context, job):
                async with semaphore:
                    await asyncio.sleep(random.uniform(1, 2))
                    job_type = job.get("job_type")
                    if job_type == "matrix":
                        return await self._scrape_matrix_search(context, job)
                    elif job_type == "multicity":
                        return await self._scrape_multicity_search(context, job)
                    return {}

            try:
                search_tasks = [scrape_with_semaphore(contexts[i % self.CONCURRENCY_LIMIT], job) for i, job in enumerate(jobs)]
                return await asyncio.gather(*search_tasks, return_exceptions=True)
            finally:
                await asyncio.gather(*(c.close() for c in contexts), return_exceptions=True)

        cash_future = asyncio.gather(*cash_price_tasks, return_exceptions=True)
        points_task = asyncio.create_task(run_points_searches())
        
        all_cash_prices_results, points_results = await asyncio.gather(cash_future, points_task)

        all_deals_dict: Dict[tuple, Tuple[int, dict]] = {}
        for result in points_results:
            if isinstance(result, Exception):
                print(f"A search task failed: {result}")
                continue
            
            for segments_key, (duration, program_options) in result.items():
                if segments_key not in all_deals_dict:
                    all_deals_dict[segments_key] = (duration, {})
                
                _, existing_options = all_deals_dict[segments_key]

                for program_code, option_data in program_options.items():
                    if program_code not in existing_options:
                        existing_options[program_code] = option_data
                    else:
                        existing_cabins = existing_options[program_code]['cabins']
                        new_cabins = option_data['cabins']
                        for cabin_code, cabin_deal in new_cabins.items():
                            if cabin_code not in existing_cabins or cabin_deal[0] < existing_cabins[cabin_code][0]:
                                existing_cabins[cabin_code] = cabin_deal
        
        valid_cash_results = [r for r in all_cash_prices_results if not isinstance(r, Exception)]
        self._match_cash_prices(all_deals_dict, valid_cash_results)

        if not all_deals_dict:
            return json.dumps({"legend": self.LEGEND, "deals": []}, indent=2)

        final_deals = []
        for segments, (duration, program_options) in all_deals_dict.items():
            options_list = [
                [
                    option_data['program'],
                    option_data['transfer_partners'],
                    option_data['url_params'],
                    option_data['cabins']
                ] for option_data in program_options.values()
            ]
            final_deals.append([list(segments), options_list, duration])

        result = {"legend": self.LEGEND, "deals": final_deals}
        return json.dumps(result, indent=2)

    async def _scrape_matrix_search(self, context: Any, job: Dict[str, Any]) -> Dict[Any, Any]:
        origins = job.get("origins", [])
        destinations = job.get("destinations", [])
        start_date = job.get("start_date")
        end_date = job.get("end_date")
        valid_routes = set(tuple(r) for r in job.get("valid_routes", []))

        page = await context.new_page()
        
        print(f"Searching MATRIX from {','.join(origins)} to {','.join(destinations)} between {start_date} and {end_date}...")
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

        search_url = self._build_matrix_url(origins, destinations, start_date, end_date)
        try:
            await page.goto(search_url, timeout=90000, wait_until='domcontentloaded')
            await asyncio.wait_for(search_done_future, timeout=90)
            print("MATRIX search complete, filtering results...")
            filtered_deals = {}
            for segments, (duration, program_options) in best_deals.items():
                if not segments: continue
                origin_code = segments[0][1]
                dest_code = segments[-1][2]
                if (origin_code, dest_code) in valid_routes:
                    filtered_deals[segments] = (duration, program_options)
            return filtered_deals
        except Exception as e:
            print(f"An error occurred during matrix scraping: {e.__class__.__name__}: {e}")
            print(f"Error accessing URL: {search_url}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"error_screenshot_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved to {screenshot_path}")
            return {}
        finally:
            await page.close()

    async def _scrape_multicity_search(self, context: Any, job: Dict[str, Any]) -> Dict[Any, Any]:
        leg1 = job.get("leg1")
        leg2 = job.get("leg2")

        page = await context.new_page()

        print(f"Searching MULTI-CITY from {leg1['origin']}-{leg1['destination']} and {leg2['origin']}-{leg2['destination']}...")
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
            search_url = self._build_multicity_url(leg1, leg2)
            await page.goto(search_url, timeout=90000, wait_until='domcontentloaded')
            await asyncio.wait_for(search_done_future, timeout=120)
            print("MULTI-CITY search complete, filtering results...")
            return best_deals
        except Exception as e:
            print(f"An error occurred during multicity scraping: {e.__class__.__name__}: {e}")
            return {}
        finally:
            await page.close()

    def _get_base_search_url(self) -> str:
        return (
            "https://www.pointsyeah.com/search?cabins=Economy%2CPremium+Economy%2CBusiness%2CFirst"
            "&cabin=Economy"
            "&banks=Amex%2CCapital+One%2CChase"
            "&airlineProgram=AR%2CAM%2CAC%2CKL%2CAS%2CAV%2CDL%2CEK%2CEY%2CAY%2CIB%2CB6%2CQF%2CSQ%2CTP%2CTK%2CUA%2CVS"
            "&adults=1"
            "&children=0"
        )

    def _build_matrix_url(self, origins: List[str], destinations: List[str], start_date: str, end_date: str) -> str:
        base_url = self._get_base_search_url()
        multiday = "true" if start_date != end_date else "false"
        depart_date_sec = end_date if multiday == "true" else start_date
        departure_str = ",".join(origins)
        arrival_str = ",".join(destinations)
        return (
            f"{base_url}"
            f"&tripType=1"
            f"&departure={departure_str}"
            f"&arrival={arrival_str}"
            f"&departDate={start_date}"
            f"&departDateSec={depart_date_sec}"
            f"&multiday={multiday}"
        )

    def _build_multicity_url(self, leg1: Dict[str, str], leg2: Dict[str, str]) -> str:
        base_url = self._get_base_search_url()
        return (
            f"{base_url}"
            f"&tripType=3"
            f"&departure={leg1['origin']}"
            f"&arrival={leg1['destination']}"
            f"&departDate={leg1['start_date']}"
            f"&departDateSec={leg1['end_date']}"
            f"&departure2={leg2['origin']}"
            f"&arrival2={leg2['destination']}"
            f"&departDate2={leg2['start_date']}"
            f"&departDateSec2={leg2['end_date']}"
            f"&multiday=false"
        )

    @functools.lru_cache(maxsize=None)
    def _get_program_code(self, code: Optional[str], program: Optional[str]) -> Optional[str]:
        program_code = code
        if not program_code:
            program_name = program
            normalized_program = normalize_program_name(program_name)
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
                        
                        layover_details = flight.get('layover_details', '')
                        stop_airports = tuple(sorted(re.findall(r'[A-Z]{3}', layover_details)))

                        key = (origin, destination, departure_date, departure_time_obj.hour, departure_time_obj.minute, num_stops)
                        
                        if key not in cash_flights_map:
                            cash_flights_map[key] = []
                        cash_flights_map[key].append({**flight, 'cabin_code': cash_cabin_code, 'stop_airports': stop_airports})
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
            
            award_num_stops = len(segments) - 1
            award_stops_tuple = tuple(sorted(s[2] for s in segments[:-1]))

            lookup_key = (award_origin, award_destination, award_departure_date, award_departure_time.hour, award_departure_time.minute, award_num_stops)
            
            potential_matches = cash_flights_map.get(lookup_key, [])
            if not potential_matches: continue

            for cash_flight in potential_matches:
                layover_match = False
                if award_num_stops == 0:
                    layover_match = True
                else:
                    if award_stops_tuple == cash_flight.get('stop_airports'):
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

import time
async def main_test():
    """Test function to run the scraper for a sample search."""
    scraper = None
    # Correctly initialize playwright with stealth
    async with Stealth().use_async(async_playwright()) as p:
        try:
            scraper = PointsYeahScraper(p)
            await scraper.start()
            
            jobs = [
                {
                    "job_type": "matrix",
                    "origins": ["SEA", "JFK", "SFO"],
                    "destinations": ["LHR", "CDG"],
                    "start_date": "2025-10-20",
                    "end_date": "2025-10-24",
                    "valid_routes": [
                        ("SEA", "LHR"),
                        ("JFK", "LHR"),
                        ("SFO", "CDG")
                    ]
                },
                {
                    "job_type": "matrix",
                    "origins": ["LHR", "CDG"],
                    "destinations": ["BKK", "NRT", "ICN"],
                    "start_date": "2025-10-24",
                    "end_date": "2025-10-28",
                    "valid_routes": [
                        ("LHR", "BKK"),
                        ("LHR", "NRT"),
                        ("CDG", "NRT"),
                        ("CDG", "ICN")
                    ]
                },
                {
                    "job_type": "matrix",
                    "origins": ["YYZ"],
                    "destinations": ["YVR"],
                    "start_date": "2025-11-24",
                    "end_date": "2025-11-27",
                    "valid_routes": [
                        ("YYZ", "YVR")
                    ]
                },
                {
                    "job_type": "matrix",
                    "origins": ["YYZ"],
                    "destinations": ["YVR"],
                    "start_date": "2025-12-24",
                    "end_date": "2025-12-27",
                    "valid_routes": [
                        ("YYZ", "YVR")
                    ]
                },
                {
                    "job_type": "matrix",
                    "origins": ["YYZ"],
                    "destinations": ["YVR"],
                    "start_date": "2025-10-24",
                    "end_date": "2025-10-27",
                    "valid_routes": [
                        ("YYZ", "YVR")
                    ]
                },
                {
                    "job_type": "matrix",
                    "origins": ["DXB"],
                    "destinations": ["HKG", "SIN"],
                    "start_date": "2025-12-24",
                    "end_date": "2025-12-28",
                    "valid_routes": [
                        ("DXB", "HKG"),
                        ("DXB", "SIN"),
                    ]
                },
                # {
                #     "job_type": "multicity",
                #     "leg1": {"origin": "LHR", "destination": "HKG", "start_date": "2025-11-01", "end_date": "2025-11-02"},
                #     "leg2": {"origin": "HKG", "destination": "TPE", "start_date": "2025-11-15", "end_date": "2025-11-16"}
                # }
            ]

            start_time = time.perf_counter()
            deals_json = await scraper.search_flights(jobs)
            
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