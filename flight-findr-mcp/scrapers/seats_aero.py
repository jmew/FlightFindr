from playwright.async_api import async_playwright, Page, Browser, Playwright, TimeoutError
import json
import asyncio
import os
from typing import List, Dict, Any, Optional

class SeatsAeroScraper:
    """
    A class to manage a persistent browser session for scraping Seats.aero.
    """
    def __init__(self, playwright: Playwright, headless: bool = True):
        self.playwright: Playwright = playwright
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start(self):
        """Initializes the browser."""
        proxy_url = os.environ.get("HTTP_PROXY")
        proxy_settings = {"server": proxy_url} if proxy_url else None
        if proxy_settings:
            print("Using proxy for Seats.aero scraper.")

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            proxy=proxy_settings,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote",
                "--single-process",
            ]
        )
        self.page = await self.browser.new_page()

    async def scrape(self, origin: str, destination: str, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrapes seats.aero for flight deals."""
        if not self.page:
            raise Exception("Scraper not initialized properly.")

        search_url = f"https://seats.aero/search?origin_airport={origin}&destination_airport={destination}&start_date={start_date}&end_date={end_date}"
        print(f"Navigating to Seats.aero search URL: {search_url}")
        
        all_deals = []
        async def handle_response(response):
            if "_api/search_partial" in response.url or "_api/enrichment_modern" in response.url:
                try:
                    data = await response.json()
                    if "trips" in data: # Enrichment data
                        processed = self._process_enrichment_data(data)
                        all_deals.extend(processed)
                except Exception as e:
                    print(f"Could not parse JSON from {response.url}: {e}")

        self.page.on("response", handle_response)

        await self.page.goto(search_url, timeout=60000, wait_until="networkidle")
        
        print("Seats.aero search complete.")
        self.page.remove_listener("response", handle_response)
        return all_deals

    def _process_enrichment_data(self, enrichment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        processed_deals = []
        if not enrichment_data.get('trips'):
            return []

        for trip in enrichment_data['trips']:
            deal = {
                "date": trip['Date'],
                "program": enrichment_data['source'],
                "route": f"{trip['OriginAirport']} -> {trip['DestinationAirport']}",
                "flight_numbers": [trip['FlightNumbers']],
                "departure_time": trip['DepartsAt'],
                "arrival_time": trip['ArrivesAt'],
                "economy": None, "premium": None, "business": None, "first": None,
            }
            cabin = trip['Cabin'].lower()
            cabin_key = "premium" if "premium" in cabin else "business" if "business" in cabin else "first" if "first" in cabin else "economy"
            deal[cabin_key] = {
                "points": trip['MileageCost'],
                "fees": f"{trip['TaxesCurrencySymbol']}{trip['TotalTaxes']/100} {trip['TaxesCurrency']}",
                "seats": trip['RemainingSeats'],
            }
            processed_deals.append(deal)
        return processed_deals

    async def close(self):
        """Closes the browser."""
        if self.browser:
            await self.browser.close()

# --- Global scraper instance management ---
scraper_instance: Optional[SeatsAeroScraper] = None

async def initialize_scraper(playwright: Playwright):
    """Initializes the global scraper instance."""
    global scraper_instance
    if scraper_instance is None:
        print("Initializing Seats.aero scraper...")
        scraper_instance = SeatsAeroScraper(playwright)
        await scraper_instance.start()
        print("Seats.aero scraper initialized successfully.")

async def close_scraper():
    """Closes the global scraper instance."""
    global scraper_instance
    if scraper_instance:
        await scraper_instance.close()
        scraper_instance = None

async def scrape_seats_aero(origin: str, destination: str, start_date: str, end_date: str, **kwargs) -> List[Dict[str, Any]]:
    """Main function to scrape Seats.aero."""
    if scraper_instance is None:
        raise Exception("Seats.aero scraper has not been initialized.")
    return await scraper_instance.scrape(origin, destination, start_date, end_date, **kwargs)

async def main_test():
    playwright = await async_playwright().start()
    try:
        await initialize_scraper(playwright)
        deals = await scrape_seats_aero("JFK", "SFO", "2025-10-10", "2025-10-10")
        if deals:
            print(f"Found {len(deals)} deals.")
            print(json.dumps(deals[0], indent=2))
    finally:
        await close_scraper()
        await playwright.stop()

if __name__ == '__main__':
    asyncio.run(main_test())
