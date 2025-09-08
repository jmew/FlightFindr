from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import json
from fast_flights import FlightData, Passengers, get_flights
import fast_flights.core
from . import custom_parser
from . import custom_schema
import fast_flights.schema
import itertools

# Load environment variables from .env file
load_dotenv()

PROGRAM_MAPPING = {
    "AR": "Aerolineas Argentinas", "AM": "Aeromexico", "AC": "Air Canada",
    "KL": "Air France/KLM", "AS": "Alaska Airlines", "AA": "American Airlines",
    "AV": "Avianca", "DL": "Delta", "EK": "Emirates", "EY": "Etihad",
    "AY": "Finnair", "IB": "Iberia", "B6": "JetBlue", "LH": "Lufthansa",
    "QF": "Qantas", "SK": "SAS", "SQ": "Singapore Airlines", "NK": "Spirit",
    "TP": "TAP Portugal", "TK": "Turkish Airlines", "UA": "United Airlines",
    "VS": "Virgin Atlantic", "VA": "Virgin Australia",
}

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
    semaphore = asyncio.Semaphore(10)

    async def search_single_flight(origin_airport, dest_airport, date):
        async with semaphore:
            try:
                # First attempt with fallback
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
                return flights_with_date
            except Exception as e:
                if "no token provided" in str(e):
                    print(f"Rate limit error for {origin_airport}->{dest_airport} on {date}. Retrying with local Playwright...")
                    try:
                        # Retry with local
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
                        return [flight.__dict__ for flight in result.flights]
                    except Exception as e2:
                        print(f"Error getting cash price with local Playwright for {origin_airport} -> {dest_airport} on {date} ({cabin}): {e2}")
                        return []
                else:
                    print(f"Error getting cash price for {origin_airport} -> {dest_airport} on {date} ({cabin}): {e}")
                    return []

    tasks = [search_single_flight(o, d, dt) for o, d, dt in search_combinations]
    all_flights_lists = await asyncio.gather(*tasks)

    # Flatten the list of lists
    flat_list = [item for sublist in all_flights_lists for item in sublist]

    print(f"Successfully fetched {len(flat_list)} cash flights for {origin} -> {destination} ({cabin})")
    return {"cabin": cabin, "flights": flat_list}