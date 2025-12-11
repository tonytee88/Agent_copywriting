"""
Campaign Plan Manager with auto-cleanup for old/completed plans.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from email_orchestrator.schemas import CampaignPlan, EmailSlot

# Retention settings
MAX_PLANS_PER_BRAND = 10  # Keep last 10 campaign plans per brand
ARCHIVE_COMPLETED_AFTER_DAYS = 90  # Archive completed plans after 90 days
DELETE_ARCHIVED_AFTER_DAYS = 365  # Delete archived plans after 1 year

class CampaignPlanManager:
    """
    Manages the persistence and retrieval of multi-email campaign plans.
    Includes auto-cleanup to prevent unbounded growth.
    """
    
    def __init__(self, db_path: str = "campaign_plans.json"):
        self.db_path = Path(db_path)
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create the database file if it doesn't exist."""
        if not self.db_path.exists():
            self.db_path.write_text(json.dumps([], indent=2))
    
    def _load_all(self) -> List[Dict[str, Any]]:
        """Load all campaign plans from the database."""
        try:
            return json.loads(self.db_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_all(self, plans: List[Dict[str, Any]]):
        """Save all campaign plans to the database."""
        self.db_path.write_text(json.dumps(plans, indent=2))
    
    def _cleanup_if_needed(self, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Auto-cleanup old and completed plans.
        
        Strategy:
        1. Delete archived plans older than DELETE_ARCHIVED_AFTER_DAYS
        2. Archive completed plans older than ARCHIVE_COMPLETED_AFTER_DAYS
        3. Keep last MAX_PLANS_PER_BRAND per brand (excluding archived)
        """
        now = datetime.now()
        cleaned = []
        archived_count = 0
        deleted_count = 0
        
        # Group by brand
        by_brand = {}
        
        for plan in plans:
            brand = plan.get("brand_name", "unknown")
            status = plan.get("status", "draft")
            created_str = plan.get("created_at", "")
            
            try:
                created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            except:
                created = now  # If can't parse, treat as recent
            
            age_days = (now - created).days
            
            # Delete very old archived plans
            if status == "archived" and age_days > DELETE_ARCHIVED_AFTER_DAYS:
                deleted_count += 1
                continue
            
            # Archive old completed plans
            if status == "completed" and age_days > ARCHIVE_COMPLETED_AFTER_DAYS:
                plan["status"] = "archived"
                archived_count += 1
            
            # Group by brand for per-brand limits
            if brand not in by_brand:
                by_brand[brand] = []
            by_brand[brand].append(plan)
        
        # Keep last N per brand (excluding archived)
        for brand, brand_plans in by_brand.items():
            # Separate archived from active
            archived = [p for p in brand_plans if p.get("status") == "archived"]
            active = [p for p in brand_plans if p.get("status") != "archived"]
            
            # Sort active by created_at
            active_sorted = sorted(active, key=lambda x: x.get("created_at", ""))
            
            # Keep last MAX_PLANS_PER_BRAND active plans
            kept_active = active_sorted[-MAX_PLANS_PER_BRAND:]
            
            # Keep all archived (they'll be deleted by age eventually)
            cleaned.extend(kept_active)
            cleaned.extend(archived)
        
        if archived_count > 0 or deleted_count > 0:
            print(f"[CampaignPlanManager] Cleanup: archived {archived_count}, deleted {deleted_count} old plans")
        
        return cleaned
    
    def save_plan(self, plan: CampaignPlan) -> None:
        """Save a new campaign plan or update an existing one."""
        plans = self._load_all()
        
        # Remove existing plan with same ID if present
        plans = [p for p in plans if p.get("campaign_id") != plan.campaign_id]
        
        # Add new plan
        plans.append(plan.model_dump())
        
        # Auto-cleanup
        plans = self._cleanup_if_needed(plans)
        
        self._save_all(plans)
        print(f"[CampaignPlanManager] Saved plan: {plan.campaign_id}")
    
    def get_plan(self, campaign_id: str) -> Optional[CampaignPlan]:
        """Retrieve a campaign plan by ID."""
        plans = self._load_all()
        for plan_dict in plans:
            if plan_dict.get("campaign_id") == campaign_id:
                return CampaignPlan(**plan_dict)
        return None
    
    def get_plans_by_brand(self, brand_name: str) -> List[CampaignPlan]:
        """Get all campaign plans for a specific brand."""
        plans = self._load_all()
        brand_plans = [
            CampaignPlan(**p) for p in plans
            if p.get("brand_name", "").lower() == brand_name.lower()
            and p.get("status") != "archived"  # Exclude archived
        ]
        return sorted(brand_plans, key=lambda x: x.created_at, reverse=True)
    
    def update_plan_status(self, campaign_id: str, new_status: str) -> bool:
        """Update the status of a campaign plan."""
        plans = self._load_all()
        updated = False
        
        for plan in plans:
            if plan.get("campaign_id") == campaign_id:
                plan["status"] = new_status
                updated = True
                break
        
        if updated:
            self._save_all(plans)
            print(f"[CampaignPlanManager] Updated status for {campaign_id}: {new_status}")
        
        return updated
    
    def get_next_email_slot(self, campaign_id: str) -> Optional[EmailSlot]:
        """
        Get the next email slot that hasn't been sent yet.
        Returns None if all slots are complete.
        """
        plan = self.get_plan(campaign_id)
        if not plan:
            return None
        
        # Find first slot without a "sent" marker
        # (We'd need to track this - for now just return first slot)
        # TODO: Add slot completion tracking
        if plan.email_slots:
            return plan.email_slots[0]
        
        return None
    
    def get_slot_by_number(self, campaign_id: str, slot_number: int) -> Optional[EmailSlot]:
        """Get a specific email slot by its number."""
        plan = self.get_plan(campaign_id)
        if not plan:
            return None
        
        for slot in plan.email_slots:
            if slot.slot_number == slot_number:
                return slot
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about campaign plans."""
        plans = self._load_all()
        
        by_brand = {}
        by_status = {}
        
        for plan in plans:
            brand = plan.get("brand_name", "unknown")
            status = plan.get("status", "draft")
            
            by_brand[brand] = by_brand.get(brand, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_plans": len(plans),
            "brands": len(by_brand),
            "plans_by_brand": by_brand,
            "plans_by_status": by_status,
            "max_per_brand": MAX_PLANS_PER_BRAND,
            "archive_after_days": ARCHIVE_COMPLETED_AFTER_DAYS,
            "delete_after_days": DELETE_ARCHIVED_AFTER_DAYS
        }
