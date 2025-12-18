import json
from datetime import datetime
from typing import Optional, Dict

from email_orchestrator.schemas import (
    BrandBio, CampaignPlan, CampaignRequest, EmailBlueprint, EmailDraft, 
    CampaignLogEntry, CampaignPlanVerification, EmailVerification
)
from email_orchestrator.tools.brand_scraper_tool import analyze_brand
from email_orchestrator.subagents.campaign_planner_agent import campaign_planner_agent, revise_campaign_plan
from email_orchestrator.subagents.campaign_plan_verifier_agent import campaign_plan_verifier_agent
from email_orchestrator.subagents.strategist_agent import strategist_agent
from email_orchestrator.subagents.drafter_agent import drafter_agent
from email_orchestrator.subagents.verifier_agent import verifier_agent

from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.tools.history_manager import HistoryManager
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager
from email_orchestrator.tools.google_docs_export import export_email_to_google_docs
from email_orchestrator.tools.token_tracker import get_token_tracker

# Initialize Tools
knowledge = KnowledgeReader()
history_manager = HistoryManager()
campaign_manager = CampaignPlanManager()

# Default folder from User Feedback
POPBRUSH_FOLDER_ID = "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y"

async def plan_campaign(
    brand_name: str,
    campaign_goal: str,
    duration: str,
    total_emails: int,
    promotional_ratio: float = 0.4,
    drive_folder_id: Optional[str] = POPBRUSH_FOLDER_ID
) -> str:
    """
    Orchestrates the Campaign Planning Phase.
    """
    print(f"\n--- STARTING CAMPAIGN PLANNING FOR {brand_name} ---")
    tracker = get_token_tracker()
    tracker.reset()
    
    # 1. Analyze Brand (or load cached)
    analysis_result = await analyze_brand(brand_name)
    brand_bio = BrandBio(**json.loads(analysis_result))
    
    # 2. Generate Initial Plan
    plan = await campaign_planner_agent(
        brand_name=brand_name,
        campaign_goal=campaign_goal,
        total_emails=total_emails,
        duration=duration,
        brand_bio=brand_bio,
        promotional_ratio=promotional_ratio
    )
    
    # Ensure brand_id is set (Critical for Multi-Brand Isolation)
    if not plan.brand_id and brand_bio.brand_id:
        plan.brand_id = brand_bio.brand_id
    
    # 3. Verification Loop (Judge + Repair)
    max_retries = 3
    is_approved = False
    
    for attempt in range(max_retries):
        print(f"\n[Plan Verification] Attempt {attempt+1}/{max_retries}")
        verification = await campaign_plan_verifier_agent(plan, brand_bio)
        
        if verification.approved:
            print(f"[Plan Verification] SUCCESS! Score: {verification.score}")
            plan.status = "approved"
            is_approved = True
            break
        else:
            print(f"[Plan Verification] REJECTED. Score: {verification.score}")
            print(f"Issues: {len(verification.issues)}")
            
            # Call Repair Logic
            if attempt < max_retries - 1:
                print("[Plan Verification] Requesting Revision...")
                plan = await revise_campaign_plan(plan, verification, brand_bio)
            else:
                print("[Plan Verification] Max retries reached. Proceeding with best effort (marked as draft).")
    
    # 4. Save Plan
    # Ensure created_at is current to prevent auto-cleanup deletion of "old" hallucinated dates
    plan.created_at = datetime.utcnow().isoformat() + "Z"

    # 4. Save Plan
    campaign_manager.save_plan(plan)
    
    # 5. Export Plan Summary to Google Sheets (Updated Feature)
    try:
        from email_orchestrator.tools.google_sheets_export import export_plan_to_google_sheets
        
        # We pass the plan object converted to dict, as the tool expects a dict-like structure or we adjust it.
        # The Pydantic model .dict() is suitable.
        sheet_result = export_plan_to_google_sheets(
            plan_data=plan.dict(),
            folder_id=drive_folder_id
        )
        print(f"[Export] Plan exported to: {sheet_result['spreadsheet_url']} (Folder: {drive_folder_id})")
            
    except Exception as e:
        print(f"[Export] Plan Export Failed: {e}")
    
    # 6. Report Tokens
    print(tracker.get_summary())
    
    return f"Campaign Plan Created! ID: {plan.campaign_id}. Status: {plan.status}"

async def generate_email_campaign(
    campaign_id: str,
    drive_folder_id: Optional[str] = POPBRUSH_FOLDER_ID
) -> str:
    """
    Orchestrates the Execution Phase (Writing Emails).
    """
    tracker = get_token_tracker()
    tracker.reset()
    
    # 1. Load Plan
    plan = campaign_manager.get_plan(campaign_id)
    if not plan:
        return f"Error: Campaign {campaign_id} not found."
    
    # Load Brand Bio
    analysis_result = await analyze_brand(plan.brand_name)
    brand_bio = BrandBio(**json.loads(analysis_result))
    
    print(f"\n--- EXECUTING CAMPAIGN: {plan.campaign_name} ({len(plan.email_slots)} emails) ---")
    
    results = []
    
    # 2. Iterate Slots
    for slot in plan.email_slots:
        print(f"\n>>> PROCESSING EMAIL #{slot.slot_number} ({slot.email_purpose}) <<<")
        
        # A. Strategist (Create Blueprint using Slot Directives)
        request = CampaignRequest(
            brand_name=plan.brand_name,
            offer=slot.offer_details or "General Brand Awareness",
            theme_angle=slot.theme,
            target_audience=brand_bio.target_audience
        )
        
        # Pass folder selection context? Not needed for Strategist.
        blueprint = await strategist_agent(request, brand_bio, campaign_context=slot)
        
        # B. Drafter Wrapper Loop
        max_draft_retries = 3
        final_draft = None
        revision_feedback = None
        
        for attempt in range(max_draft_retries):
            # C. Drafter
            draft = await drafter_agent(blueprint, brand_bio, revision_feedback)
            
            # D. Verify
            verification = await verifier_agent(draft, blueprint, plan.brand_name)
            
            if verification.approved:
                print(f"[Email #{slot.slot_number}] APPROVED! Score: {verification.score}")
                final_draft = draft
                break
            else:
                print(f"[Email #{slot.slot_number}] QA DETECTED ISSUES. OPTIMIZING DRAFT (Attempt {attempt+1}). Issues: {len(verification.issues)}")
                
                if attempt < max_draft_retries - 1:
                    feedback_lines = []
                    feedback_lines.append(f"FEEDBACK: {verification.feedback_for_drafter}")
                    if verification.replacement_options:
                        opts = verification.replacement_options
                        if opts.hero_title_alternatives:
                            feedback_lines.append(f"SUGGESTED HERO TITLES: {opts.hero_title_alternatives}")
                        if opts.subject_alternatives:
                             feedback_lines.append(f"SUGGESTED SUBJECTS: {opts.subject_alternatives}")
                        if opts.descriptive_block_rewrite_hint:
                             feedback_lines.append(f"REWRITE HINT: {opts.descriptive_block_rewrite_hint}")
                    
                    revision_feedback = "\n".join(feedback_lines)
                else:
                    print(f"[Email #{slot.slot_number}] Max retries reached. Using last draft.")
                    final_draft = draft
        
        # E. Save Metadata (Log History)
        log_entry = CampaignLogEntry(
            campaign_id=campaign_id,
            timestamp=datetime.now().isoformat(),
            brand_id=plan.brand_id, # Added for multi-brand isolation
            brand_name=plan.brand_name,
            transformation_id=blueprint.transformation_id,
            structure_id=blueprint.structure_id,
            angle_id=blueprint.angle_id,
            cta_style_id=blueprint.cta_style_id,
            offer_placement_used=blueprint.offer_placement,
            blueprint=blueprint,
            final_draft=final_draft
        )
        history_manager.log_campaign(log_entry)
        
        results.append({
            "slot": slot.slot_number,
            "subject": final_draft.subject,
            "status": "completed"
        })
        
        # F. Export to Google Docs
        try:
            doc_result = export_email_to_google_docs(
                email_draft=final_draft.dict(),
                brand_name=plan.brand_name,
                folder_id=drive_folder_id, # Use the passed folder ID
                structure_name=blueprint.structure_id,
                language=plan.language
            )
            print(f"[Export] Email #{slot.slot_number} exported to: {doc_result['document_url']} (Folder: {drive_folder_id})")
        except Exception as e:
            print(f"[Export] Failed: {e}")

    print("\n--- CAMPAIGN EXECUTION FINISHED ---")
    print(tracker.get_summary())
    
    return json.dumps(results, indent=2)
