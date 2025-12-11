"""
Utility script to export EXISTING approved campaign plans to Google Sheets.
Run this if you have plans created before the export feature was enabled.
"""

import os
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager
from email_orchestrator.tools.google_sheets_export import export_campaign_to_sheets

def export_all_approved_plans():
    print("=" * 60)
    print("EXPORTING EXISTING PLANS TO GOOGLE SHEETS")
    print("=" * 60)
    
    manager = CampaignPlanManager()
    
    # Get all plans
    all_plans = manager.list_all_plans()
    
    if not all_plans:
        print("No plans found.")
        return

    print(f"Found {len(all_plans)} plans total.")
    
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y")
    share_with = os.getenv('GOOGLE_DOCS_SHARE_EMAIL')
    
    exported_count = 0
    
    for plan_meta in all_plans:
        # Load full plan
        plan = manager.get_plan(plan_meta.campaign_id)
        
        if not plan:
            continue
            
        print(f"\nProcessing: {plan.campaign_name} ({plan.campaign_id})")
        print(f"Status: {plan.status}")
        
        if plan.status == "approved":
            try:
                print("  > Exporting...")
                result = export_campaign_to_sheets(plan, folder_id, share_with)
                print(f"  ✓ Exported: {result['spreadsheet_url']}")
                exported_count += 1
            except Exception as e:
                print(f"  ✗ Failed to export: {e}")
        else:
            print("  > Skipping (not approved)")
            
    print("\n" + "=" * 60)
    print(f"DONE. Exported {exported_count} plans.")

if __name__ == "__main__":
    export_all_approved_plans()
