import json
from datetime import datetime
from typing import Optional, Dict, List

from email_orchestrator.schemas import (
    BrandBio, CampaignPlan, CampaignRequest, EmailBlueprint, EmailDraft, 
    CampaignLogEntry, CampaignPlanVerification, EmailVerification,
    BlockingIssue, OptimizationOption, TopImprovement
)
from email_orchestrator.tools.brand_scraper_tool import analyze_brand
# from email_orchestrator.subagents.campaign_planner_agent import campaign_planner_agent, revise_campaign_plan
from email_orchestrator.subagents.campaign_plan_verifier_agent import campaign_plan_verifier_agent
from email_orchestrator.subagents.strategist_agent import strategist_agent
from email_orchestrator.subagents.drafter_agent import drafter_agent
from email_orchestrator.subagents.stylist_agent import StylistAgent
from email_orchestrator.tools.campaign_planner_tools import optimize_plan_transformations
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
    languages: Optional[list] = ["FR"],
    notes: Optional[str] = None,
    start_date: Optional[str] = None,
    excluded_days: List[str] = [],
    raw_user_input: Optional[str] = None,
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
    # Instantiate Session for this run
    from email_orchestrator.subagents.campaign_planner_agent import CampaignPlanningSession
    planner_session = CampaignPlanningSession(brand_name)
    
    plan = await planner_session.generate_initial_plan(
        campaign_goal=campaign_goal,
        total_emails=total_emails,
        duration=duration,
        brand_bio=brand_bio,
        start_date=start_date,
        excluded_days=excluded_days,
        promotional_ratio=promotional_ratio,
        languages=languages,
        notes=notes,
        raw_user_input=raw_user_input
    )
    
    # 2. [NEW] Strategic Optimization Layer: Refine Transformations
    plan = await optimize_plan_transformations(plan, brand_bio)
    
    # Ensure brand_id is set (Critical for Multi-Brand Isolation)
    if not plan.brand_id and brand_bio.brand_id:
        plan.brand_id = brand_bio.brand_id
    
    # Save folder ID to plan for Phase 2 persistence
    plan.drive_folder_id = drive_folder_id
    plan.languages = languages # Ensure persistent languages
    
    # 3. Verification Loop (Judge + Repair)
    max_retries = 2 # Limit to 1 Revision Pass
    is_approved = False
    
    for attempt in range(max_retries):
        print(f"\n[Plan Verification] Attempt {attempt+1}/{max_retries}")
        
        # --- LAYER 1: Deterministic QA ---
        history_identifier = brand_bio.brand_id if getattr(brand_bio, 'brand_id', None) else brand_name
        past_campaigns = history_manager.get_recent_campaigns(history_identifier, limit=10) # Get enough history
        print(f"[Plan QA] Loaded {len(past_campaigns)} history items for brand '{history_identifier}'")
        past_campaigns_dicts = [entry.model_dump() for entry in past_campaigns]

        det_issues = det_verifier.verify_plan(plan, past_campaigns_dicts)
        
        if det_issues:
            print(f"[Plan Verification] Layer 1 (Deterministic) Failed. Issues: {len(det_issues)}")
            # Skip Layer 2, enforce fixes immediately
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
                print("[Plan Verification] Requesting ONE-TIME Revision based on QA feedback via SESSION...")
                # Use session for revision to maintain context
                plan = await planner_session.process_qa_feedback(plan, verification)
                plan.languages = languages # Re-assert languages after revision
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
    sheet_url = "N/A"
    try:
        from email_orchestrator.tools.google_sheets_export import export_plan_to_google_sheets
        
        # We pass the plan object converted to dict, as the tool expects a dict-like structure or we adjust it.
        # The Pydantic model .dict() is suitable.
        sheet_result = export_plan_to_google_sheets(
            plan_data=plan.dict(),
            folder_id=drive_folder_id
        )
        sheet_url = sheet_result['spreadsheet_url']
        print(f"[Export] Plan exported to: {sheet_url} (Folder: {drive_folder_id})")
        
        # Save Sheet URL to Plan
        plan.sheet_url = sheet_url
        campaign_manager.save_plan(plan)
            
    except Exception as e:
        print(f"[Export] Plan Export Failed: {e}")
    
    # 6. Report Tokens
    print(tracker.get_summary())
    
    # PHASE 1 COMPLETE: Return Info for CLI
    return f"Campaign Plan Created! ID: {plan.campaign_id}\nGoogle Sheet: {sheet_url}"

async def generate_email_campaign(
    campaign_id: str,
    drive_folder_id: Optional[str] = POPBRUSH_FOLDER_ID,
    slot_number: Optional[int] = None
) -> str:
    """
    Orchestrates the Execution Phase (Writing Emails).
    
    Args:
        campaign_id (str): The ID of the campaign plan created via plan_campaign.
        drive_folder_id (str, optional): The Google Drive folder ID to export results to.
        slot_number (int, optional): The specific email slot number to generate (idx, e.g. 1). 
                                     If provided, ONLY this slot is generated. 
                                     If omitted, ALL slots in the plan are generated.
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
    
    stylist = StylistAgent()
    results = []
    
    # 2. Iterate Slots
    target_languages = plan.languages or ["FR"]

    for slot in plan.email_slots:
        # FILTER: If slot_number is provided, skip others
        if slot_number is not None and slot.slot_number != slot_number:
            continue
            
        print(f"\n>>> PROCESSING EMAIL #{slot.slot_number} ({slot.email_purpose}) <<<")
        
        for lang in target_languages:
            print(f"   > [Language: {lang}]")
            
            # A. Strategist (Create Blueprint using Slot Directives)
            request = CampaignRequest(
                brand_name=plan.brand_name,
                offer=slot.offer_details or "General Brand Awareness",
                theme_angle=slot.theme,
                target_audience=brand_bio.target_audience
            )
            
            # Pass folder selection context? Not needed for Strategist.
            blueprint = await strategist_agent(request, brand_bio, campaign_context=slot, language=lang)
            
            # B. Drafter Wrapper Loop (Judge + Repair)
            final_draft = None
            revision_feedback = None
            
            # Determine history for this brand/ isolation
            history_identifier = brand_bio.brand_id if getattr(brand_bio, 'brand_id', None) else plan.brand_name
            past_emails = history_manager.get_recent_campaigns(history_identifier, limit=10)
            past_emails_dicts = [entry.model_dump() for entry in past_emails]
    
            # 1. GENERATION + DETERMINISTIC LOOP (Strict)
            max_det_retries = 5
            det_attempt = 0
            
            # SESSION START
            from email_orchestrator.subagents.drafter_agent import DraftingSession
            drafting_session = DraftingSession(blueprint, brand_bio, language=lang, campaign_context=plan.campaign_context)
            
            # Initial Draft
            draft = await drafting_session.start()
            
            while det_attempt < max_det_retries:
                # draft is already generated above or via revision below
                det_issues = det_verifier.verify_draft(draft, history=past_emails_dicts, campaign_id=plan.campaign_id)
                
                if not det_issues:
                    print(f"[Email #{slot.slot_number}-{lang}] Layer 1 (Deterministic) Passed.")
                    break
                    
                det_attempt += 1
                print(f"[Email #{slot.slot_number}-{lang}] Layer 1 FAILED ({len(det_issues)} issues). Retry {det_attempt}/{max_det_retries}...")
                
                # Construct feedback ONLY for deterministic issues
                feedback_msg = "STRICT RULES VIOLATION. You MUST fix these before we can proceed:\n"
                feedback_msg += "\n".join([f"- [{i.field}] {i.problem} (Reason: {i.rationale})" for i in det_issues])
                
                # LOGGING for diagnosis (User Request)
                print(f"[Email #{slot.slot_number}-{lang}] DET FEEDBACK SENT TO DRAFTER:\n{feedback_msg}")
                
                # Session-based Revision
                draft = await drafting_session.revise(feedback_msg)
    
            if det_attempt >= max_det_retries:
                print(f"[Email #{slot.slot_number}-{lang}] CRITICAL: Failed to fix deterministic issues after {max_det_retries} attempts.")
                # We still proceed to LLM QA but it will likely fail too. Or we could raise/skip.
                # For now, let's proceed with the best we have.
    
            # 2. [NEW] STYLIST AGENT (Tactical Formatting)
            # Runs on the draft (either perfected or best-effort) before final LLM QA
            print(f"[Email #{slot.slot_number}-{lang}] Passing to Stylist for tactical formatting...")
            try:
                # draft is an EmailDraft Pydantic object, accessed via dot notation
                raw_desc = getattr(draft, 'descriptive_block_content', '')
                if raw_desc:
                    styled_desc = await stylist.style_content(
                        content=raw_desc, 
                        structure_id=blueprint.structure_id,
                        brand_voice=brand_bio.brand_voice, 
                        language=lang
                    )
                    # Update the Pydantic model directly
                    draft.descriptive_block_content = styled_desc
                    print(f"[Email #{slot.slot_number}-{lang}] Stylist applied formatting.")
            except Exception as e:
                 print(f"[Email #{slot.slot_number}-{lang}] Stylist failed, keeping raw draft: {e}")

            # 3. LLM QA LOOP (One-Pass)
            print(f"[Email #{slot.slot_number}-{lang}] Proceeding to LLM QA...")
            # Todo: Verifier should ideally know language too, but English feedback is usually fine for general structure checks.
            # Assuming Verifier is Language-Agnostic or defaults to EN analysis which works ok for structure.
            # Ideally Verifier should verify IN that language.
            # For now, standard verifier is used.
            verification = await verifier_agent(draft, blueprint, plan.brand_name, campaign_context=plan.campaign_context)
            
            if verification.approved:
                print(f"[Email #{slot.slot_number}-{lang}] APPROVED! Score: {verification.score}")
                final_draft = draft
            else:
                print(f"[Email #{slot.slot_number}-{lang}] REJECTED. Requesting ONE-TIME Strategic Revision...")
                
                # Construct detailed feedback for revision
                feedback_lines = [f"QA VERDICT: {verification.feedback_for_drafter}"]
                for imp in verification.top_improvements:
                    feedback_lines.append(f"- [Rank {imp.rank}] [{imp.category}] {imp.problem}")
                    feedback_lines.append(f"  Fix Options: {json.dumps(imp.options)}")
    
                revision_feedback = "\n".join(feedback_lines)
                
                # Session-based Revision
                final_draft = await drafting_session.revise(revision_feedback)
                
                # Final Deterministic Check on revised draft (Safety)
                final_det = det_verifier.verify_draft(final_draft, history=past_emails_dicts, campaign_id=plan.campaign_id)
                if final_det:
                    print(f"[Email #{slot.slot_number}-{lang}] Warning: Revised draft still has {len(final_det)} deterministic issues.")
                
                print(f"[Email #{slot.slot_number}-{lang}] Revision complete. Auto-approving for export.")
            
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
            
            # Serialize full draft for compiler
            draft_data = final_draft.dict()
            draft_data.update({
                "slot_number": slot.slot_number,
                "status": "completed",
                "content": final_draft.full_text_formatted,
                "structure_id": blueprint.structure_id,
                "language": lang 
            })
            results.append(draft_data)
        
        # F. Export to Google Docs (LEGACY - Disabled)
        # try:
        #     doc_result = export_email_to_google_docs(
        #         email_draft=final_draft.dict(),
        #         brand_name=plan.brand_name,
        #         folder_id=drive_folder_id, # Use the passed folder ID
        #         structure_name=blueprint.structure_id,
        #         language=plan.language
        #     )
        #     print(f"[Export] Email #{slot.slot_number} exported to: {doc_result['document_url']} (Folder: {drive_folder_id})")
        # except Exception as e:
        #     print(f"[Export] Failed to export doc: {e}")


    print("\n--- CAMPAIGN EXECUTION FINISHED ---")
    print(tracker.get_summary())
    
    return json.dumps(results, indent=2)
