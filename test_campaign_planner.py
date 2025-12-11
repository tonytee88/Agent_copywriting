"""
Test script for Campaign Planner feature.
Tests the end-to-end campaign planning workflow.
"""

import asyncio
from email_orchestrator.tools.campaign_tools import plan_campaign

async def test_campaign_planner():
    """Test campaign planning for PopBrush."""
    
    print("=" * 60)
    print("TESTING CAMPAIGN PLANNER")
    print("=" * 60)
    
    # Test 1: Plan a 10-email campaign over 1 month
    print("\n[Test 1] Planning 10-email campaign for PopBrush...")
    
    result = await plan_campaign(
        brand_name="PopBrush",
        campaign_goal="Build awareness about hair health, then drive Black Friday sales",
        total_emails=7,
        duration="next month",
        promotional_ratio=0.4  # 40% promotional, 60% educational
    )
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(result)
    
    # Test 2: Try with too many emails (should warn)
    print("\n\n[Test 2] Testing frequency validation (12 emails in 1 month)...")
    
    result2 = await plan_campaign(
        brand_name="PopBrush",
        campaign_goal="Aggressive promotional push",
        total_emails=12,
        duration="1 month",
        promotional_ratio=0.6
    )
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(result2)

if __name__ == "__main__":
    asyncio.run(test_campaign_planner())
