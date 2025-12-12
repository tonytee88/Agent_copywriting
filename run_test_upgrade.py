import asyncio
import os
import sys

# Ensure module path
sys.path.append(os.getcwd())

from email_orchestrator.tools.campaign_tools import plan_campaign, generate_email_campaign
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager

async def main():
    print("=== STEP 1: PLANNING CAMPAIGN ===")
    plan_output = await plan_campaign(
        brand_name="PopBrush",
        campaign_goal="Launch new Detangling Spray with 20% off",
        duration="1 week",
        total_emails=2,
        promotional_ratio=0.5
    )
    print(f"Plan Output: {plan_output}")
    
    # Extract ID
    # Output format: "Campaign Plan Created! ID: {plan.campaign_id}. Status: {plan.status}"
    if "ID: " in plan_output:
        campaign_id = plan_output.split("ID: ")[1].split(".")[0]
        print(f"Captured ID: {campaign_id}")
        
        print("\n=== STEP 2: GENERATING EMAILS ===")
        gen_output = await generate_email_campaign(campaign_id)
        print(f"Generate Output: {gen_output}")
    else:
        print("Could not extract campaign ID to proceed.")

if __name__ == "__main__":
    asyncio.run(main())
