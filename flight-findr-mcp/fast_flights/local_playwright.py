from typing import Any
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

class Response:
    status_code = 200
    text: str
    text_markdown: str
    def __init__(self, text: str):
        self.text = text
        self.text_markdown = text

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def fetch_with_playwright(url: str):
    """
    Fetches the main content of a Google Flights page.

    It intelligently waits for either the flight results to load or a
    "no results" message to appear, whichever comes first.
    """
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            # Increase navigation timeout for slow connections
            await page.goto(url, timeout=15000, wait_until='domcontentloaded')

            # Handle consent dialog if it appears
            if "consent.google.com" in page.url:
                try:
                    accept_button = page.locator('button:has-text("Accept all")').or_(page.locator('button:has-text("I agree")'))
                    await accept_button.click(timeout=5000)
                except PlaywrightTimeoutError:
                    print("Consent dialog did not appear or was not clicked in time.")
                except Exception as e:
                    print(f"An error occurred while handling consent: {e}")


            # This JavaScript code will run in the browser.
            # It creates two promises: one for the results and one for the "no results" message.
            # Promise.race() resolves as soon as the first of these promises resolves.
            check_for_element_js = """
            () => {
                const resultsSelector = '.eQ35Ce';
                const noResultsSelector = '.BgYkof';

                const waitForResults = new Promise((resolve) => {
                    const interval = setInterval(() => {
                        if (document.querySelector(resultsSelector)) {
                            clearInterval(interval);
                            resolve('results_found');
                        }
                    }, 100); // Check every 100ms
                });

                const waitForNoResults = new Promise((resolve) => {
                    const interval = setInterval(() => {
                        if (document.querySelector(noResultsSelector)) {
                            clearInterval(interval);
                            resolve('no_results_found');
                        }
                    }, 100);
                });

                // Race the two promises and return the result of the one that finishes first
                return Promise.race([waitForResults, waitForNoResults]);
            }
            """

            # Evaluate the script and wait for the result
            outcome = await page.evaluate(check_for_element_js)

            # --- Handle the outcome ---
            if outcome == 'no_results_found':
                print("No flight results found.")
                return None
            elif outcome == 'results_found':
                body = await page.evaluate(
                    "() => document.querySelector('[role=\"main\"]').innerHTML"
                )
                return body
            else:
                # This case should ideally not be reached
                print("An unexpected outcome occurred while waiting for elements.")
                return None

        except PlaywrightTimeoutError:
            print(f"Timeout error navigating to or processing page: {url}")
            return None
        except Exception as e:
            raise e
        finally:
            # Ensure the browser is always closed
            await browser.close()

def local_playwright_fetch(params: dict) -> Any:
    url = "https://www.google.com/travel/flights?" + "&".join(f"{k}={v}" for k, v in params.items())
    body = asyncio.run(fetch_with_playwright(url))

    if body is None:
        return None

    return Response(body)