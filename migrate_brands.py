import json
import os
from email_orchestrator.schemas import BrandBio
from email_orchestrator.tools.brand_bio_manager import BrandBioManager

DB_FILE = "brand_bio_db.json"
CATALOG_DIR = "catalogs/brands"

def migrate():
    if not os.path.exists(DB_FILE):
        print("No legacy database found.")
        return

    manager = BrandBioManager(catalog_dir=CATALOG_DIR)
    
    with open(DB_FILE, 'r') as f:
        legacy_data = json.load(f)
        
    print(f"Propagating {len(legacy_data)} brands to {CATALOG_DIR}...")
    
    for key, data in legacy_data.items():
        try:
            # Create a BrandBio object to validate and normalize
            bio = BrandBio(**data)
            
            # Save using the new manager logic (creates split files)
            # Use 'brand_id' if present as the identifier, otherwise let manager decide
            manager.save_bio(bio)
            print(f"  ✓ Migrated: {bio.brand_name}")
            
        except Exception as e:
            print(f"  ❌ Failed to migrate {key}: {e}")

if __name__ == "__main__":
    migrate()
