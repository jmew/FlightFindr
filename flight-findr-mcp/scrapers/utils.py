from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
from dotenv import load_dotenv
from fast_flights import FlightData, Passengers, get_flights
import fast_flights.core
from . import custom_parser
from . import custom_schema
import fast_flights.schema
import itertools
import random

# Load environment variables from .env file
load_dotenv()

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

def normalize_program_name(program_name: Optional[str]) -> Optional[str]:
    if not program_name:
        return None
    return program_name.strip()

def parse_time(time_str: str) -> Optional[datetime.time]:
    """Parses time from various formats into a time object."""
    if not time_str:
        return None

    # Replace non-standard space characters
    time_str = time_str.replace('\u202f', ' ')

    formats_to_try = [
        '%Y-%m-%dT%H:%M:%S',  # For ISO-like formats without Z
        '%Y-%m-%dT%H:%M:%S%z', # For ISO-like formats with Z
        '%I:%M %p',          # For AM/PM formats
        '%H:%M',              # For 24-hour formats
    ]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    
    # If all formats fail, try fromisoformat as a last resort
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00')).time()
    except ValueError:
        return None

# Set the custom parser
fast_flights.core.parse_response = custom_parser.parse_response
fast_flights.schema.Flight = custom_schema.Flight

async def fetch_cash_prices(origin: str, destination: str, dates: List[str], cabin: str) -> Dict[str, Any]:
    """Fetches cash prices for given routes and cabin across multiple dates in parallel using fast_flights."""
    print(f"Fetching cash prices for {origin} -> {destination} (Cabin: {cabin}) on dates: {', '.join(dates)}")

    origins = origin.split(',')
    destinations = destination.split(',')
    
    # Generate all combinations of origins, destinations, and dates
    search_combinations = list(itertools.product(origins, destinations, dates))
    
    # Limit concurrency to 5 to avoid overwhelming the local Playwright
    semaphore = asyncio.Semaphore(5)

    async def search_single_flight(origin_airport, dest_airport, date):
        async with semaphore:
            max_fallback_retries = 3
            
            # Retry loop for 'fallback'
            for attempt in range(max_fallback_retries):
                try:
                    result = await asyncio.to_thread(
                        get_flights,
                        flight_data=[
                            FlightData(date=date, from_airport=origin_airport, to_airport=dest_airport)
                        ],
                        trip="one-way",
                        seat=cabin,
                        passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
                        fetch_mode="fallback",
                    )
                    flights_with_date = []
                    for flight in result.flights:
                        flight_dict = flight.__dict__
                        flight_dict['date'] = date
                        flights_with_date.append(flight_dict)
                    return flights_with_date # Success
                except Exception:
                    if attempt < max_fallback_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(wait_time) # wait before next retry
            
            # If all fallback attempts failed, try with 'local'
            print(f"All fallback attempts failed. Trying with local for {origin_airport}->{dest_airport} on {date}")
            try:
                result = await asyncio.to_thread(
                    get_flights,
                    flight_data=[
                        FlightData(date=date, from_airport=origin_airport, to_airport=dest_airport)
                    ],
                    trip="one-way",
                    seat=cabin,
                    passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
                    fetch_mode="local",
                )
                flights_with_date = []
                for flight in result.flights:
                    flight_dict = flight.__dict__
                    flight_dict['date'] = date
                    flights_with_date.append(flight_dict)
                return flights_with_date
            except Exception as e:
                print(f"Final attempt (local) failed for {origin_airport} -> {dest_airport} on {date} ({cabin}): {e}")
                return []

    tasks = [search_single_flight(o, d, dt) for o, d, dt in search_combinations]
    all_flights_lists = await asyncio.gather(*tasks)

    # Flatten the list of lists
    flat_list = [item for sublist in all_flights_lists for item in sublist]

    print(f"Successfully fetched {len(flat_list)} cash flights for {origin} -> {destination} ({cabin})")
    return {"cabin": cabin, "flights": flat_list}
