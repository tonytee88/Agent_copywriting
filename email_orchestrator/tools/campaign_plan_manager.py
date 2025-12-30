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
                # comparison fix: ensure both are naive
                if created.tzinfo is not None:
                    created = created.replace(tzinfo=None)
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
    
    def get_plans_by_brand(self, brand_name: str, brand_id: Optional[str] = None) -> List[CampaignPlan]:
        """Get all campaign plans for a specific brand."""
        plans = self._load_all()
        
        filtered_plans = []
        for p in plans:
            # Skip archived
            if p.get("status") == "archived":
                continue
                
            # Filter logic: Prefer brand_id if both have it. Fallback to name.
            p_brand_id = p.get("brand_id")
            p_brand_name = p.get("brand_name", "")
            
            if brand_id and p_brand_id:
                if p_brand_id == brand_id:
                    filtered_plans.append(CampaignPlan(**p))
            elif brand_name and p_brand_name.lower() == brand_name.lower():
                filtered_plans.append(CampaignPlan(**p))
                
        return sorted(filtered_plans, key=lambda x: x.created_at, reverse=True)

    def list_all_plans(self) -> List[CampaignPlan]:
        """List all available campaign plans."""
        plans = self._load_all()
        return [CampaignPlan(**p) for p in plans]
    
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
        
    def update_plan_from_import(self, imported_data: Dict[str, Any]) -> bool:
        """
        Updates an existing plan with data imported from Google Sheets.
        Strictly overrides text fields.
        """
        campaign_id = imported_data.get("campaign_id")
        if not campaign_id:
            print("[CampaignPlanManager] Update failed: No campaign_id in imported data.")
            return False
            
        plans = self._load_all()
        target_index = -1
        
        for i, p in enumerate(plans):
            if p.get("campaign_id") == campaign_id:
                target_index = i
                break
        
        if target_index == -1:
            print(f"[CampaignPlanManager] Plan {campaign_id} not found.")
            return False
        
        # Merge Data
        target_plan = plans[target_index]
        
        # 1. Update Top-Level fields if present (e.g. Narrative)
        # Note: Current importer mainly focuses on slots, but we can extend.
        
        # 2. Update Slots
        imported_slots = imported_data.get("email_slots", [])
        current_slots = target_plan.get("email_slots", []) # Pydantic model is dict here actually
        
        # Create map of current slots by number to preserve non-sheet fields (like connection_to_prev)
        # Note: current_slots is a list of dicts.
        current_slot_map = {s.get("slot_number"): s for s in current_slots}
        
        updated_slots_list = []
        changes_made = False
        
        # We strictly iterate over IMPORTED slots. 
        # If a slot is in imported but not current -> We should probably add it (or warn).
        # If a slot is in current but not imported -> It gets dropped (Deletions).
        
        for new_slot in imported_slots:
            s_num = new_slot.get("slot_number")
            
            # Base object to use: existing or new
            if s_num in current_slot_map:
                base_slot = current_slot_map[s_num]
            else:
                # User added a row? We need a basic structure.
                # Since we don't know all fields, we initialize with defaults + imported data.
                # This might be tricky if schema requires fields not in sheet.
                # For now, let's assume we copy new_slot and hope for best (or skip adding new rows for safety if schema is strict).
                # Safer: Warn about new rows being unsupported for now, Or try to support.
                # Let's try to support by using new_slot as base.
                base_slot = new_slot
                changes_made = True
            
            # List of fields to sync from Sheet
            fields_to_sync = [
                "theme", "email_purpose", "intensity_level", 
                "transformation_description", "angle_description",
                "structure_id", "persona_description", 
                "key_message", "offer_details", "offer_placement",
                "cta_description"
            ]
            
            # Ensure defaults for required fields if missing (Schema safety)
            if "cta_description" not in base_slot or not base_slot["cta_description"]:
                 base_slot["cta_description"] = "Shop Now" # Default fallback
            
            for field in fields_to_sync:
                # Only update if sheet has a value (non-empty)
                val = new_slot.get(field)
                if val is not None:
                    if base_slot.get(field) != val:
                        base_slot[field] = val
                        changes_made = True
            
            updated_slots_list.append(base_slot)
            
        # Check if deletions occurred
        if len(updated_slots_list) != len(current_slots):
            changes_made = True
            print(f"[CampaignPlanManager] Plan slot count changed: {len(current_slots)} -> {len(updated_slots_list)}")
            
        if changes_made:
            target_plan["email_slots"] = updated_slots_list
            plans[target_index] = target_plan
            self._save_all(plans)
            print(f"[CampaignPlanManager] ✓ Synced plan {campaign_id} with Google Sheet data (Strict Sync).")
            return True
        else:
            print(f"[CampaignPlanManager] No changes detected during sync for {campaign_id}.")
            return True
