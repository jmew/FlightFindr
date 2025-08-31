import json
import os
from primp import Client

def scrape_seats_aero(origin, destination, start_date, end_date, programs=None, alliances=None, transfer_partners=None, points_min=None, points_max=None, days=None):
    """
    Scrapes seats.aero for flight deals using their internal API.

    Args:
        origin (str): The origin airport IATA code.
        destination (str): The destination airport IATA code.
        start_date (str): The start date of the travel date range in YYYY-MM-DD format.
        end_date (str): The end date for the travel date range in YYYY-MM-DD format.
        programs (list, optional): List of frequent flyer programs to filter by. Defaults to None.
        alliances (list, optional): List of airline alliances to filter by. Defaults to None.
        transfer_partners (list, optional): List of transfer partners to filter by. Defaults to None.
        points_min (int, optional): Minimum points required for a deal. Defaults to None.
        points_max (int, optional): Maximum points required for a deal. Defaults to None.
        days (int, optional): Number of days to search around the specified date. Defaults to None.

    Returns:
        list: A list of flight options, where each option is a dictionary.
    """
    search_url = f"https://seats.aero/_api/search_partial?min_seats=1&applicable_cabin=any&max_fees=40000&disable_live_filtering=false&date={start_date}&origins={origin}&destinations={destination}"
    if days and days > 0:
        search_url += f"&additional_days_num={days}"

    print(f"Scraping {search_url}")

    proxies = None
    if os.environ.get("NODE_ENV") == "production":
        proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        if proxy_url:
            print("Using proxy for seats.aero in production mode.")
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
        else:
            print("Production mode detected, but no proxy URL is set.")

    client = Client(impersonate="safari_17.2.1", proxies=proxies)
    try:
        search_response = client.get(search_url)
        print(f"seats.aero search response status: {search_response.status_code}")
        if search_response.status_code != 200:
            print(f"seats.aero search response text: {search_response.text}")
            raise Exception(f"Failed to fetch search results: {search_response.status_code}")
        search_data = json.loads(search_response.text)
    except Exception as e:
        print(f"Error fetching search results from seats.aero: {e}")
        return []

    all_deals = []
    if not search_data.get('metadata'):
        print("No metadata found in seats.aero search response.")
        return []

    print(f"Found {len(search_data['metadata'])} potential items in seats.aero metadata.")

    for item in search_data['metadata']:
        enrichment_url = f"https://seats.aero/_api/enrichment_modern/{item['id']}?m=1&min_seats=1&applicable_cabin=any&additional_days_num=1&max_fees=40000&disable_live_filtering=false&date={start_date}&origins={origin}&destinations={destination}"
        try:
            enrichment_response = client.get(enrichment_url)
            if enrichment_response.status_code != 200:
                print(f"seats.aero enrichment response status for id {item['id']}: {enrichment_response.status_code}")
                print(f"seats.aero enrichment response text for id {item['id']}: {enrichment_response.text}")
                raise Exception(f"Failed to fetch enrichment data: {enrichment_response.status_code}")
            enrichment_data = json.loads(enrichment_response.text)
        except Exception as e:
            print(f"Error fetching enrichment data from seats.aero for id {item['id']}: {e}")
            continue

        if not enrichment_data.get('trips'):
            print(f"No trips found in enrichment data for id {item['id']}.")
            continue
        
        print(f"Found {len(enrichment_data['trips'])} trips in enrichment data for id {item['id']}.")

        for trip in enrichment_data['trips']:
            deal = {
                "date": item['date'],
                "program": enrichment_data['source'],
                "route": f"{trip['OriginAirport']} -> {trip['DestinationAirport']}",
                "flight_numbers": [trip['FlightNumbers']],
                "departure_time": trip['DepartsAt'],
                "arrival_time": trip['ArrivesAt'],
                "economy": None,
                "premium": None,
                "business": None,
                "first": None,
            }

            cabin = trip['Cabin'].lower()
            if "premium" in cabin:
                cabin_key = "premium"
            elif "business" in cabin:
                cabin_key = "business"
            elif "first" in cabin:
                cabin_key = "first"
            else:
                cabin_key = "economy"

            deal[cabin_key] = {
                "points": trip['MileageCost'],
                "fees": f"{trip['TaxesCurrencySymbol']}{trip['TotalTaxes']/100} {trip['TaxesCurrency']}",
                "seats": trip['RemainingSeats'],
                "direct": trip['Stops'] == 0,
            }
            all_deals.append(deal)

    return all_deals

if __name__ == '__main__':
    # Example usage for testing
    origin = "SEA"
    destination = "SJC"
    start_date = "2025-10-10"
    end_date = "2025-10-10"
    
    deals = scrape_seats_aero(origin, destination, start_date, end_date)
    
    if deals:
        for deal in deals:
            print(json.dumps(deal, indent=2))
    else:
        print("No deals found.")