from playwright.async_api import async_playwright, Page, Browser, Playwright, TimeoutError
import json
import asyncio
import os
from typing import List, Dict, Any, Optional

class PointsYeahScraper:
    """
    A class to manage a persistent browser session for scraping PointsYeah.com,
    optimizing performance by logging in only once.
    """
    def __init__(self, playwright: Playwright, headless: bool = True):
        self.playwright: Playwright = playwright
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start(self):
        """Initializes the browser and logs in."""
        proxy_url = os.environ.get("HTTP_PROXY")
        proxy_settings = {"server": proxy_url} if proxy_url else None
        if proxy_settings:
            print("Using proxy for PointsYeah scraper.")

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
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ]
        )
        self.page = await self._create_new_page()
        await self._login()

    async def _create_new_page(self) -> Page:
        """Creates a new page with anti-bot detection scripts and resource blocking."""
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light'
        )
        page = await context.new_page()

        async def intelligent_block(route):
            if "flight/search/fetch_result" in route.request.url or "flight/search/create_task" in route.request.url:
                await route.continue_()
            elif route.request.resource_type in ["image", "font", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", intelligent_block)
        
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
        await page.add_init_script(stealth_script)
        return page

    async def _login(self):
        """Performs a one-time login to PointsYeah."""
        if not self.page: return
        try:
            print("Navigating to login page...")
            await self.page.goto("https://www.pointsyeah.com/login", timeout=10000, wait_until="domcontentloaded")
            await self.page.wait_for_selector('input[name="username"]', state="visible", timeout=10000)
            
            print("Entering credentials...")
            await self.page.fill('input[name="username"]', "jepara2048@mogash.com")
            await self.page.fill('input[name="password"]', "Password1!")
        
        except Exception as e:
            print(f"An error occurred during initial page load and form fill: {e}")
            await self.close()
            raise

        max_retries = 3
        for attempt in range(max_retries):
            print(f"Clicking 'Sign In' (Attempt {attempt + 1}/{max_retries})...")
            await self.page.locator('button[type="submit"].amplify-button--primary').click()
            await asyncio.sleep(1)

            error_element = await self.page.query_selector("text=Incorrect username or password")
            if error_element and await error_element.is_visible():
                print("Login failed with 'Incorrect username or password'. Retrying click...")
                if attempt == max_retries - 1:
                    raise Exception("Login failed after multiple retries: Incorrect username or password.")
                continue
            
            print("Login successful.")
            return
        
        raise Exception("Login failed after multiple retries.")

    async def scrape(self, origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Scrapes pointsyeah.com for flight deals."""
        if not self.page:
            raise Exception("Scraper not initialized properly.")

        all_deals = []
        async def handle_response(response):
            if "flight/search/fetch_result" in response.url:
                try:
                    data = await response.json()
                    results = data.get("data", {}).get("result")
                    if data.get("success") and results:
                        print(f"  -> Intercepted {len(results)} deals.")
                        all_deals.extend(results)
                except Exception as e:
                    print(f"  -> Could not parse JSON from response: {e}")

        self.page.on("response", handle_response)

        search_url = self._build_search_url(origin, destination, start_date, end_date)
        print(f"Navigating to search URL: {search_url}")
        await self.page.goto(search_url, timeout=15000)

        print("Waiting for search results to load...")
        try:
            await self.page.wait_for_selector('#nprogress', state='attached', timeout=15000)
            await self.page.wait_for_selector('#nprogress', state='detached', timeout=90000)
            print("Search complete.")
        except TimeoutError:
            print("Timed out waiting for results. Results may be incomplete.")
        
        self.page.remove_listener("response", handle_response)
        return self._process_deals(all_deals)

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

    async def close(self):
        """Closes the browser."""
        print("Closing browser...")
        if self.browser:
            await self.browser.close()

# --- Global scraper instance management ---
scraper_instance: Optional[PointsYeahScraper] = None
playwright_instance: Optional[Playwright] = None

async def initialize_scraper():
    """Initializes the global scraper instance."""
    global scraper_instance, playwright_instance
    if scraper_instance is None:
        print("Initializing PointsYeah scraper at server startup...")
        playwright_instance = await async_playwright().start()
        scraper_instance = PointsYeahScraper(playwright_instance)
        await scraper_instance.start()
        print("PointsYeah scraper initialized successfully.")
    else:
        print("PointsYeah scraper already initialized.")

async def close_scraper():
    """Closes the global scraper instance."""
    global scraper_instance, playwright_instance
    if scraper_instance:
        print("Closing PointsYeah scraper at server shutdown...")
        await scraper_instance.close()
        scraper_instance = None
    if playwright_instance:
        await playwright_instance.stop()
        playwright_instance = None

async def scrape_pointsyeah(origin: str, destination: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Main function to scrape PointsYeah."""
    global scraper_instance
    if scraper_instance is None:
        await initialize_scraper()
    
    if scraper_instance:
        return await scraper_instance.scrape(origin, destination, start_date, end_date)
    raise Exception("Failed to initialize scraper.")

async def main_test():
    try:
        await initialize_scraper()
        
        print("--- First Search ---")
        deals1 = await scrape_pointsyeah("JFK", "SFO", "2025-10-10", "2025-10-10")
        if deals1:
            print(f"Found {len(deals1)} deals.")
        
        print("\n--- Second Search (should be much faster) ---")
        deals2 = await scrape_pointsyeah("LAX", "HNL", "2025-11-15", "2025-11-15")
        if deals2:
            print(f"Found {len(deals2)} deals.")

    finally:
        await close_scraper()

if __name__ == '__main__':
    asyncio.run(main_test())
