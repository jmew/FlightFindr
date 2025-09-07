from typing import Optional

from fast_flights.primp import Response
from fast_flights.schema import Result
import fast_flights.schema
from selectolax.lexbor import LexborHTMLParser, LexborNode


def parse_response(
    r: Response, *, dangerously_allow_looping_last_item: bool = False
) -> Result:
    class _blank:
        def text(self, *_, **__):
            return ""
        
        def attr(self, *_, **__):
            return ""

        def iter(self):
            return []

    blank = _blank()

    def safe(n: Optional[LexborNode]):
        return n or blank

    parser = LexborHTMLParser(r.text)
    
    flights = []

    for i, fl in enumerate(parser.css('div[jsname="IWWDBc"], div[jsname="YdtKid"]')):
        is_best_flight = i == 0

        for item in fl.css("ul.Rk10dc li"):
            # --- Basic Flight Info ---
            name = safe(item.css_first("div.sSHqwe.tPgKwe.ogfYpf span")).text(strip=True)
            price = safe(item.css_first(".YMlIz.FpEdX")).text(strip=True) or "0"
            
            # --- CORRECTED: More robust selectors for core flight details ---
            duration = safe(item.css_first(".gvkrdb")).text(strip=True)
            departure_time = safe(item.css_first(".wtdjmc.YMlIz.ogfYpf.tPgKwe")).text(strip=True)
            arrival_time = safe(item.css_first(".XWcVob.YMlIz.ogfYpf.tPgKwe")).text(strip=True)
            departure_airport_code = safe(item.css_first(".G2WY5c.sSHqwe.ogfYpf.tPgKwe > div")).text(strip=True)
            arrival_airport_code = safe(item.css_first(".c8rWCd.sSHqwe.ogfYpf.tPgKwe > div")).text(strip=True)
            
            arrival_time_ahead = safe(item.css_first("span.bOzv6")).text(strip=True)
            
            # --- Stops and Layover Details ---
            stops_node = item.css_first(".BbR8Ec .ogfYpf")
            stops_text = stops_node.text(strip=True) if stops_node else "Nonstop"
            
            layover_info = None
            if "stop" in stops_text:
                layover_node = item.css_first(".sSHqwe.tPgKwe.ogfYpf[aria-label]")
                if layover_node:
                    layover_info = layover_node.text(strip=True)

            # --- Emissions and Delays ---
            delay = safe(item.css_first(".GsCCve")).text(strip=True) or None
            
            # --- Amenities and Baggage ---
            amenities_nodes = item.css("div.b8_33-N6PNV .b8_33-bN97Pc")
            amenities = [node.attr('aria-label') for node in amenities_nodes if node.attr('aria-label')] or None
            baggage_node = item.css_first(".b8_33-bN97Pc.b8_33-L6cTce")
            baggage = baggage_node.text(strip=True) if baggage_node else "Info not specified"

            # --- Flight Number from Emissions div ---
            flight_number = None
            try:
                emissions_div = item.css_first("div.NZRfve.E8UxCd")
                if emissions_div:
                    url = emissions_div.attrs.get('data-travelimpactmodelwebsiteurl', '')
                    if url:
                        parts = url.split('-')
                        if len(parts) >= 4:
                            flight_number = f"{parts[-3]} {parts[-2]}"
            except Exception:
                flight_number = None

            # --- Formatting ---
            try:
                stops_fmt = 0 if "Nonstop" in stops_text else int(stops_text.split(" ", 1)[0])
            except (ValueError, AttributeError):
                stops_fmt = "Unknown"

            flights.append(
                fast_flights.schema.Flight(
                    is_best=is_best_flight,
                    name=name,
                    price=price.replace(",", ""),
                    departure=departure_time,
                    arrival=arrival_time,
                    arrival_time_ahead=arrival_time_ahead,
                    duration=duration,
                    stops=stops_fmt,
                    delay=delay,
                    departure_airport_code=departure_airport_code,
                    arrival_airport_code=arrival_airport_code,
                    amenities=amenities,
                    baggage=baggage,
                    flight_number=flight_number,
                    layover_details=layover_info,
                )
            )

    current_price = safe(parser.css_first("span.gOatQ")).text()
    if not flights:
        raise RuntimeError("No flights found in HTML content")

    return Result(current_price=current_price, flights=flights)
