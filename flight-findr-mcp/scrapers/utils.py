from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import os
from dotenv import load_dotenv
from serpapi import GoogleSearch

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

async def fetch_cash_prices(origin: str, destination: str, date: str, cabin: str) -> Dict[str, Any]:
    """Fetches cash prices for a given route and cabin."""
    print(f"Fetching cash prices for {origin} -> {destination} on {date} (Cabin: {cabin})")
    try:
        travel_class_map = {
            'economy': 1,
            'premium': 2,
            'business': 3,
            'first': 4
        }
        travel_class = travel_class_map.get(cabin)
        if not travel_class:
            return {}

        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": date,
            "adults": 1,
            "travel_class": travel_class,
            "type": 2, # one way
            "api_key": os.getenv("SERPAPI_KEY"),
        }

        search = GoogleSearch(params)
        results = await asyncio.to_thread(search.get_dict)

        print(f"Successfully fetched {len(results.get('best_flights', [])) + len(results.get('other_flights', []))} cash flights for {origin} -> {destination}")
        return {"cabin": cabin, "flights": results.get('best_flights', []) + results.get('other_flights', [])}

    except Exception as e:
        print(f"Error getting cash price for {origin} -> {destination} ({cabin}): {e}")
        return {"cabin": cabin, "flights": []}
