import json
from pathlib import Path
from email_orchestrator.tools.straico_tool import get_client
from email_orchestrator.config import MODEL_RESEARCHER

async def brand_scraper_agent(website_url: str) -> str:
    """
    Uses a Perplexity-powered model (via Straico) to research a brand URL 
    and generate a structured BrandBio JSON.
    
    Args:
        website_url: The homepage URL of the brand (e.g. "https://ohydration.com").
        
    Returns:
        JSON string containing the BrandBio structure.
    """
    print(f"[BrandScraper] Researching {website_url} using {MODEL_RESEARCHER}...")
    
    # 1. Load the prompt template (contains schema definitions)
    try:
        prompt_path = Path(__file__).parent.parent / "prompts" / "brand_scraper" / "v1.txt"
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return json.dumps({"error": "Prompt file not found."})

    # 2. Construct the prompt
    # We simply give the URL to the research model. It can browse.
    full_prompt = f"{prompt_template}\n\n=== TARGET BRAND URL ===\n{website_url}\n\nPlease research this specific URL to find the information."

    # 3. Call LLM (Perplexity)
    try:
        client = get_client()
        # Pass the specific research model
        result_json_str = await client.generate_text(full_prompt, model=MODEL_RESEARCHER)
        
        # 4. Clean up result
        result_json_str = result_json_str.strip()
        if result_json_str.startswith("```json"):
            result_json_str = result_json_str.replace("```json", "").replace("```", "")
            
        # Basic validation
        if "{" not in result_json_str:
            raise ValueError("Model did not return JSON")
            
        print(f"[BrandScraper] Research complete. (Length: {len(result_json_str)})")
        return result_json_str

    except Exception as e:
        print(f"[BrandScraper] Research failed: {e}")
        return json.dumps({
            "error": f"Brand research failed: {str(e)}",
            "website_url": website_url
        })
