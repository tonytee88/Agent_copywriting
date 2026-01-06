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

    # Try importing googlesearch
    try:
        from googlesearch import search
        SEARCH_AVAILABLE = True
    except ImportError:
        SEARCH_AVAILABLE = False
        print("[BrandScraper] Warning: googlesearch-python not installed. Search fallback disabled.")

    print(f"[BrandScraper] Fetching {website_url}...")
    
    # 1. URL Sanitization
    target_url = website_url
    if not target_url.startswith("http"):
        target_url = "https://" + target_url.strip()
        print(f"[BrandScraper] Auto-corrected URL to: {target_url}")

    soup_text = ""
    scrape_success = False

    try:
        # Attempt to use cloudscraper to bypass Cloudflare
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper(browser='chrome')
            response = scraper.get(target_url, timeout=15)
            response.raise_for_status()
            print("[BrandScraper] Access Code: Cloudscraper Success")
        except (ImportError, Exception) as cs_error:
            # Fallback to standard requests if Cloudscraper fails/missing
            print(f"[BrandScraper] Cloudscraper failed/missing ({cs_error}), falling back to standard requests...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            response = requests.get(target_url, headers=headers, timeout=10)
            response.raise_for_status()

        # 2. Extract text
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.extract()
            
        soup_text = soup.get_text(separator=' ', strip=True)
        scrape_success = True
        
    except Exception as e:
        print(f"[BrandScraper] Direct scrape failed: {e}")
        
        if SEARCH_AVAILABLE:
            print("[BrandScraper] ⚠️ Website failed. Falling back to Google Search...")
            try:
                # Infer brand name for search
                from urllib.parse import urlparse
                domain = urlparse(target_url).netloc.replace("www.", "")
                brand_guess = domain.split('.')[0]
                
                query = f"{brand_guess} brand mission target audience products"
                print(f"[BrandScraper] Searching for: '{query}'")
                
                search_results = list(search(query, num_results=3, advanced=True))
                
                combined_text = f"SEARCH RESULTS for '{brand_guess}':\n\n"
                
                for res in search_results:
                     try:
                         # Lightweight fetch of search result text
                         r = requests.get(res.url, headers=headers, timeout=5)
                         if r.status_code == 200:
                             s = BeautifulSoup(r.content, 'html.parser')
                             for script in s(["script", "style"]): script.extract()
                             txt = s.get_text(separator=' ', strip=True)[:1000] # Limit per result
                             combined_text += f"-- Source: {res.url} --\n{res.title}\n{res.description}\nContent: {txt}\n\n"
                     except:
                         continue
                
                soup_text = combined_text
                if len(soup_text) > 200: # Relaxed check
                     scrape_success = True
                     print(f"[BrandScraper] Successfully gathered {len(soup_text)} chars from search.")
                else:
                     # Attempt to return whatever we have if it's not empty, even if small
                     if len(soup_text) > 50:
                         scrape_success = True
                         print(f"[BrandScraper] Warning: Low data from search ({len(soup_text)} chars), but proceeding.")
                     else:
                         # Fallback to Manual Input Prompt mechanism (by returning a specific error structure)
                         return json.dumps({
                             "error": f"Automated discovery failed for {target_url}. Google Search blocked or yielded no data. Please provide brand details (Industry, Audience, USP) in your prompt notes or try again later."
                         })

            except Exception as search_e:
                 print(f"[BrandScraper] Search Exception: {search_e}")
                 return json.dumps({"error": f"Search fallback failed: {search_e}. Please provide brand details manually."})
        else:
            return json.dumps({
                "error": f"Failed to scrape URL: {str(e)} and Search fallback unavailable."
            })
            
    # Truncate to avoid token limits (keep first ~3000 words logic or ~12k chars)
    truncated_text = soup_text[:12000]

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
