import json
from pathlib import Path
from typing import Optional, Dict, List, Any

class CatalogManager:
    """
    Manages loading and searching of global and brand-specific catalogs.
    Provides ID-based validation and retrieval.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CatalogManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
            
        self.catalogs_dir = Path("catalogs")
        self.global_catalogs: Dict[str, List[Dict]] = {}
        self.brand_catalogs: Dict[str, Dict[str, List[Dict]]] = {} # brand -> type -> list
        
        self.known_global_types = ["structures", "angles", "cta_styles"]
        self.known_brand_types = ["personas", "transformations"]
        
        self._load_catalogs()
        self.initialized = True
    
    def _load_catalogs(self):
        """Load all JSON catalogs into memory."""
        # Load Global
        global_dir = self.catalogs_dir / "global"
        if global_dir.exists():
            for cat_type in self.known_global_types:
                path = global_dir / f"{cat_type}.json"
                if path.exists():
                    try:
                        self.global_catalogs[cat_type] = json.loads(path.read_text(encoding="utf-8"))
                        print(f"[CatalogManager] Loaded global/{cat_type}: {len(self.global_catalogs[cat_type])} items")
                    except Exception as e:
                        print(f"[CatalogManager] Error loading global/{cat_type}: {e}")
                        self.global_catalogs[cat_type] = []
        
        # Load Brands
        brands_dir = self.catalogs_dir / "brands"
        if brands_dir.exists():
            for brand_dir in brands_dir.iterdir():
                if brand_dir.is_dir():
                    brand_slug = brand_dir.name
                    self.brand_catalogs[brand_slug] = {}
                    
                    for cat_type in self.known_brand_types:
                        path = brand_dir / f"{cat_type}.json"
                        if path.exists():
                            try:
                                self.brand_catalogs[brand_slug][cat_type] = json.loads(path.read_text(encoding="utf-8"))
                                print(f"[CatalogManager] Loaded brands/{brand_slug}/{cat_type}: {len(self.brand_catalogs[brand_slug][cat_type])} items")
                            except Exception as e:
                                print(f"[CatalogManager] Error loading brands/{brand_slug}/{cat_type}: {e}")
                                self.brand_catalogs[brand_slug][cat_type] = []

    def get_global_catalog(self, cat_type: str) -> List[Dict]:
        """Get full list of items for a global catalog type."""
        return self.global_catalogs.get(cat_type, [])
    
    def get_brand_catalog(self, brand_name: str, cat_type: str) -> List[Dict]:
        """Get full list of items for a brand catalog type. Normalizes brand name to slug."""
        brand_slug = self._normalize_brand(brand_name)
        return self.brand_catalogs.get(brand_slug, {}).get(cat_type, [])
        
    def get_item(self, cat_type: str, item_id: str, brand_name: Optional[str] = None) -> Optional[Dict]:
        """
        Find a specific item by ID.
        Checks global first (if type is global), then brand (if brand provided).
        """
        # Check Global
        if cat_type in self.known_global_types:
            for item in self.get_global_catalog(cat_type):
                if item["id"] == item_id:
                    return item
        
        # Check Brand
        if brand_name and cat_type in self.known_brand_types:
            for item in self.get_brand_catalog(brand_name, cat_type):
                if item["id"] == item_id:
                    return item
                    
        return None

    def validate_id(self, cat_type: str, item_id: str, brand_name: Optional[str] = None) -> bool:
        """Check if an ID exists in the specified catalog."""
        return self.get_item(cat_type, item_id, brand_name) is not None
        
    def _normalize_brand(self, brand_name: str) -> str:
        """Convert 'PopBrush' -> 'popbrush'."""
        return brand_name.lower().replace(" ", "")

# Global instance getter
def get_catalog_manager() -> CatalogManager:
    return CatalogManager()
