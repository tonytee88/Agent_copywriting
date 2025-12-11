"""
Test Google Sheets export functionality.
"""

import asyncio
from email_orchestrator.tools.google_sheets_export import export_campaign_to_sheets
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager

def test_google_sheets_export():
    """Test exporting a campaign plan to Google Sheets."""
    
    print("=" * 80)
    print("TESTING GOOGLE SHEETS EXPORT")
    print("=" * 80)
    
    # 1. Load an existing campaign plan
    plan_manager = CampaignPlanManager()
    plans = plan_manager.get_plans_by_brand("PopBrush")
    
    if not plans:
        print("✗ No campaign plans found to export. Create one first.")
        return
    
    # Use the most recent approved plan
    plan = plans[0]
    print(f"\nFound plan: {plan.campaign_name} ({plan.campaign_id})")
    
    # 2. Export to Sheets
    print("\n[Exporting to Google Sheets...]")
    
    import os
    folder_id = "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y"
    share_with = os.getenv('GOOGLE_DOCS_SHARE_EMAIL')
    
    try:
        result = export_campaign_to_sheets(
            campaign_plan=plan,
            folder_id=folder_id,
            share_with=share_with
        )
        
        print("\n" + "=" * 80)
        print("✓ EXPORT SUCCESSFUL!")
        print("=" * 80)
        print(f"Spreadsheet Title: {result['title']}")
        print(f"Spreadsheet URL: {result['spreadsheet_url']}")
        print("\nOpen the link above to view your campaign plan!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Export failed: {e}")

if __name__ == "__main__":
    test_google_sheets_export()
