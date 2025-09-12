import os
import sys
from playwright.async_api import async_playwright, Browser, Playwright
from playwright_stealth import Stealth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
import re
import random
import statistics
from typing import List, Dict, Any, Optional, Tuple
from scrapers.utils import parse_time, fetch_cash_prices, normalize_program_name, LEGEND
from datetime import datetime, timedelta
import pytz
import airportsdata
import functools
from urllib.parse import parse_qs, urlencode
from fake_useragent import UserAgent

class PointsYeahScraper:
    CONCURRENCY_LIMIT = 5

    def __init__(self, headless: bool = True):
        self.playwright: Optional[Playwright] = None
        self.headless = headless
        self.browser: Optional[Browser] = None
        self._cm = None
        self.ua = UserAgent()
        self.LEGEND = LEGEND
        self.PROGRAM_CODES = {normalize_program_name(v): k for k, v in self.LEGEND["programs"].items()}
        self.BANK_CODES = {v: k for k, v in self.LEGEND["banks"].items()}
        self.CABIN_CODES_REVERSE = {v: k for k, v in self.LEGEND["cabin_codes"].items()}
        self.airports = airportsdata.load('IATA')

    @classmethod
    async def create(cls, headless: bool = True):
        """Creates and starts a new scraper instance."""
        instance = cls(headless=headless)
        instance._cm = Stealth().use_async(async_playwright())
        instance.playwright = await instance._cm.__aenter__()
        await instance.start()
        return instance

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
        print("Closing scraper resources...")
        if self.browser and self.browser.is_connected():
            print("Closing browser...")
            try:
                await asyncio.wait_for(self.browser.close(), timeout=5.0)
                print("Browser closed.")
            except asyncio.TimeoutError:
                print("Warning: Browser close timed out.")
        if self._cm:
            print("Exiting playwright context manager...")
            await self._cm.__aexit__(None, None, None)
            print("Playwright context manager exited.")
        print("Scraper resources closed.")

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
                "user_agent": self.ua.random,
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
        
        all_deals_dict = self._filter_deals_by_points(all_deals_dict)
        all_deals_dict = self._apply_composite_score_filter(all_deals_dict)

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
                    option_data['booking_url'],
                    option_data['cabins']
                ] for option_data in program_options.values()
            ]
            final_deals.append([list(segments), options_list, duration])

        result = {"legend": self.LEGEND, "deals": final_deals}
        if "booking_urls" in result["legend"]:
            del result["legend"]["booking_urls"]
        return json.dumps(result, indent=2)

    async def _scrape_matrix_search(self, context: Any, job: Dict[str, Any]) -> Dict[Any, Any]:
        origins = job.get("origins", [])
        destinations = job.get("destinations", [])
        start_date = job.get("start_date")
        end_date = job.get("end_date")
        valid_routes_list = job.get("valid_routes")
        valid_routes = set(tuple(r) for r in valid_routes_list) if valid_routes_list is not None else None

        page = await context.new_page()
        
        print(f"Searching MATRIX from {','.join(origins)} to {','.join(destinations)} between {start_date} and {end_date}...")
        best_deals: Dict[Any, Any] = {}
        loop = asyncio.get_running_loop()
        search_done_future = loop.create_future()
        first_response_received = asyncio.Event()

        async def handle_response(response):
            if "flight/search/fetch_result" in response.url:
                first_response_received.set() 
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
            
            try:
                await asyncio.wait_for(first_response_received.wait(), timeout=25)
            except asyncio.TimeoutError:
                raise Exception("No flight data received within 25 seconds.")

            await asyncio.wait_for(search_done_future, timeout=70)
            print("MATRIX search complete, filtering results...")
            
            if valid_routes is None:
                return best_deals

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
        first_response_received = asyncio.Event()

        async def handle_response(response):
            if "flight/search/fetch_result" in response.url:
                first_response_received.set()
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

            try:
                await asyncio.wait_for(first_response_received.wait(), timeout=15)
            except asyncio.TimeoutError:
                raise Exception("No flight data received within 15 seconds.")

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
            flight_number = s.get('flight_number')
            da = s.get('da')
            aa = s.get('aa')
            dt = s.get('dt')
            at = s.get('at')

            segment_tuple = (
                flight_number, da, aa,
                dt, at
            )
            segments_data.append(segment_tuple)
        return tuple(segments_data)

    def _get_booking_option(self, route: Dict[str, Any], program_code: str) -> Dict[str, Any]:
        URL_PARAM_MAP = {
            'tripType': 't', 'departure': 'd', 'arrival': 'a', 'departDate': 'dd',
            'departDateSec': 'dds', 'multiday': 'md', 'departure2': 'd2', 'arrival2': 'a2',
            'departDate2': 'dd2', 'departDateSec2': 'dds2', 'cabins': 'cs', 'cabin': 'c',
            'banks': 'bs', 'airlineProgram': 'ap', 'adults': 'as', 'children': 'ch'
        }

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
        if '?' in booking_url:
            base_url, url_params_str = booking_url.split('?', 1)
            parsed_params = parse_qs(url_params_str)
            minified_params = {}
            for key, value in parsed_params.items():
                short_key = URL_PARAM_MAP.get(key, key)
                minified_params[short_key] = value
            
            minified_url_params_str = urlencode(minified_params, doseq=True)
            final_url = f"{base_url}?{minified_url_params_str}"
        else:
            final_url = booking_url

        return {
            "program": program_code,
            "transfer_partners": transfer_partners,
            "booking_url": final_url, # New key
            "cabins": {}
        }

    def _process_deals(self, deals_chunk: List[Dict[str, Any]], best_deals: Dict[Any, Any]):
        for deal in deals_chunk:
            if not deal.get("routes"): continue
            
            program_code = self._get_program_code(deal.get("code"), deal.get("program"))
            if not program_code or program_code == 'AA': continue

            for route in deal["routes"]:
                payment = route.get("payment", {})
                cabin, points = payment.get("cabin", "").lower(), payment.get("miles")
                if not cabin or points is None: continue

                if "business" in cabin or "first" in cabin:
                    premium_cabin_percentage = route.get("premium_cabin_percentage")
                    if premium_cabin_percentage is not None and premium_cabin_percentage <= 60 and premium_cabin_percentage > 0:
                        continue
                
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
                    
                    cabin_deal_data = [points, payment.get('tax')]

                    existing_cabin_deal = option_data["cabins"].get(cabin_code)
                    if not existing_cabin_deal or points < existing_cabin_deal[0]:
                        option_data["cabins"][cabin_code] = cabin_deal_data
                except TypeError as e:
                    print(f"Error processing deal: {e}")
                    print(f"Problematic segments: {valid_segments}")

    def _filter_deals_by_points(self, deals_dict: Dict[Any, Any]) -> Dict[Any, Any]:
        """Filters deals based on points thresholds."""
        
        # 1. Collect all economy prices, grouped by route
        economy_prices_by_route: Dict[Tuple[str, str], List[int]] = {}
        for segments_key, (_, program_options) in deals_dict.items():
            if not segments_key:
                continue
            origin = segments_key[0][1]
            destination = segments_key[-1][2]
            route_key = (origin, destination)

            for _, option_data in program_options.items():
                if 'Y' in option_data['cabins']:
                    points = option_data['cabins']['Y'][0]
                    if route_key not in economy_prices_by_route:
                        economy_prices_by_route[route_key] = []
                    economy_prices_by_route[route_key].append(points)

        # 2. Calculate the points threshold for economy on each route
        economy_thresholds: Dict[Tuple[str, str], float] = {}
        for route_key, prices in economy_prices_by_route.items():
            if len(prices) > 1:
                mean = statistics.mean(prices)
                stdev = statistics.stdev(prices)
                economy_thresholds[route_key] = mean + stdev
            else:
                # If only one data point, don't filter it
                economy_thresholds[route_key] = float('inf')

        # 3. Iterate through deals and apply all filters
        fixed_thresholds = {'F': 200000, 'J': 120000, 'W': 80000}
        filtered_deals_dict: Dict[Any, Any] = {}

        for segments_key, (duration, program_options) in deals_dict.items():
            if not segments_key:
                continue
            
            origin = segments_key[0][1]
            destination = segments_key[-1][2]
            route_key = (origin, destination)

            filtered_program_options = {}
            for program_code, option_data in program_options.items():
                filtered_cabins = {}
                for cabin_code, cabin_deal in option_data['cabins'].items():
                    points = cabin_deal[0]
                    
                    should_keep = True
                    if cabin_code in fixed_thresholds:
                        if points > fixed_thresholds[cabin_code]:
                            should_keep = False
                    elif cabin_code == 'Y':
                        # Only filter if a threshold was calculated for this route
                        if route_key in economy_thresholds and points > economy_thresholds[route_key]:
                            should_keep = False
                    
                    if should_keep:
                        filtered_cabins[cabin_code] = cabin_deal
                
                if filtered_cabins:
                    # Important: create a copy to avoid modifying the original dict while iterating
                    new_option_data = option_data.copy()
                    new_option_data['cabins'] = filtered_cabins
                    filtered_program_options[program_code] = new_option_data
            
            if filtered_program_options:
                filtered_deals_dict[segments_key] = (duration, filtered_program_options)

        return filtered_deals_dict

    def _apply_composite_score_filter(self, deals_dict: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Applies a composite score to filter for the top 50% of deals per route and cabin.
        """
        # 1. Create a flat list of deals
        all_individual_deals = []
        for segments_key, (duration, program_options) in deals_dict.items():
            if not segments_key: continue
            
            stops = len(segments_key) - 1
            origin = segments_key[0][1]
            destination = segments_key[-1][2]

            for program_code, option_data in program_options.items():
                for cabin_code, cabin_deal in option_data['cabins'].items():
                    points = cabin_deal[0]
                    fees = cabin_deal[1] or 0 # tax can be None

                    all_individual_deals.append({
                        "segments_key": segments_key,
                        "program_code": program_code,
                        "cabin_code": cabin_code,
                        "origin": origin,
                        "destination": destination,
                        "points": points,
                        "fees": fees,
                        "duration": duration,
                        "stops": stops,
                    })

        if not all_individual_deals:
            return {}

        # 2. Group deals by (origin, destination, cabin_code)
        grouped_deals = {}
        for deal in all_individual_deals:
            key = (deal['origin'], deal['destination'], deal['cabin_code'])
            if key not in grouped_deals:
                grouped_deals[key] = []
            grouped_deals[key].append(deal)

        # 3. Score, rank, and filter each group
        filtered_deals_to_keep = set() # Use a set of (segments_key, program_code, cabin_code)

        for group_key, deals_in_group in grouped_deals.items():
            if len(deals_in_group) <= 2: # Don't filter small groups
                for deal in deals_in_group:
                    filtered_deals_to_keep.add((deal['segments_key'], deal['program_code'], deal['cabin_code']))
                continue

            weights = {'points': 0.45, 'fees': 0.15, 'duration': 0.25, 'stops': 0.15}
            
            # Normalize continuous metrics
            continuous_metrics = ['points', 'fees', 'duration']
            min_max = {}
            for m in continuous_metrics:
                values = [d[m] for d in deals_in_group]
                min_max[m] = (min(values), max(values))

            for deal in deals_in_group:
                score = 0
                # Score continuous metrics
                for m in continuous_metrics:
                    min_val, max_val = min_max[m]
                    if max_val == min_val:
                        norm_score = 1.0
                    else:
                        norm_score = (max_val - deal[m]) / (max_val - min_val)
                    score += norm_score * weights[m]
                
                # Score stops
                stops = deal['stops']
                if stops == 0:
                    stops_score = 1.0
                elif stops == 1:
                    stops_score = 0.5
                else:
                    stops_score = 0.0
                score += stops_score * weights['stops']

                deal['score'] = score

            # Sort and filter
            deals_in_group.sort(key=lambda d: d['score'], reverse=True)
            num_to_keep = max(1, int(len(deals_in_group) * 0.5)) # Keep top 50%, at least 1
            
            for deal in deals_in_group[:num_to_keep]:
                filtered_deals_to_keep.add((deal['segments_key'], deal['program_code'], deal['cabin_code']))

        # 4. Reconstruct the deals_dict
        new_deals_dict = {}
        for segments_key, (duration, program_options) in deals_dict.items():
            new_program_options = {}
            for program_code, option_data in program_options.items():
                new_cabins = {}
                for cabin_code, cabin_deal in option_data['cabins'].items():
                    if (segments_key, program_code, cabin_code) in filtered_deals_to_keep:
                        new_cabins[cabin_code] = cabin_deal
                
                if new_cabins:
                    new_option_data = option_data.copy()
                    new_option_data['cabins'] = new_cabins
                    new_program_options[program_code] = new_option_data
            
            if new_program_options:
                new_deals_dict[segments_key] = (duration, new_program_options)
                
        return new_deals_dict

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
                                if len(cabin_deal) == 2: # Only add cash price once
                                    points = cabin_deal[0]
                                    cpp = round((price / points) * 100, 2) if points > 0 else 0
                                    cabin_deal.extend([price, cpp])
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
