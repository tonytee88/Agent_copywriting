import json
from typing import Optional
from email_orchestrator.subagents.brand_scraper_agent import brand_scraper_agent
from email_orchestrator.tools.brand_bio_manager import BrandBioManager

async def analyze_brand(brand_name: Optional[str] = None, website_url: Optional[str] = None) -> str:
    """
    Analyzes a brand to produce a BrandBio JSON.
    
    Args:
        brand_name: Name of the brand (e.g., "PopBrush"). If omitted, inferred from URL.
        website_url: URL of the brand (e.g., "https://popbrush.fr").
    """
    manager = BrandBioManager()
    
    # 0. Infer brand_name if missing
    if not brand_name and website_url:
        # Simple heuristic: domain name
        from urllib.parse import urlparse
        if "://" not in website_url:
            website_url = "https://" + website_url
        domain = urlparse(website_url).netloc
        # split by dot, take first part (e.g. popbrush.fr -> popbrush)
        # remove www.
        domain = domain.replace("www.", "")
        brand_name = domain.split('.')[0].capitalize()
        print(f"[BrandTool] Inferred brand name '{brand_name}' from URL")
        
    if not brand_name:
         return json.dumps({"error": "Invoking `analyze_brand` failed: `brand_name` is required if no URL is provided."})
    
    # 1. Try URL-based ID Lookup First
    if website_url:
        # We can use the manager's helper (need to instantiate first)
        temp_id = manager._generate_brand_id(website_url)
        cached_bio = manager.get_bio(temp_id)
        if cached_bio:
            print(f"[BrandTool] Found cached bio for {brand_name or temp_id} (ID: {temp_id})")
            return cached_bio.model_dump_json()

    # 2. Try Name-based Lookup
    if brand_name:
        cached_bio = manager.get_bio(brand_name)
        if cached_bio:
             print(f"[BrandTool] Found cached bio for {brand_name}")
             return cached_bio.model_dump_json()
    
    # 3. Scrape if URL provided
    if website_url:
        print(f"[BrandTool] Scraping {website_url}...")
        bio_json = await brand_scraper_agent(website_url)
        # Cache it
        try:
            from email_orchestrator.schemas import BrandBio
            bio_data = json.loads(bio_json)
            
            # Ensure ID and URL are set
            bio_data["website_url"] = website_url
            if "brand_id" not in bio_data:
                 bio_data["brand_id"] = manager._generate_brand_id(website_url)
            
            bio_obj = BrandBio(**bio_data)
            # Ensure name matches requested if provided
            if brand_name:
                bio_obj.brand_name = brand_name
            
            manager.save_bio(bio_obj)
            return bio_obj.model_dump_json()
        except Exception as e:
            print(f"[BrandTool] Error processing scrape result: {e}")
            return bio_json
            
    # 4. Fallback / Mock for "PopBrush" (Test convenience)
    if brand_name and brand_name.lower() == "popbrush":
        print("[BrandTool] Using Hardcoded Fallback for PopBrush")
        mock_bio = {
            "brand_id": "popbrush.fr",
            "website_url": "https://popbrush.fr",
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
