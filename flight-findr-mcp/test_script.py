import asyncio
import json
import os
import sys

# Add the parent directory to the path to allow importing the scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.pointsyeah import PointsYeahScraper

async def main_test():
    """
    Runs a test flight search and saves the output to a JSON file.
    """
    print("Initializing scraper for test...")
    scraper = await PointsYeahScraper.create(headless=True)
    
    # Define a simple test job
    test_jobs = [
        {
            "job_type": "matrix",
            "origins": ["JFK"],
            "destinations": ["LHR"],
            "start_date": "2025-10-20",
            "end_date": "2025-10-21",
            "valid_routes": [["JFK", "LHR"]]
        }
    ]

    print(f"Starting test search with {len(test_jobs)} job(s)...")
    
    try:
        results_json_str = await scraper.search_flights(test_jobs)
        
        # Define the output file path
        output_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(output_dir, "test_output.json")

        print(f"Search complete. Saving results to {output_path}...")

        # Parse and re-indent the JSON for readability in the output file
        results_data = json.loads(results_json_str)
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print("Test results saved successfully.")
        # Also print the first 500 characters of the raw output to the console
        print("\n--- Sample of Raw Output ---")
        print(results_json_str[:500])
        print("--------------------------\n")

    except Exception as e:
        print(f"An error occurred during the test: {e}")
    finally:
        print("Closing scraper...")
        await scraper.close()
        print("Test finished.")

if __name__ == "__main__":
    # To address a known issue with Playwright and asyncio on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main_test())
