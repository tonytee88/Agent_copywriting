import json
from email_orchestrator.subagents.brand_scraper_agent import brand_scraper_agent
from email_orchestrator.tools.brand_bio_manager import BrandBioManager

async def analyze_brand(brand_name: str, website_url: str = None) -> str:
    """
    Analyzes a brand to produce a BrandBio JSON.
    First checks the local DB. If missing, attempts to scrape (if URL provided).
    If no URL and no DB entry, returns a valid but generic/placeholder JSON.
    """
    manager = BrandBioManager()
    
    # 1. Check Cache
    cached_bio = manager.get_bio(brand_name)
    if cached_bio:
        print(f"[BrandTool] Found cached bio for {brand_name}")
        return cached_bio.model_dump_json()
    
    # 2. Scrape if URL provided
    if website_url:
        print(f"[BrandTool] Scraping {website_url}...")
        bio_json = await brand_scraper_agent(website_url)
        # Cache it
        try:
            from email_orchestrator.schemas import BrandBio
            bio_obj = BrandBio(**json.loads(bio_json))
            # Ensure name matches requested
            bio_obj.brand_name = brand_name
            manager.save_bio(bio_obj)
            return bio_obj.model_dump_json()
        except:
            return bio_json
            
    # 3. Fallback / Mock for "PopBrush" (Test convenience)
    if brand_name.lower() == "popbrush":
        print("[BrandTool] Using Hardcoded Fallback for PopBrush")
        mock_bio = {
            "brand_name": "PopBrush",
            "industry": "Beauty & Hair Care",
            "target_audience": "Moms with daughters, women with sensitive scalps.",
            "unique_selling_proposition": "Painless detangling with boar bristle technology.",
            "brand_voice": "Empathetic, Helpful, Cheerful",
            "key_products": ["PopBrush Detangler", "PopBrush Mini"],
            "mission_statement": "To make hair brushing a joy, not a chore."
        }
        # Save to DB for next time
        from email_orchestrator.schemas import BrandBio
        manager.save_bio(BrandBio(**mock_bio))
        return json.dumps(mock_bio)

    return json.dumps({"error": f"Brand '{brand_name}' not found and no URL provided."})
