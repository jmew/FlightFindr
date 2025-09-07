from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Flight:
    is_best: bool
    name: str
    price: str
    departure: str
    arrival: str
    duration: str
    stops: int
    delay: Optional[str]
    arrival_time_ahead: str
    departure_airport_code: str
    arrival_airport_code: str
    amenities: Optional[List[str]]
    baggage: str
    flight_number: Optional[str]
    layover_details: Optional[str]