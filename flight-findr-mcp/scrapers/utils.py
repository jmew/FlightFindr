from datetime import datetime
from typing import Optional
import asyncio
from fast_flights import get_flights, FlightData, Passengers

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
    try:
        # Handles formats like '2025-10-10T16:52:00' or '2025-10-10T16:53:00Z'
        return datetime.fromisoformat(time_str.replace('Z', '+00:00')).time()
    except ValueError:
        try:
            # Handles formats like '4:52 PM'
            return datetime.strptime(time_str, '%I:%M %p').time()
        except ValueError:
            return None

async def get_flight_cash_prices(deal: dict, cabin: str) -> None:
    """Gets cash prices for a given deal and cabin, and calculates CPP."""
    if not deal.get(cabin) or not deal[cabin].get('points'):
        return

    try:
        origin, destination = deal['route'].split(' -> ')
        flight_data = [
            FlightData(date=deal['date'], from_airport=origin, to_airport=destination)
        ]
        passengers = Passengers(adults=1)

        seat_map = {
            'economy': 'economy',
            'premium': 'premium-economy',
            'business': 'business',
            'first': 'first'
        }
        seat_type = seat_map.get(cabin)
        if not seat_type:
            return

        loop = asyncio.get_running_loop()
        cash_result = await loop.run_in_executor(
            None,
            lambda: get_flights(
                flight_data=flight_data,
                trip="one-way",
                passengers=passengers,
                seat=seat_type,
                fetch_mode="fallback",
            ),
        )

        if cash_result:
            flights = cash_result.flights
            if flights:
                # Cheapest cash price is the first result
                cheapest_flight = flights[0]
                cheapest_price_str = cheapest_flight.price.replace('$', '').replace(',', '')
                cheapest_price = float(cheapest_price_str)
                points = deal[cabin]['points']
                cheapest_cpp = (cheapest_price / points) * 100 if points > 0 else 0
                deal[cabin]['cheapest_cash_price'] = cheapest_price
                deal[cabin]['cheapest_cpp'] = round(cheapest_cpp, 2)

                # Find exact match
                exact_match_flight = None
                award_departure_time = parse_time(deal[cabin].get('departure_time'))

                for flight in flights:
                    cash_departure_time = parse_time(flight.departure)
                    # Fallback to matching by departure time
                    if award_departure_time and cash_departure_time and award_departure_time == cash_departure_time:
                        exact_match_flight = flight
                        break
            
                if exact_match_flight:
                    exact_price_str = exact_match_flight.price.replace('$', '').replace(',', '')
                    exact_price = float(exact_price_str)
                    exact_cpp = (exact_price / points) * 100 if points > 0 else 0
                    deal[cabin]['exact_cash_price'] = exact_price
                    deal[cabin]['exact_cpp'] = round(exact_cpp, 2)
                else:
                    deal[cabin]['exact_cash_price'] = 'N/A'
                    deal[cabin]['exact_cpp'] = 'N/A'

    except Exception as e:
        print(f"Error getting cash price for {deal['route']} ({cabin}): {e}")
