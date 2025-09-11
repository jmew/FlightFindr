from scrapers.pointsyeah import PointsYeahScraper
import json
import asyncio
import time

jobs = [
    {
        "job_type": "matrix",
        "origins": ["SEA", "AKL"],
        "destinations": ["AKL", "SYD"],
        "start_date": "2025-11-07",
        "end_date": "2025-11-11",
        "valid_routes": [["SEA", "AKL"], ["AKL", "SYD"]]
    },
    {
        "job_type": "matrix",
        "origins": ["SEA", "AKL"],
        "destinations": ["AKL", "SYD"],
        "start_date": "2025-11-12",
        "end_date": "2025-11-16",
        "valid_routes": [["SEA", "AKL"], ["AKL", "SYD"]]
    },
    {
        "job_type": "matrix",
        "origins": ["DPS"],
        "destinations": ["NRT", "ICN", "SIN", "HKG", "TPE"],
        "start_date": "2025-11-20",
        "end_date": "2025-11-24",
        "valid_routes": [
            ["DPS", "NRT"], ["DPS", "ICN"], ["DPS", "SIN"],
            ["DPS", "HKG"], ["DPS", "TPE"]
        ]
    },
    {
        "job_type": "matrix",
        "origins": ["NRT", "ICN", "SIN", "HKG", "TPE"],
        "destinations": ["SEA"],
        "start_date": "2025-11-25",
        "end_date": "2025-11-29",
        "valid_routes": [
            ["NRT", "SEA"], ["ICN", "SEA"], ["SIN", "SEA"],
            ["HKG", "SEA"], ["TPE", "SEA"]
        ]
    }
]

async def main_test():
    scraper = await PointsYeahScraper.create()

    start_time = time.perf_counter()
    deals_json = await scraper.search_flights(jobs)
    end_time = time.perf_counter()
        
    deals_data = json.loads(deals_json)
    print(f"Found {len(deals_data.get('deals', []))} deals.")
    
    flight_count = 0
    for deal in deals_data.get('deals', []):
        options = deal[1]
        for option in options:
            cabins = option[3]
            flight_count += len(cabins)
    print(f"Found {flight_count} individual flight options.")

    with open("flight_results.json", 'w') as f:
        json.dump(deals_data, f, indent=2)
    
    duration = end_time - start_time
    print(f"The search took {duration} seconds.")

    if scraper:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main_test())