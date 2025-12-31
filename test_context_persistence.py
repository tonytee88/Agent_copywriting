from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager
from email_orchestrator.schemas import CampaignPlan, EmailSlot
import json

# 1. Setup Mock Plan
manager = CampaignPlanManager("test_db.json")
plan_id = "TEST_CONTEXT_123"

mock_plan = {
    "campaign_id": plan_id,
    "brand_name": "TestBrand",
    "campaign_name": "Test",
    "campaign_goal": "Goal",
    "duration": "1 month",
    "total_emails": 1,
    "overarching_narrative": "Narrative",
    "promotional_balance": "50/50",
    "created_at": "2025-01-01T00:00:00",
    "status": "draft",
    "campaign_context": "THIS IS THE SECRET CONTEXT",
    "email_slots": [
        {
            "slot_number": 1,
            "email_purpose": "promotional",
            "intensity_level": "medium",
            "transformation_description": "Trans",
            "structure_id": "STRUCT",
            "angle_description": "Angle",
            "persona_description": "Persona",
            "cta_description": "CTA",
            "theme": "Theme",
            "key_message": "Msg",
            "offer_details": "Offer"
        }
    ]
}

# Save it manually
manager._save_all([mock_plan])
print("Saved plan with context.")

# 2. Simulate Import Data (No context field)
imported_data = {
    "campaign_id": plan_id,
    "email_slots": [
        {
            "slot_number": 1,
            "theme": "UPDATED THEME FROM SHEET"
        }
    ]
}

# 3. Logic Check (Mimicking update_plan_from_import)
# We can't call manager.update_plan_from_import directly if test_db is not the real one, 
# but we initialized manager with "test_db.json", so we CAN call it.

success = manager.update_plan_from_import(imported_data)
if not success:
    print("Update failed!")
    exit(1)

# 4. Reload and Verify
updated_plan = manager.get_plan(plan_id)
print(f"Reloaded Plan Context: {updated_plan.campaign_context}")
print(f"Reloaded Plan Theme: {updated_plan.email_slots[0].theme}")

if updated_plan.campaign_context == "THIS IS THE SECRET CONTEXT":
    print("SUCCESS: Context Preserved.")
else:
    print("FAILURE: Context Lost.")

# Cleanup
import os
try:
    os.remove("test_db.json")
except:
    pass
