
import asyncio
import json
from email_orchestrator.schemas import CampaignPlan, BrandBio, CampaignPlanVerification
from email_orchestrator.tools.deterministic_verifier import DeterministicVerifier
from email_orchestrator.subagents.campaign_planner_agent import revise_campaign_plan
from email_orchestrator.tools.history_manager import HistoryManager

async def test_revision_loop():
    print("=== Testing Automated Plan Revision Loop ===")
    
    det_verifier = DeterministicVerifier()
    
    # 1. Create a "Bad" plan with intentional collisions
    bad_plan_data = {
        "campaign_id": "test_collision_loop",
        "brand_name": "PopBrush",
        "campaign_name": "Test Collision Campaign",
        "campaign_goal": "Force a QA collision and fix it",
        "duration": "1 week",
        "total_emails": 3,
        "overarching_narrative": "Testing the loop",
        "promotional_balance": "50/50",
        "created_at": "2024-12-22T00:00:00Z",
        "email_slots": [
            {
                "slot_number": 1,
                "email_purpose": "promotional",
                "intensity_level": "medium",
                "transformation_description": "Transforming your smile",
                "structure_id": "ST_01", # Conflict with Slot 2
                "angle_description": "The best toothbrush for travel",
                "persona_description": "Savvy Traveler",
                "cta_description": "Buy Now",
                "theme": "Travel",
                "key_message": "Portable clean"
            },
            {
                "slot_number": 2,
                "email_purpose": "educational",
                "intensity_level": "soft",
                "transformation_description": "Improving dental health",
                "structure_id": "ST_01", # Conflict with Slot 1
                "angle_description": "Why silicon bristles matter",
                "persona_description": "Health Enthusiast",
                "cta_description": "Learn More",
                "theme": "Health",
                "key_message": "Gentle clean"
            },
            {
                "slot_number": 3,
                "email_purpose": "conversion",
                "intensity_level": "hard_sell",
                "transformation_description": "Transforming your smile with modern tech", # Conflict with Slot 1 (Jaccard)
                "structure_id": "ST_03",
                "angle_description": "The best toothbrush for travel adventures", # Conflict with Slot 1 (Fuzzy)
                "persona_description": "Adventure Seeker",
                "cta_description": "Get Discount",
                "theme": "Adventure",
                "key_message": "Rugged clean"
            }
        ]
    }
    
    plan = CampaignPlan(**bad_plan_data)
    brand_bio = BrandBio(
        brand_name="PopBrush", 
        industry="Dental Care",
        target_audience="Eco-conscious adults",
        unique_selling_proposition="Recyclable silicon toothbrushes",
        brand_voice="Friendly and health-focused",
        mission_statement="Clean teeth for all",
        key_products=["Silicon Toothbrush"]
    )
    
    # 2. Run Verification
    print("\n[Step 1] Running Deterministic QA on Bad Plan...")
    issues = det_verifier.verify_plan(plan, [])
    
    if not issues:
        print("FAILED: No issues detected in a known bad plan.")
        return

    print(f"Detected {len(issues)} issues as expected.")
    for i in issues:
        print(f" - {i.field}: {i.problem} (Rationale: {i.rationale})")

    # 3. Create Verification object (mocking what plan_campaign does)
    issues_summary = "\n".join([f"- {i.field}: {i.problem} (Rationale: {i.rationale})" for i in issues])
    feedback_msg = f"Strict Constraints Violation. Fix these repetition errors:\n{issues_summary}"
    
    verification = CampaignPlanVerification(
        approved=False,
        score=0,
        variety_check={},
        balance_check={},
        coherence_check={},
        issues=issues,
        feedback_for_planner=feedback_msg
    )

    # 4. Call Revision Agent
    print("\n[Step 2] Calling Revision Agent with detailed feedback...")
    revised_plan = await revise_campaign_plan(plan, verification, brand_bio)
    
    print("\n[Step 3] Verifying Revised Plan...")
    new_issues = det_verifier.verify_plan(revised_plan, [])
    
    if new_issues:
        print("FAILED: Revised plan still has issues.")
        for i in new_issues:
            print(f" - {i.field}: {i.problem} (Rationale: {i.rationale})")
    else:
        print("SUCCESS: Revised plan passed all Layer 1 checks!")
        print("\nRevised Email Slots:")
        for slot in revised_plan.email_slots:
            print(f" Slot {slot.slot_number}: ID={slot.structure_id}, Angle='{slot.angle_description[:40]}...', Trans='{slot.transformation_description[:40]}...'")

if __name__ == "__main__":
    asyncio.run(test_revision_loop())
