"""
Test script for end-to-end campaign planning and email generation workflow.
"""

import asyncio
from email_orchestrator.tools.campaign_tools import plan_campaign, generate_email_campaign

async def test_campaign_workflow():
    """Test the complete campaign planning and email generation workflow."""
    
    print("=" * 80)
    print("TESTING CAMPAIGN-DRIVEN EMAIL GENERATION WORKFLOW")
    print("=" * 80)
    
    # Step 1: Plan a campaign
    print("\n[STEP 1] Planning 7-email campaign for PopBrush...")
    print("-" * 80)
    
    plan_result = await plan_campaign(
        brand_name="PopBrush",
        campaign_goal="Build awareness about hair health, then drive Black Friday sales",
        total_emails=7,
        duration="next month",
        promotional_ratio=0.4
    )
    
    print(plan_result)
    
    # Extract campaign ID from result
    import json
    if "Campaign Plan Approved" in plan_result:
        # Parse the campaign ID from the result
        lines = plan_result.split("\n")
        campaign_id = None
        for line in lines:
            if line.startswith("ID:"):
                campaign_id = line.split("ID:")[1].strip()
                break
        
        if campaign_id:
            print(f"\n✓ Campaign plan created with ID: {campaign_id}")
            
            # Step 2: Generate first email using the campaign plan
            print("\n" + "=" * 80)
            print("[STEP 2] Generating Email #1 using campaign plan...")
            print("-" * 80)
            
            email_result = await generate_email_campaign(
                brand_name="PopBrush",
                offer="See campaign plan",  # Will be overridden by slot
                angle="See campaign plan",  # Will be overridden by slot
                campaign_plan_id=campaign_id,
                slot_number=1
            )
            
            print("\n" + "=" * 80)
            print("EMAIL #1 RESULT:")
            print("=" * 80)
            print(email_result[:1000] + "..." if len(email_result) > 1000 else email_result)
            
            print("\n" + "=" * 80)
            print("✓ WORKFLOW TEST COMPLETE!")
            print("=" * 80)
        else:
            print("\n✗ Could not extract campaign ID from result")
    else:
        print("\n✗ Campaign planning failed")

if __name__ == "__main__":
    asyncio.run(test_campaign_workflow())
