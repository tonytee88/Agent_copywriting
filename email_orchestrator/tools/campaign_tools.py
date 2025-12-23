import json
from datetime import datetime
from typing import Optional, Dict

from email_orchestrator.schemas import (
    BrandBio, CampaignPlan, CampaignRequest, EmailBlueprint, EmailDraft, 
    CampaignLogEntry, CampaignPlanVerification, EmailVerification,
    BlockingIssue, OptimizationOption, TopImprovement
)
from email_orchestrator.tools.brand_scraper_tool import analyze_brand
from email_orchestrator.subagents.campaign_planner_agent import campaign_planner_agent, revise_campaign_plan
from email_orchestrator.subagents.campaign_plan_verifier_agent import campaign_plan_verifier_agent
from email_orchestrator.subagents.strategist_agent import strategist_agent
from email_orchestrator.subagents.drafter_agent import drafter_agent
from email_orchestrator.subagents.verifier_agent import verifier_agent
from email_orchestrator.tools.deterministic_verifier import DeterministicVerifier

from email_orchestrator.tools.knowledge_reader import KnowledgeReader
from email_orchestrator.tools.history_manager import HistoryManager
from email_orchestrator.tools.campaign_plan_manager import CampaignPlanManager
from email_orchestrator.tools.google_docs_export import export_email_to_google_docs
from email_orchestrator.tools.token_tracker import get_token_tracker

# Initialize Tools
knowledge = KnowledgeReader()
history_manager = HistoryManager()
campaign_manager = CampaignPlanManager()
det_verifier = DeterministicVerifier()

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
    max_retries = 2 # Limit to 1 Revision Pass
    is_approved = False
    
    for attempt in range(max_retries):
        print(f"\n[Plan Verification] Attempt {attempt+1}/{max_retries}")
        
        # --- LAYER 1: Deterministic QA ---
        # Fetch history for duplication checks
        # Critical: Use brand_id for isolation if available.
        # HistoryManager.get_recent_campaigns prioritizes brand_id lookup.
        
        history_identifier = brand_bio.brand_id if getattr(brand_bio, 'brand_id', None) else brand_name
        
        # NOTE: If history_identifier is a name (legacy), duplicate names across brands could be an issue.
        # But for now, we trust brand_id is set for new brands.
        
        past_campaigns = history_manager.get_recent_campaigns(history_identifier, limit=10) # Get enough history
        
        print(f"[Plan QA] Loaded {len(past_campaigns)} history items for brand '{history_identifier}'")
        
        # Convert Pydantic to dict for verifier
        past_campaigns_dicts = [entry.model_dump() for entry in past_campaigns]

        det_issues = det_verifier.verify_plan(plan, past_campaigns_dicts)
        
        if det_issues:
            print(f"[Plan Verification] Layer 1 (Deterministic) Failed. Issues: {len(det_issues)}")
            # Skip Layer 2, enforce fixes immediately
            
            # Map deterministic issues to TopImprovement for consistency
            top_improvements = [
                TopImprovement(
                    rank=i+1,
                    category="structure_purpose_fit",
                    problem=issue.problem,
                    why_it_matters=issue.rationale,
                    options={"A": "Fix the structure ID or repetition issue manually."}
                ) for i, issue in enumerate(det_issues)
            ]
            
            verification = CampaignPlanVerification(
                approved=False,
                final_verdict="Plan rejected due to strict validation rules (Repetition or Invalid IDs).",
                top_improvements=top_improvements,
                issues=det_issues # Kept for internal record
            )
        else:
            # --- LAYER 2: LLM QA ---
            print("[Plan Verification] Layer 1 Passed. Proceeding to LLM QA...")
            verification = await campaign_plan_verifier_agent(plan, brand_bio)
        
        # Proceed with existing logic using 'verification' object
        if verification.approved:
            print(f"[Plan Verification] SUCCESS! Initial plan approved.")
            plan.status = "approved"
            is_approved = True
            break
        else:
            print(f"[Plan Verification] REJECTED. Verdict: {verification.final_verdict}")
            
            # Call Repair Logic
            if attempt < max_retries - 1:
                print("[Plan Verification] Requesting ONE-TIME Revision based on QA feedback...")
                plan = await revise_campaign_plan(plan, verification, brand_bio)
                plan.status = "approved" # Forced approved as per user request
                print("[Plan Verification] Revised plan created and marked as approved.")
                break
            else:
                # Should not be reachable with max_retries=2 and the break above, but kept for safety
                print("[Plan Verification] Max retries reached or process skipped.")
                break
    
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
            
            # --- LAYER 1: Deterministic QA ---
            det_issues = det_verifier.verify_draft(draft)
            
            if det_issues:
                print(f"[Email #{slot.slot_number}] Layer 1 (Deterministic) Failed. Issues: {len(det_issues)}")
                # Construct detailed feedback so the agent knows what to fix
                issues_summary = "\n".join([f"- {i.field}: {i.problem} ({i.rationale})" for i in det_issues])
                feedback_msg = f"Strict Rules Violation. You must fix these errors:\n{issues_summary}"
                
                # Construct a pseudo-verification result to trigger revision
                verification = EmailVerification(
                    approved=False,
                    score=0,
                    issues=det_issues,
                    feedback_for_drafter=feedback_msg,
                    replacement_options=None # No replacements for formatting
                )
            else:
                # --- LAYER 2: LLM QA ---
                print(f"[Email #{slot.slot_number}] Layer 1 Passed. Proceeding to LLM QA...")
                verification = await verifier_agent(draft, blueprint, plan.brand_name)
            
            # D. Verify (Common handling)
            # verification = await verifier_agent(draft, blueprint, plan.brand_name) <-- Replaced by above logic
            
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
            transformation_description=blueprint.transformation_description,
            transformation_id=blueprint.transformation_id,
            structure_id=blueprint.structure_id,
            angle_description=blueprint.angle_description,
            angle_id=blueprint.angle_id,
            cta_description=blueprint.cta_description,
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
