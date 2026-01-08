import asyncio
import json
import os
from email_orchestrator.tools.brand_scraper_tool import analyze_brand

async def run_test():
    url = "https://ohydration.com"
    print(f"Executing analyze_brand for {url}...")
    
    # This calls the full pipeline: Tool -> Scraper -> Manager -> File System
    result_json = await analyze_brand(website_url=url)
    
    # Analyze results
    try:
        data = json.loads(result_json)
        print("\n=== FINAL DB SAVED STATE ===")
        print(f"Product Description: {data.get('product_description')}")
        print(f"Avoid Topics: {data.get('avoid_topics')}")
        
        # Verify file existence
        expected_path = "catalogs/brands/ohydration.com.json"
        if os.path.exists(expected_path):
             print(f"\n✅ SUCCESS: File found at {expected_path}")
        else:
             print(f"\n❌ FAILURE: File NOT found at {expected_path}")
            
    except Exception as e:
        print(f"Error parsing result: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
