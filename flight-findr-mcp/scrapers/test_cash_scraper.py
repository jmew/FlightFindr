import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.utils import fetch_cash_prices

async def main():
    """
    Test function to verify the cash price scraping functionality.
    """
    print("--- Starting Cash Scraper Test ---")
    
    # Test Case 1: Single date, valid route
    print("\n[Test Case 1: Single Date - SEA to JFK]")
    deals = await fetch_cash_prices("SEA", "JFK", ["2025-10-04"], "economy")
    if deals and deals.get("flights"):
        print(f"✅ Success! Found {len(deals['flights'])} flights.")
    else:
        print("❌ Failed or no flights found.")

    # Test Case 2: Multiple dates, another valid route
    print("\n[Test Case 2: Multiple Dates - LAX to LHR]")
    deals_multi = await fetch_cash_prices("LAX", "LHR", ["2025-11-10", "2025-11-12"], "business")
    if deals_multi and deals_multi.get("flights"):
        print(f"✅ Success! Found {len(deals_multi['flights'])} flights.")
    else:
        print("❌ Failed or no flights found.")
        
    # Test Case 3: Invalid route
    print("\n[Test Case 3: Invalid Route - XYZ to ABC]")
    deals_invalid = await fetch_cash_prices("XYZ", "ABC", ["2025-12-01"], "economy")
    if not deals_invalid or not deals_invalid.get("flights"):
        print("✅ Success! Correctly handled invalid route (no flights found).")
    else:
        print(f"❌ Failed! Found {len(deals_invalid['flights'])} flights for an invalid route.")

    print("\n--- Cash Scraper Test Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
