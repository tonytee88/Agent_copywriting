import json
import os
from typing import List, Dict, Any
from datetime import datetime

from email_orchestrator.schemas import CampaignLogEntry

HISTORY_FILE = "email_history_log.json"

class HistoryManager:
    """
    Manages the persistence of email campaign history.
    Used to prevent repetition of themes, structures, and angles.
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

    def log_campaign(self, entry: CampaignLogEntry):
        """Append a new campaign entry to the log."""
        history = self._load_history()
        # Convert Pydantic model to dict
        history.append(entry.model_dump())
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
