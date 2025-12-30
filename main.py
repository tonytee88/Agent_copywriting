import argparse
import asyncio
import sys
from typing import List, Optional
from pathlib import Path

from email_orchestrator.tools.campaign_tools import plan_campaign, generate_email_campaign
# We will import these later as we implement Phase 2
# from email_orchestrator.tools.google_sheets_importer import import_plan_from_sheet

from email_orchestrator.tools.request_parser import parse_campaign_request

async def run_plan(args):
    """Executes the PLANNING phase."""
    print("=== CAMPAIGN ORCHESTRATOR: PHASE 1 (PLANNING) ===")
    
    # 1. Parse Request
    prompt_is_list = isinstance(args.prompt, list)
    user_prompt = " ".join(args.prompt) if prompt_is_list else args.prompt
    
    print(f"[Input] '{user_prompt}'")
    print("[Orchestrator] Parsing request...")
    
    req = await parse_campaign_request(user_prompt)
    print(f"[Parser] Detected: Brand='{req.brand_name}', Goal='{req.campaign_goal}', Count={req.total_emails}")
    if req.notes:
        print(f"[Parser] Notes: {req.notes}")

    try:
        result = await plan_campaign(
            brand_name=req.brand_name,
            campaign_goal=req.campaign_goal,
            duration=req.duration,
            total_emails=req.total_emails,
            promotional_ratio=req.promotional_ratio,
            notes=req.notes
        )
        print("\n" + "="*50)
        print(result)
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"Error during planning: {e}")
        sys.exit(1)

from email_orchestrator.tools.google_sheets_importer import import_plan_from_sheet
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager
from email_orchestrator.tools.campaign_compiler import compile_campaign_doc
from datetime import datetime

async def run_execute(args):
    """Executes the EXECUTION phase (Phase 2)."""
    print("=== CAMPAIGN ORCHESTRATOR: PHASE 2 (EXECUTION) ===")
    
    manager = CampaignPlanManager()
    plan = manager.get_plan(args.campaign_id)
    
    if not plan:
        print(f"Error: Campaign Plan {args.campaign_id} not found.")
        sys.exit(1)
        
    # 1. AUTO-SYNC
    if plan.sheet_url:
        print(f"\n[Sync] Found linked Google Sheet: {plan.sheet_url}")
        print("[Sync] Importing user edits...")
        try:
            imported_data = import_plan_from_sheet(plan.sheet_url)
            # Ensure we are updating the correct campaign
            if imported_data.get('campaign_id') and imported_data['campaign_id'] != args.campaign_id:
                print(f"[Warning] Mismatch ID in sheet ({imported_data['campaign_id']}) vs argument ({args.campaign_id}). Proceeding with argument ID.")
                imported_data['campaign_id'] = args.campaign_id
                
            manager.update_plan_from_import(imported_data)
        except Exception as e:
            print(f"[Sync] Failed to sync from sheet: {e}")
            print("[Sync] Proceeding with existing internal plan...")
    else:
        print("[Sync] No linked Google Sheet found (created before Phase 1 update?). Skipping sync.")

    # 2. GENERATE
    print(f"\n[Execution] Generating emails for Campaign: {args.campaign_id}")
    
    # We call generate_email_campaign (which now returns JSON with content)
    import json
    json_result = await generate_email_campaign(
        campaign_id=args.campaign_id,
        # TODO: Add logic for specific slots if needed. Current implementation runs all or one. 
        # Support for list of slots requires refactoring generate loop in tools.
        # For Minimum Viable Phase 2: We iterate in CLI or just run all.
        # Let's run all for now as 'slots' argument support in tools is 'Optional[int]' (single).
        # Improving this is a "Refactoring" task for later.
    )
    
    try:
        drafts = json.loads(json_result)
        
        # SAVE DRAFTS Locally (Safety)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        drafts_dir = Path(f"outputs/drafts/{args.campaign_id}")
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft_file = drafts_dir / f"drafts_{timestamp}.json"
        draft_file.write_text(json.dumps(drafts, indent=2))
        print(f"[Safety] Drafts saved to {draft_file}")
        
        # ROTATION: Keep last 5
        all_files = sorted(drafts_dir.glob("drafts_*.json"), key=lambda f: f.stat().st_mtime)
        if len(all_files) > 5:
            for old_file in all_files[:-5]:
                try:
                    old_file.unlink()
                    print(f"[Cleanup] Deleted old draft file: {old_file.name}")
                except Exception as e:
                    print(f"[Cleanup] Failed to delete {old_file.name}: {e}")
        
        # Filter if slots argument was provided (post-generation filter if we can't pre-filter)
        # Note: This is inefficient but functional for now.
        if args.slots:
            target_slots = [int(s.strip()) for s in args.slots.split(',')]
            drafts = [d for d in drafts if d.get('slot_number') in target_slots]
            
        if not drafts:
            print("No drafts generated.")
            return

        # 3. COMPILE
        print("\n[Compilation] Compiling consolidated document...")
        
        # Get target month from plan
        # Reuse logic or get from duration/start_date
        target_month = "Campaign"
        try:
            from email_orchestrator.tools.google_sheets_export import GoogleSheetsExporter
            # Hack: Instantiate to use helper or just duplicate logic
            # Simpler: Try to parse 'duration'
            dur = plan.duration.lower()
            for m in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]:
                if m in dur:
                    target_month = m.capitalize()
                    break
        except: 
            pass
            
        doc_url = compile_campaign_doc(
            brand_name=plan.brand_name,
            campaign_id=plan.campaign_id,
            target_month=target_month,
            drafts=drafts,
            folder_id=None # Optionally we could lookup folder from plan meta if we stored it
        )
        
        print("\n" + "="*50)
        print(f"PHASE 2 COMPLETE")
        print(f"Compiled Drafts: {doc_url}")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"[Execution] Error processing results: {e}")


def main():
    parser = argparse.ArgumentParser(description="AI Email Campaign Orchestrator")
    subparsers = parser.add_subparsers(dest='command', help='Phase to run')
    
    # COMMAND: PLAN
    parser_plan = subparsers.add_parser('plan', help='Phase 1: Generate & Export Plan')
    parser_plan.add_argument('prompt', nargs='+', help='Natural language request (e.g. "Plan 5 emails for PopBrush Black Friday")')
    # Legacy args removed in favor of NL interface
    # parser_plan.add_argument('--brand', type=str, required=True, help='Brand Name') ...
    
    # COMMAND: EXECUTE
    parser_execute = subparsers.add_parser('execute', help='Phase 2: Sync & Generate Emails')
    parser_execute.add_argument('campaign_id', type=str, help='Campaign ID to execute')
    parser_execute.add_argument('--slots', type=str, help='Comma-separated slot numbers (e.g. "1,3")')
    parser_execute.add_argument('--instructions', type=str, help='Natural language instructions for revisions')

    args = parser.parse_args()
    
    if args.command == 'plan':
        asyncio.run(run_plan(args))
    elif args.command == 'execute':
        asyncio.run(run_execute(args))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
