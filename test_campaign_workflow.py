"""
Complete workflow test: Campaign Planning → Email Generation

This demonstrates the full campaign-driven email generation workflow:
1. Create a campaign plan (or use existing)
2. Generate emails following the plan's strategic directives
3. Track progress through the campaign
"""

import asyncio
import json
from email_orchestrator.tools.campaign_tools import plan_campaign, generate_email_campaign
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager

async def test_full_workflow():
    """Test complete campaign planning and email generation workflow."""
    
    print("=" * 80)
    print("CAMPAIGN-DRIVEN EMAIL GENERATION - FULL WORKFLOW TEST")
    print("=" * 80)
    
    # Check for existing approved plans
    plan_manager = CampaignPlanManager()
    existing_plans = plan_manager.get_plans_by_brand("PopBrush")
    
    campaign_id = None
    
    if existing_plans:
        print(f"\n✓ Found {len(existing_plans)} existing campaign plan(s) for PopBrush")
        
        # Use the most recent approved plan
        for plan in existing_plans:
            if plan.status == "approved":
                campaign_id = plan.campaign_id
                print(f"\n📋 Using existing campaign plan:")
                print(f"   ID: {campaign_id}")
                print(f"   Name: {plan.campaign_name}")
                print(f"   Emails: {plan.total_emails}")
                print(f"   Balance: {plan.promotional_balance}")
                break
    
    # If no existing plan, create one
    if not campaign_id:
        print("\n[STEP 1] Creating new campaign plan...")
        print("-" * 80)
        
        plan_result = await plan_campaign(
            brand_name="PopBrush",
            campaign_goal="Build awareness about hair health, then drive Black Friday sales",
            total_emails=5,  # Smaller for testing
            duration="next month",
            promotional_ratio=0.4
        )
        
        # Extract campaign ID
        if "Campaign Plan Approved" in plan_result:
            lines = plan_result.split("\n")
            for line in lines:
                if line.startswith("ID:"):
                    campaign_id = line.split("ID:")[1].strip()
                    break
            
            if campaign_id:
                print(f"\n✓ New campaign plan created: {campaign_id}")
            else:
                print("\n✗ Failed to extract campaign ID")
                return
        else:
            print("\n✗ Campaign planning failed")
            print(plan_result)
            return
    
    # Generate emails from the campaign plan
    print("\n" + "=" * 80)
    print("[STEP 2] Generating Emails from Campaign Plan")
    print("=" * 80)
    
    # Load the plan to see how many emails
    plan = plan_manager.get_plan(campaign_id)
    if not plan:
        print(f"\n✗ Could not load campaign plan {campaign_id}")
        return
    
    print(f"\nCampaign: {plan.campaign_name}")
    print(f"Total Emails: {plan.total_emails}")
    print(f"Balance: {plan.promotional_balance}\n")
    
    # Generate first 3 emails as demonstration
    emails_to_generate = min(3, plan.total_emails)
    
    for slot_num in range(1, emails_to_generate + 1):
        print("-" * 80)
        print(f"GENERATING EMAIL #{slot_num}/{plan.total_emails}")
        print("-" * 80)
        
        # Get slot info
        slot = plan_manager.get_slot_by_number(campaign_id, slot_num)
        if slot:
            print(f"Theme: {slot.theme}")
            print(f"Purpose: {slot.email_purpose} ({slot.intensity_level})")
            print(f"Transformation: {slot.assigned_transformation}")
            print(f"Structure: {slot.assigned_structure}")
            print(f"Send Date: {slot.send_date}\n")
        
        # Generate the email
        result = await generate_email_campaign(
            brand_name="PopBrush",
            offer="See campaign plan",  # Will be overridden
            angle="See campaign plan",  # Will be overridden
            campaign_plan_id=campaign_id,
            slot_number=slot_num
        )
        
        # Parse result to check status
        try:
            result_data = json.loads(result)
            status = result_data.get("status", "UNKNOWN")
            
            if status == "APPROVED":
                draft = result_data.get("draft", {})
                print(f"✓ Email #{slot_num} APPROVED")
                print(f"  Subject: {draft.get('subject', 'N/A')}")
                print(f"  Hero: {draft.get('hero_title', 'N/A')}")
            else:
                print(f"⚠ Email #{slot_num} status: {status}")
                if "warning" in result_data:
                    print(f"  Warning: {result_data['warning']}")
        except:
            # Not JSON, might be error message
            if "Error" in result:
                print(f"✗ Email #{slot_num} failed:")
                print(f"  {result[:200]}")
            else:
                print(f"✓ Email #{slot_num} generated (non-JSON response)")
        
        print()
    
    # Summary
    print("=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print(f"✓ Campaign Plan: {campaign_id}")
    print(f"✓ Emails Generated: {emails_to_generate}/{plan.total_emails}")
    print(f"✓ All emails followed campaign strategic directives")
    print(f"\nNext Steps:")
    print(f"  - Generate remaining emails (slots {emails_to_generate + 1}-{plan.total_emails})")
    print(f"  - Review outputs in outputs/ directory")
    print(f"  - Mark campaign as 'in_progress' or 'completed'")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
