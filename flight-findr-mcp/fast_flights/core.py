from typing import List, Literal, Optional

from selectolax.lexbor import LexborHTMLParser, LexborNode

from .schema import Flight, Result
from .flights_impl import FlightData, Passengers
from .filter import TFSData
from .local_playwright import local_playwright_fetch
from .primp import Client, Response

def fetch(params: dict) -> Response:
    client = Client(impersonate="chrome_126", verify=False)
    res = client.get("https://www.google.com/travel/flights", params=params)
    assert res.status_code == 200, f"{res.status_code} Result: {res.text_markdown}"
    return res

def parse_response(
    r: Response
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
        for item in fl.css("ul.Rk10dc li"):
            # --- Basic Flight Info ---
            name = safe(item.css_first("div.sSHqwe.tPgKwe.ogfYpf span")).text(strip=True)
            price = safe(item.css_first(".YMlIz.FpEdX")).text(strip=True) or "0"

            if not name or price == "0":
                continue
            
            # --- CORRECTED: More robust selectors for core flight details ---
            departure_time = safe(item.css_first(".wtdjmc.YMlIz.ogfYpf.tPgKwe")).text(strip=True)
            
            arrival_time_ahead = safe(item.css_first("span.bOzv6")).text(strip=True)
            
            # --- Stops and Layover Details ---
            stops_node = item.css_first(".BbR8Ec .ogfYpf")
            stops_text = stops_node.text(strip=True) if stops_node else "Nonstop"
            
            layover_info = None
            if "stop" in stops_text:
                layover_node = item.css_first(".sSHqwe.tPgKwe.ogfYpf[aria-label]")
                if layover_node:
                    layover_info = layover_node.text(strip=True)


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
                stops_fmt = -1

            flights.append(
                Flight(
                    name=name,
                    price=price.replace(",", ""),
                    departure=departure_time,
                    stops=stops_fmt,
                    arrival_time_ahead=arrival_time_ahead,
                    flight_number=flight_number,
                    layover_details=layover_info,
                )
            )

    current_price = safe(parser.css_first("span.gOatQ")).text()
    if not flights:
        raise RuntimeError("No flights found in HTML content")

    return Result(current_price=current_price, flights=flights)


def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *, 
    mode: Literal["primp", "playwright"] = "primp",
) -> Result:
    data = filter.as_b64()

    params = {
        "tfs": data.decode("utf-8"),
        "hl": "en",
        "tfu": "EgQIABABIgA",
        "curr": currency,
    }

    if mode == "primp":
        try:
            res = fetch(params)
        except Exception:
            res = local_playwright_fetch(params)
    else: # mode == "playwright"
        res = local_playwright_fetch(params)

    if res == None:
        print("Result was none")
        return Result("", [])
    
    return parse_response(res)


def get_flights(
    *,
    flight_data: List[FlightData],
    trip: Literal["round-trip", "one-way", "multi-city"],
    passengers: Passengers,
    seat: Literal["economy", "premium-economy", "business", "first"],
    fetch_mode: Literal["primp", "playwright"] = "primp",
    max_stops: Optional[int] = None,
) -> Result:
    return get_flights_from_filter(
        TFSData.from_interface(
            flight_data=flight_data,
            trip=trip,
            passengers=passengers,
            seat=seat,
            max_stops=max_stops,
        ),
        mode=fetch_mode,
    )
