import json
import os
from typing import List, Dict, Any
from datetime import datetime

from email_orchestrator.schemas import CampaignLogEntry

HISTORY_FILE = "email_history_log.json"
MAX_ENTRIES_PER_BRAND = 50  # Keep last 50 emails per brand
TOTAL_MAX_ENTRIES = 500  # Hard limit across all brands

class HistoryManager:
    """
    Manages the persistence of email campaign history.
    Used to prevent repetition of themes, structures, and angles.
    
    Auto-cleanup: Keeps last 50 emails per brand, max 500 total.
    """
    
    def __init__(self, history_file: str = HISTORY_FILE):
        self.history_file = history_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump([], f)

    def _load_history(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_history(self, history: List[Dict[str, Any]]):
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def _cleanup_if_needed(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Auto-cleanup to prevent unbounded growth.
        
        Strategy:
        1. Keep last MAX_ENTRIES_PER_BRAND per brand
        2. If still over TOTAL_MAX_ENTRIES, keep newest across all brands
        """
        # Group by brand
        by_brand = {}
        for entry in history:
            brand = entry.get("brand_name", "unknown")
            if brand not in by_brand:
                by_brand[brand] = []
            by_brand[brand].append(entry)
        
        # Keep last N per brand
        cleaned = []
        for brand, entries in by_brand.items():
            # Sort by timestamp (newest last)
            sorted_entries = sorted(entries, key=lambda x: x.get("timestamp", ""))
            # Keep last MAX_ENTRIES_PER_BRAND
            cleaned.extend(sorted_entries[-MAX_ENTRIES_PER_BRAND:])
        
        # If still too many, keep newest across all brands
        if len(cleaned) > TOTAL_MAX_ENTRIES:
            cleaned = sorted(cleaned, key=lambda x: x.get("timestamp", ""))
            cleaned = cleaned[-TOTAL_MAX_ENTRIES:]
            print(f"[HistoryManager] Cleaned up history: kept {len(cleaned)} newest entries")
        
        return cleaned

    def log_campaign(self, entry: CampaignLogEntry):
        """Append a new campaign entry to the log with auto-cleanup."""
        history = self._load_history()
        # Convert Pydantic model to dict
        history.append(entry.model_dump())
        
        # Auto-cleanup
        history = self._cleanup_if_needed(history)
        
        self._save_history(history)

    def get_recent_campaigns(self, brand_name: str, limit: int = 10) -> List[CampaignLogEntry]:
        """
        Retrieve the most recent N campaigns for a specific brand.
        Returns them as Pydantic models.
        """
        all_history = self._load_history()
        
        # Filter by brand
        brand_history = [
            item for item in all_history 
            if item.get("brand_name", "").lower() == brand_name.lower()
        ]
        
        # Sort by timestamp (assuming ISO format strings), newest last
        # But we want recent ones, so let's take the slice from the end.
        # Assuming append-only, the last ones are the newest.
        
        recent_dicts = brand_history[-limit:]
        
        # Convert back to Pydantic models
        return [CampaignLogEntry(**item) for item in recent_dicts]

    def get_usage_summary(self, brand_name: str, limit: int = 10) -> Dict[str, List[str]]:
        """
        Returns a summary of recently used elements for quick checking.
        """
        recent = self.get_recent_campaigns(brand_name, limit)
        return {
            "transformations": [c.transformation_used for c in recent],
            "structures": [c.structure_used for c in recent],
            "storytelling_angles": [c.storytelling_angle_used for c in recent],
            "offer_placements": [c.offer_placement_used for c in recent],
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the history log."""
        history = self._load_history()
        
        # Count by brand
        by_brand = {}
        for entry in history:
            brand = entry.get("brand_name", "unknown")
            by_brand[brand] = by_brand.get(brand, 0) + 1
        
        return {
            "total_entries": len(history),
            "brands": len(by_brand),
            "entries_by_brand": by_brand,
            "max_per_brand": MAX_ENTRIES_PER_BRAND,
            "total_max": TOTAL_MAX_ENTRIES
        }
