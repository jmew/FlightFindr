import os
import sys
from playwright.async_api import async_playwright, Page, Browser, Playwright
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from scrapers.utils import parse_time, fetch_cash_prices, PROGRAM_MAPPING
from datetime import datetime, timedelta
import pytz
import airportsdata

LEGEND = {
    "field_order": {
        "deal": ["segments", "options", "duration_minutes"],
        "segment": ["flight_number", "dep_airport", "arr_airport", "dep_time", "arr_time", "layover_mins"],
        "option": ["program", "transfer_partners", "url_params", "cabins"],
        "cabin_deal": ["points", "tax", "cash_price", "cpp"]
    },
    "programs": {
        "EY": "Etihad Guest", "VA": "Virgin Australia Velocity", "AS": "Alaska Atmos Rewards", 
        "UA": "United MileagePlus", "BA": "British Airways Executive Club", "AR": "Aerolineas Argentinas",
        "AM": "Aeromexico Club Premier", "AC": "Air Canada Aeroplan", "KL": "KLM Flying Blue",
        "AV": "Avianca LifeMiles", "DL": "Delta SkyMiles", "EK": "Emirates Skywards",
        "AY": "Finnair Plus", "IB": "Iberia Plus", "B6": "JetBlue TrueBlue",
        "LH": "Lufthansa Miles & More", "QF": "Qantas Frequent Flyer", "SK": "SAS EuroBonus",
        "SQ": "Singapore Airlines KrisFlyer", "NK": "Spirit Airlines", "TP": "TAP Air Portugal",
        "TK": "Turkish Airlines Miles&Smiles", "VS": "Virgin Atlantic Flying Club",
        "AA": "American Airlines Aadvantage"
    },
    "banks": {
        "amex": "Amex Rewards", "c1": "Capital One", "citi": "Citi Points", 
        "bilt": "Bilt", "chase": "Chase UR"
    },
    "cabin_codes": {
        "Y": "Economy", "W": "Premium Economy", "J": "Business", "F": "First"
    },
    "booking_urls": {
        "EY": "https://digital.etihad.com/book/search?{params}",
        "AS": "https://www.alaskaair.com/search/results?{params}",
        "VA": "https://book.virginaustralia.com/dx/VADX/#/flight-selection?{params}",
        "UA": "https://www.united.com/en/us/fsr/choose-flights?{params}",
        "BA": "https://www.britishairways.com/travel/redeem/execclub/_gf/en_us?{params}",
        "AC": "https://www.aircanada.com/aeroplan/redeem/availability/outbound?{params}",
        "KL": "https://www.klm.com/flight-search/search-results?{params}",
        "VS": "https://flywith.virginatlantic.com/gb/en/reward-flights-search/results/outbound?{params}",
        "AA": "https://www.aa.com/booking/search?{params}",
        "QF": "https://www.qantas.com/au/en/book-a-trip/flights.html?{params}"
    }
}

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

    async def _scrape_one_search(self, origin: str, destination: str, start_date: str, end_date: str) -> Dict[Any, Any]:
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

            cash_prices_list = await cash_task
            self._match_cash_prices(best_deals, cash_prices_list)
            
            filtered_deals = {}
            for segments, (duration, program_options) in best_deals.items():
                origin_code = segments[0][1]
                dest_code = segments[-1][2]
                if origin_code in origin and dest_code in destination:
                    filtered_deals[segments] = (duration, program_options)

            return filtered_deals

        except asyncio.TimeoutError:
            print("Timed out waiting for the 'done' signal from the server.")
            return {}
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            return {}
        finally:
            page.remove_listener("response", handle_response)
            await page.context.close()

    def _get_program_code(self, deal: Dict[str, Any]) -> Optional[str]:
        program_code = deal.get("code")
        if not program_code:
            program_name = deal.get("program")
            normalized_program = self._normalize_program_name(program_name)
            if not normalized_program:
                return None
            program_code = self.PROGRAM_CODES.get(normalized_program)
        return program_code

    def _calculate_duration(self, valid_segments: List[Dict[str, Any]], route: Dict[str, Any]) -> int:
        try:
            dep_airport_code = valid_segments[0]['da']
            arr_airport_code = valid_segments[-1]['aa']
            dep_tz_str = self.airports[dep_airport_code]['tz']
            arr_tz_str = self.airports[arr_airport_code]['tz']
            dep_tz = pytz.timezone(dep_tz_str)
            arr_tz = pytz.timezone(arr_tz_str)

            dep_time_naive = datetime.fromisoformat(valid_segments[0]['dt'])
            arr_time_naive = datetime.fromisoformat(valid_segments[-1]['at'])

            dep_time_aware = dep_tz.localize(dep_time_naive)
            arr_time_aware = arr_tz.localize(arr_time_naive)

            return round((arr_time_aware - dep_time_aware).total_seconds() / 60)
        except (KeyError, pytz.UnknownTimeZoneError):
            return route.get("duration", 0)

    def _extract_segments_data(self, valid_segments: List[Dict[str, Any]]) -> Tuple[Tuple[Any, ...], ...]:
        segments_data = []
        for i, s in enumerate(valid_segments):
            layover_mins = 0
            if i < len(valid_segments) - 1:
                arr_time = datetime.fromisoformat(s.get('at'))
                dep_time = datetime.fromisoformat(valid_segments[i+1].get('dt'))
                layover_mins = round((dep_time - arr_time).total_seconds() / 60)
            
            segment_tuple = (
                s.get('flight_number'), s.get('da'), s.get('aa'),
                s.get('dt'), s.get('at'), layover_mins
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
            
            program_code = self._get_program_code(deal)
            if not program_code: continue

            for route in deal["routes"]:
                payment = route.get("payment", {})
                cabin, points = payment.get("cabin", "").lower(), payment.get("miles")
                if not cabin or points is None: continue
                
                valid_segments = [s for s in route.get("segments", []) if s.get("flight_number")]
                if not valid_segments: continue

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

    def _match_cash_prices(self, deals_dict: Dict[Any, Any], cash_prices_data: List[Dict[str, Any]]):
        if not deals_dict or not any(c.get('flights') for c in cash_prices_data):
            return

        for segments, (duration, program_options) in deals_dict.items():
            if not segments: continue
            
            first_segment = segments[0]
            award_departure_time_str = first_segment[3]
            if not award_departure_time_str: continue
            
            award_departure_datetime = datetime.fromisoformat(award_departure_time_str)
            award_departure_time = award_departure_datetime.time()
            award_departure_date = award_departure_datetime.date()
            
            award_stops = [s[2] for s in segments[:-1]]
            award_num_stops = len(award_stops)

            for cabin_prices in cash_prices_data:
                cabin = cabin_prices['cabin']
                
                cash_cabin_code = "Y"
                if "premium" in cabin: cash_cabin_code = "W"
                elif "business" in cabin: cash_cabin_code = "J"
                elif "first" in cabin: cash_cabin_code = "F"

                exact_match_flight = None
                for flight in cabin_prices.get('flights', []):
                    cash_departure_time = parse_time(flight.get('departure'))
                    if not cash_departure_time: continue
                    
                    cash_departure_date_str = flight.get('date')
                    if not cash_departure_date_str: continue
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
                    try:
                        exact_price_str = exact_match_flight['price'].replace('$', '').replace(',', '')
                        exact_price = float(exact_price_str)
                        
                        for program_code, option_data in program_options.items():
                            if cash_cabin_code in option_data['cabins']:
                                cabin_deal = option_data['cabins'][cash_cabin_code]
                                points = cabin_deal[0]
                                cabin_deal[2] = exact_price
                                cabin_deal[3] = round((exact_price / points) * 100, 2) if points > 0 else 0
                    except (ValueError, TypeError, KeyError):
                        pass

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
            f"&airlineProgram=AR%2CAM%2CAC%2CKL%2CAS%2CAV%2CDL%2CEK%2CEY%2CAY%2CIB%2CB6%2CLH%2CQF%2CSK%2CSQ%2CNK%2CTP%2CTK%2CUA%2CVS%2CAA"
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
        return PROGRAM_MAPPING.get(lower_program_name, program_name.strip())

async def main_test():
    """Test function to run the scraper for a sample search."""
    scraper = None
    try:
        scraper = await PointsYeahScraper.create()
        searches = [
            {"origin_airports": ["SEA"], "destination_airports": ["JFK"], "start_date": "2025-10-04", "end_date": "2025-10-04"},
        ]
        deals_json = await scraper.search_flights(searches)
        
        deals_data = json.loads(deals_json)
        print(f"Found {len(deals_data.get('deals', []))} deals.")
        
        flight_count = 0
        for deal in deals_data.get('deals', []):
            options = deal[1]
            for option in options:
                cabins = option[3]
                flight_count += len(cabins)
        print(f"Found {flight_count} individual flight options.")

        with open("deals.json", 'w') as f:
            json.dump(deals_data, f, indent=2)

    finally:
        if scraper:
            await scraper.close()

if __name__ == '__main__':
    asyncio.run(main_test())