import requests
import json
from pathlib import Path
from email_orchestrator.tools.straico_tool import get_client

# Try importing bs4, handle if missing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

async def brand_scraper_agent(website_url: str) -> str:
    """
    Scrapes the given website URL and uses Straico to generate a structured 
    Brand Biography (JSON).
    
    Args:
        website_url: The homepage URL of the brand.
        
    Returns:
        JSON string containing the BrandBio structure.
    """
    if not BS4_AVAILABLE:
        return json.dumps({
            "error": "BeautifulSoup4 library is missing. Please install it with `pip install beautifulsoup4`."
        })

    print(f"[BrandScraper] Fetching {website_url}...")
    try:
        # 1. Fetch content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        response = requests.get(website_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 2. Extract text
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        
        # Truncate to avoid token limits (keep first ~3000 words logic or ~12k chars)
        truncated_text = text[:12000]
        
    except Exception as e:
        return json.dumps({
            "error": f"Failed to scrape URL: {str(e)}"
        })

    # 3. Load prompt
    try:
        prompt_path = Path(__file__).parent.parent / "prompts" / "brand_scraper" / "v1.txt"
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Fallback if file not found yet
        prompt_template = "Analyze the following website text and return a JSON Brand Biography."

    full_prompt = f"{prompt_template}\n\n=== WEBSITE CONTENT ===\n{truncated_text}"

    # 4. Call LLM
    print(f"[BrandScraper] Analyzing content with Straico...")
    client = get_client()
    # Using a cheaper/faster model for scraping analysis if possible, but Straico default is fine
    result_json_str = await client.generate_text(full_prompt)
    
    # 5. Clean up result (sometimes LLMs add markdown)
    result_json_str = result_json_str.strip()
    if result_json_str.startswith("```json"):
        result_json_str = result_json_str.replace("```json", "").replace("```", "")
    
    return result_json_str
