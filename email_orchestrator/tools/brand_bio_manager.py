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

    def save_bio(self, bio: BrandBio):
        """Saves a BrandBio, keyed by the normalized brand name."""
        db = self._load_db()
        key = bio.brand_name.strip().lower()
        db[key] = bio.model_dump()
        self._save_db(db)
        print(f"[BrandBioManager] Saved bio for '{bio.brand_name}'")

    def get_bio(self, brand_name: str) -> Optional[BrandBio]:
        """Retrieves a BrandBio by name (case-insensitive)."""
        db = self._load_db()
        key = brand_name.strip().lower()
        data = db.get(key)
        if data:
            return BrandBio(**data)
        return None

    def list_brands(self) -> List[str]:
        """Returns list of all brand names in DB."""
        db = self._load_db()
        return [data["brand_name"] for data in db.values()]
