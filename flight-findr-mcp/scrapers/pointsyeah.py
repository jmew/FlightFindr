from playwright.sync_api import sync_playwright, Page, Browser, Playwright, TimeoutError
import json
import time
import os
from typing import List, Dict, Any, Optional

class PointsYeahScraper:
    """
    A class to manage a persistent browser session for scraping PointsYeah.com,
    optimizing performance by logging in only once.
    """
    def __init__(self, headless: bool = True):
        self.playwright: Playwright = sync_playwright().start()

        # Use the same proxy logic as the seats.aero scraper for production
        proxy_url = os.environ.get("HTTP_PROXY")
        proxy_settings = {"server": proxy_url} if proxy_url else None
        if proxy_settings:
            print("Using proxy for PointsYeah scraper.")

        self.browser: Browser = self.playwright.chromium.launch(
            headless=headless,
            proxy=proxy_settings,
            args=[
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ]
        )
        self.page: Page = self._create_new_page()
        self._login()

    def _create_new_page(self) -> Page:
        """Creates a new page with anti-bot detection scripts."""
        context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light'
        )
        page = context.new_page()
        
        # Anti-bot detection script
        stealth_script = """
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.navigator.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """
        page.add_init_script(stealth_script)
        return page

    def _login(self):
        """
        Performs a one-time login to PointsYeah, retrying the click on failure.
        """
        try:
            print("Navigating to login page...")
            self.page.goto("https://www.pointsyeah.com/login", timeout=60000)
            self.page.wait_for_selector('input[name="username"]', state="visible", timeout=15000)
            
            print("Entering credentials...")
            self.page.fill('input[name="username"]', "jepara2048@mogash.com")
            self.page.fill('input[name="password"]', "Password1!")
        
        except Exception as e:
            print(f"An error occurred during initial page load and form fill: {e}")
            self.page.screenshot(path="error_login_setup.png")
            self.close()
            raise

        max_retries = 3
        for attempt in range(max_retries):
            print(f"Clicking 'Sign In' (Attempt {attempt + 1}/{max_retries})...")
            self.page.locator('button[type="submit"].amplify-button--primary').click()

            # Wait for 1 second as requested, to see if an error message appears
            time.sleep(1)

            # Check for the specific "Incorrect username or password" error
            error_selector = "text=Incorrect username or password"
            error_element = self.page.query_selector(error_selector)
            
            if error_element and error_element.is_visible():
                print("Login failed with 'Incorrect username or password'. Retrying click...")
                # If this is the last attempt, fail loudly
                if attempt == max_retries - 1:
                    self.page.screenshot(path="login_final_attempt_failed.png")
                    raise Exception("Login failed after multiple retries: Incorrect username or password.")
                continue # Go to the next attempt to re-click

            # If no error is found, assume success and break the loop
            print("Login successful.")
            return
        
        # This should not be reached if the loop logic is correct, but as a fallback:
        raise Exception("Login failed after multiple retries.")

    def scrape(self, origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Scrapes pointsyeah.com for flight deals using the existing logged-in session.
        """
        all_deals = []

        def handle_response(response):
            if "flight/search/fetch_result" in response.url:
                try:
                    data = response.json()
                    results = data.get("data", {}).get("result")
                    if data.get("success") and results:
                        print(f"  -> Intercepted {len(results)} deals.")
                        all_deals.extend(results)
                except Exception as e:
                    print(f"  -> Could not parse JSON from response: {e}")

        self.page.on("response", handle_response)

        # --- Perform Search ---
        search_url = self._build_search_url(origin, destination, start_date, end_date)
        print(f"Navigating to search URL: {search_url}")
        self.page.goto(search_url, timeout=15000)

        print("Waiting for search results to load...")
        try:
            # Wait for the loading bar to appear and then disappear
            self.page.wait_for_selector('#nprogress', state='attached', timeout=15000)
            self.page.wait_for_selector('#nprogress', state='detached', timeout=90000)
            print("Search complete.")
        except TimeoutError:
            print("Timed out waiting for results. Results may be incomplete.")
        
        self.page.remove_listener("response", handle_response)
        
        processed_deals = self._process_deals(all_deals)
        return processed_deals

    def _build_search_url(self, origin: str, destination: str, start_date: str, end_date: str) -> str:
        multiday = "true" if start_date != end_date else "false"
        depart_date_sec = end_date if multiday == "true" else start_date
        
        return (
            f"https://www.pointsyeah.com/search?cabins=Economy%2CPremium+Economy%2CBusiness%2CFirst"
            f"&cabin=Economy"
            f"&banks=Amex%2CCapital+One%2CChase%2CBilt"
            f"&airlineProgram=AR%2CAM%2CAC%2CKL%2CAS%2CAV%2CDL%2CEK%2CEY%2CAY%2CIB%2CB6%2CLH%2CQF%2CSK%2CSQ%2CNK%2CTP%2CTK%2CUA%2CVS"
            f"&tripType=1"
            f"&adults=1"
            f"&children=0"
            f"&departure={origin}"
            f"&arrival={destination}"
            f"&departDate={start_date}"
            f"&departDateSec={depart_date_sec}"
            f"&multiday={multiday}"
        )

    def _process_deals(self, all_deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # This logic remains the same as before
        best_deals = {}
        for deal in all_deals:
            if not deal.get("routes"): continue
            program_name, deal_date = deal.get("program"), deal.get("date")
            route_str = f"{deal.get('departure')} -> {deal.get('arrival')}"
            for route in deal["routes"]:
                payment = route.get("payment", {})
                cabin, points = payment.get("cabin", "").lower(), payment.get("miles")
                if not cabin or points is None: continue
                segments = route.get("segments", [])
                if not segments: continue
                departure_time, arrival_time = segments[0].get("dt"), segments[-1].get("at")
                deal_key = (program_name, deal_date, route_str, departure_time, arrival_time)
                if deal_key not in best_deals:
                    best_deals[deal_key] = {
                        "program": program_name, "route": route_str, "date": deal_date,
                        "departure_time": departure_time, "arrival_time": arrival_time,
                        "direct": len(segments) == 1, "economy": None, "premium": None,
                        "business": None, "first": None
                    }
                cabin_key = "premium" if "premium" in cabin else "business" if "business" in cabin else "first" if "first" in cabin else "economy"
                current_best = best_deals[deal_key].get(cabin_key)
                if current_best is None or points < current_best['points']:
                    best_deals[deal_key][cabin_key] = {
                        "points": points, "fees": f"${payment.get('tax')} {payment.get('currency')}",
                        "seats": payment.get("seats")
                    }
        return list(best_deals.values())

    def close(self):
        """Closes the browser and stops the Playwright instance."""
        print("Closing browser...")
        self.browser.close()
        self.playwright.stop()

# --- Global scraper instance ---
scraper_instance: Optional[PointsYeahScraper] = None

def initialize_scraper():
    """Initializes the global scraper instance."""
    global scraper_instance
    if scraper_instance is None:
        print("Initializing PointsYeah scraper at server startup...")
        scraper_instance = PointsYeahScraper()
        print("PointsYeah scraper initialized successfully.")
    else:
        print("PointsYeah scraper already initialized.")

def close_scraper():
    """Closes the global scraper instance."""
    global scraper_instance
    if scraper_instance:
        print("Closing PointsYeah scraper at server shutdown...")
        scraper_instance.close()
        scraper_instance = None

def scrape_pointsyeah(origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Main function to scrape PointsYeah. It uses the pre-initialized global scraper instance.
    """
    global scraper_instance
    if scraper_instance is None:
        raise Exception("PointsYeah scraper has not been initialized. Please call initialize_scraper() first.")
    
    return scraper_instance.scrape(origin, destination, start_date, end_date)

if __name__ == '__main__':
    try:
        initialize_scraper()
        
        print("--- First Search ---")
        deals1 = scrape_pointsyeah("JFK", "SFO", "2025-10-10", "2025-10-10")
        if deals1:
            print(f"Found {len(deals1)} deals.")
        
        print("\n--- Second Search (should be much faster) ---")
        deals2 = scrape_pointsyeah("LAX", "HNL", "2025-11-15", "2025-11-15")
        if deals2:
            print(f"Found {len(deals2)} deals.")

    finally:
        close_scraper()