from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Result:
    current_price: str
    flights: List[Flight]


@dataclass
class Flight:
    name: str
    price: str
    departure: str
    stops: int
    arrival_time_ahead: str
    flight_number: Optional[str]
    layover_details: Optional[str]