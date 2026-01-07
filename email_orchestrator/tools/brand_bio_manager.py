import json
import os
from typing import Dict, Optional, List
from email_orchestrator.schemas import BrandBio

BRAND_DB_FILE = "brand_bio_db.json"

class BrandBioManager:
    """
    Manages the persistence of Brand Bios.
    Allows saving retrieved bios and looking them up by brand name.
    """
    
    def __init__(self, db_file: str = BRAND_DB_FILE):
        self.db_file = db_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump({}, f)

    def _load_db(self) -> Dict[str, dict]:
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_db(self, db: Dict[str, dict]):
        with open(self.db_file, 'w') as f:
            json.dump(db, f, indent=2)

    def _generate_brand_id(self, website_url: str) -> str:
        """Generates a consistent ID from the URL (e.g. 'popbrush.fr')."""
        if not website_url:
            return "unknown_brand"
        try:
            from urllib.parse import urlparse
            if "://" not in website_url:
                website_url = "https://" + website_url
            domain = urlparse(website_url).netloc
            return domain.replace("www.", "").lower()
        except:
            return "unknown_brand"

    def save_bio(self, bio: BrandBio):
        """Saves a BrandBio, keyed by brand_id (domain) if available, else normalized name."""
        db = self._load_db()
        
        # 1. Determine Key (ID > Name)
        if bio.website_url:
            key = self._generate_brand_id(bio.website_url)
            bio.brand_id = key # Ensure ID is set on object
        else:
            # Fallback for legacy/no-url
            key = bio.brand_name.strip().lower()
            if not bio.brand_id:
                bio.brand_id = key

        db[key] = bio.model_dump()
        self._save_db(db)
        print(f"[BrandBioManager] Saved bio for '{bio.brand_name}' (ID: {key})")

    def get_bio(self, identifier: str) -> Optional[BrandBio]:
        """
        Retrieves a BrandBio by identifier.
        1. Checks if identifier is a direct key (ID).
        2. Scans for brand_name match (case-insensitive).
        """
        db = self._load_db()
        identifier = identifier.strip().lower()
        
        # 1. Direct Lookup (ID match)
        if identifier in db:
            return BrandBio(**db[identifier])
            
        # 2. Name Lookup (Scan)
        for data in db.values():
            if data.get("brand_name", "").lower() == identifier:
                return BrandBio(**data)
                
        # 3. Fuzzy Lookup (Substring)
        # Useful if Plan says "ICAR EXPERIENCE" but Bio is "ICAR"
        for data in db.values():
            stored_name = data.get("brand_name", "").strip().lower()
            if stored_name and (stored_name in identifier or identifier in stored_name):
                # Only match if reasonable length overlap to avoid "Shop" in "Shopify" false positives
                # If the shorter string is at least 3 chars?
                if len(stored_name) >= 3 and len(identifier) >= 3:
                     print(f"[BrandBioManager] Fuzzy match found: '{identifier}' matched with '{data.get('brand_name')}'")
                     return BrandBio(**data)

        return None

    def list_brands(self) -> List[str]:
        """Returns list of all brand names in DB."""
        db = self._load_db()
        return [data.get("brand_name", "Unknown") for data in db.values()]
