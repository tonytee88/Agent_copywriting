from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager

# Mock data simulating a sheet where Slot 2 was deleted (only Slot 1 remains)
# We also update the theme to prove data sync works.
mock_imported_data = {
    "campaign_id": "20240130172200",
    "email_slots": [
        {
            "slot_number": 1,
            "theme": "Simulated Sync Theme Update",
            "cta_description": "Shop Now"
            # Fields required to avoid None errors if not present? 
            # My logic uses existing slot as base if present, so missing fields are fine.
        }
    ]
}

manager = CampaignPlanManager()
plan = manager.get_plan("20240130172200")
print(f"Before: {len(plan.email_slots)} slots")

# Run Sync
manager.update_plan_from_import(mock_imported_data)

# Verify
plan = manager.get_plan("20240130172200")
print(f"After: {len(plan.email_slots)} slots")
print(f"Slot 1 Theme: {plan.email_slots[0].theme}")
