
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager

def inspect_latest_plan():
    manager = CampaignPlanManager()
    plans = manager.list_all_plans()
    if not plans:
        print("No plans found.")
        return

    # Sort by created_at or campaign_id to get the latest
    all_plans = sorted(plans, key=lambda x: x.campaign_id)
    latest_plans = all_plans[-5:]
    
    for plan in latest_plans:
        print(f"\n=== Plan: {plan.campaign_name} ({plan.campaign_id}) ===")
        print("Email Transformations:")
        for slot in plan.email_slots:
            print(f" Slot {slot.slot_number}: {slot.transformation_description}")

if __name__ == "__main__":
    inspect_latest_plan()
