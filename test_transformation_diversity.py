
import asyncio
import json
from email_orchestrator.tools.campaign_tools import plan_campaign

async def test_transformation_diversity():
    print("=== Testing Transformation Diversity in Campaign Planning ===")
    
    brand_name = "PopBrush"
    campaign_goal = "Promote our new eco-friendly silicon toothbrush"
    duration = "2 weeks"
    total_emails = 5
    
    print(f"Generating a {total_emails}-email campaign for {brand_name}...")
    
    # Run the planning process
    result = await plan_campaign(
        brand_name=brand_name,
        campaign_goal=campaign_goal,
        duration=duration,
        total_emails=total_emails
    )
    
    # plan_campaign returns a string summary usually, but we want to see the saved plan
    from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager
    manager = CampaignPlanManager()
    plans = manager.list_all_plans()
    # plans is a list of CampaignPlan objects
    latest_plan = sorted(plans, key=lambda x: x.campaign_id)[-1]
    
    print(f"\nPlan: {latest_plan.campaign_name}")
    print("Email Transformations:")
    for slot in latest_plan.email_slots:
        print(f" Slot {slot.slot_number}: {slot.transformation_description}")

if __name__ == "__main__":
    asyncio.run(test_transformation_diversity())
