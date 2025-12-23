import asyncio
import json
import os
from datetime import datetime
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager
from email_orchestrator.tools.campaign_tools import generate_email_campaign
from email_orchestrator.tools.token_tracker import get_token_tracker

async def test_draft_qa():
    print("=== DRAFT QA INTEGRATION TEST ===")
    
    manager = CampaignPlanManager()
    plans = manager.list_all_plans()
    
    # Filter for approved plans
    approved_plans = [p for p in plans if p.status == "approved"]
    
    if not approved_plans:
        print("❌ Error: No approved plans found in history. Please run a campaign plan first.")
        return

    # Pick the latest approved plan
    plan = sorted(approved_plans, key=lambda x: x.created_at, reverse=True)[0]
    print(f"✅ Found Approved Plan: {plan.campaign_name} ({plan.campaign_id})")
    print(f"Brand: {plan.brand_name}")
    print(f"Goal: {plan.campaign_goal}")
    print(f"Total Emails: {plan.total_emails}")
    
    # Run the email generation loop (this will trigger the Draft QA logic)
    print("\n--- Starting Draft Execution Phase ---")
    results = await generate_email_campaign(plan.campaign_id)
    
    print("\n=== TEST COMPLETE ===")
    print(f"Results: {results}")
    
    tracker = get_token_tracker()
    print(tracker.get_summary())

if __name__ == "__main__":
    asyncio.run(test_draft_qa())
