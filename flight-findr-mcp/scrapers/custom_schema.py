from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Flight:
    name: str
    price: str
    departure: str
    stops: int
    arrival_time_ahead: str
    flight_number: Optional[str]
    layover_details: Optional[str]