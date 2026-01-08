import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from email_orchestrator.schemas import BrandBio

CATALOG_DIR = "catalogs/brands"

class BrandBioManager:
    """
    Manages the persistence of Brand Bios using a file-based catalog.
    Source of Truth: 'catalogs/brands/{brand_id}.json'
    """
    
    def __init__(self, catalog_dir: str = CATALOG_DIR):
        self.catalog_dir = catalog_dir
        os.makedirs(self.catalog_dir, exist_ok=True)

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
        """Saves a BrandBio to its own JSON file in the catalog."""
        
        # 1. Determine Key (ID > Name)
        if bio.website_url:
            key = self._generate_brand_id(bio.website_url)
            bio.brand_id = key 
        elif bio.brand_id:
            key = bio.brand_id
        else:
            # Fallback for legacy/no-url
            key = bio.brand_name.strip().lower().replace(" ", "-")
            bio.brand_id = key

        file_path = os.path.join(self.catalog_dir, f"{key}.json")
        
        with open(file_path, 'w') as f:
            json.dump(bio.model_dump(), f, indent=4, ensure_ascii=False)
            
        print(f"[BrandBioManager] Saved bio for '{bio.brand_name}' to {file_path}")

    def get_bio(self, identifier: str) -> Optional[BrandBio]:
        """
        Retrieves a BrandBio by identifier.
        1. Checks for file exact match (identifier.json)
        2. Scans all files for name match (slower but necessary for non-ID lookups)
        """
        identifier = identifier.strip().lower()
        
        # 1. Direct File Lookup (Fastest)
        # Try both direct ID ("popbrush.fr") and ID + .json ("popbrush.fr.json")
        possible_filenames = [f"{identifier}.json", identifier if identifier.endswith(".json") else f"{identifier}.json"]
        
        for fname in possible_filenames:
            fpath = os.path.join(self.catalog_dir, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r') as f:
                        data = json.load(f)
                        return BrandBio(**data)
                except Exception as e:
                    print(f"[BrandBioManager] Error reading {fpath}: {e}")

        # 2. Scan All Files (Name Match)
        # Needed if we ask for "PopBrush" but file is "popbrush.fr.json"
        for fname in os.listdir(self.catalog_dir):
            if not fname.endswith(".json"): continue
            
            try:
                with open(os.path.join(self.catalog_dir, fname), 'r') as f:
                    data = json.load(f)
                    # Name match
                    if data.get("brand_name", "").lower() == identifier:
                        return BrandBio(**data)
                    # ID match inside file
                    if data.get("brand_id", "").lower() == identifier:
                        return BrandBio(**data)
            except:
                continue

        return None

    def list_brands(self) -> List[str]:
        """Returns list of all brand names in catalog."""
        names = []
        for fname in os.listdir(self.catalog_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.catalog_dir, fname), 'r') as f:
                        data = json.load(f)
                        names.append(data.get("brand_name", "Unknown"))
                except:
                    pass
        return names
