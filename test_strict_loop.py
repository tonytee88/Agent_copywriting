
import asyncio
import json
from email_orchestrator.schemas import CampaignPlan, BrandBio, CampaignPlanVerification, BlockingIssue, OptimizationOption
from email_orchestrator.subagents.campaign_planner_agent import revise_campaign_plan
from email_orchestrator.subagents.campaign_plan_verifier_agent import campaign_plan_verifier_agent

async def test_strict_qa_loop():
    print("=== Testing Strict Mode Strategic Revision Loop ===")
    
    # 1. Mock a plan that might have strategic issues (e.g. narrative jump)
    plan_data = {
        "campaign_id": "strict_qa_test",
        "brand_name": "PopBrush",
        "brand_id": "popbrush_test",
        "campaign_name": "Test Strategic Campaign",
        "campaign_goal": "Build awareness and drive sales",
        "duration": "1 week",
        "total_emails": 2,
        "overarching_narrative": "A quick intro then a hard sell.", # Narratively weak
        "promotional_balance": "50/50",
        "created_at": "2024-12-23T00:00:00Z",
        "email_slots": [
            {
                "slot_number": 1,
                "email_purpose": "educational",
                "intensity_level": "soft",
                "transformation_description": "Knowing that silicon is better.",
                "structure_id": "STRUCT_NARRATIVE_PARAGRAPH",
                "angle_description": "What are silicon bristles?",
                "persona_description": "Curious Learner",
                "cta_description": "Read Blog",
                "theme": "Education",
                "key_message": "Silicon is techy."
            },
            {
                "slot_number": 2,
                "email_purpose": "conversion",
                "intensity_level": "hard_sell",
                "transformation_description": "Buying a toothbrush now.", # Weak connection to slot 1
                "structure_id": "STRUCT_5050_SPLIT",
                "angle_description": "20% off sale ending soon.",
                "persona_description": "Deal Hunter",
                "cta_description": "Shop Now",
                "theme": "Sales",
                "key_message": "Buy it now."
            }
        ]
    }
    
    plan = CampaignPlan(**plan_data)
    brand_bio = BrandBio(
        brand_name="PopBrush", 
        industry="Dental Care",
        target_audience="Eco-conscious adults",
        unique_selling_proposition="Recyclable silicon toothbrushes",
        brand_voice="Friendly and health-focused",
        mission_statement="Clean teeth for all",
        key_products=["Silicon Toothbrush"]
    )
    
    # 2. Run Real Verifier Agent
    print("\n[Step 1] Calling Strict Plan QA (Layer 2)...")
    verification = await campaign_plan_verifier_agent(plan, brand_bio)
    
    if verification.approved:
        print("Plan was approved! (Unexpected for this weak example, but LLM might be lenient).")
        # If it's approved, we can't test revision. Let's force a rejection for testing purposes if it happened to pass.
    
    # 3. Test Revision Loop (either with real response or forced one)
    if not verification.approved:
        print("\n[Step 2] Plan REJECTED. Calling Revision Agent with optimization options...")
        revised_plan = await revise_campaign_plan(plan, verification, brand_bio)
        
        print("\n[Step 3] Verifying Revised Plan...")
        new_verification = await campaign_plan_verifier_agent(revised_plan, brand_bio)
        
        if new_verification.approved:
            print("SUCCESS: Revised plan passed Strict Mode QA!")
        else:
            print("Revised plan still rejected. Verdict:", new_verification.final_verdict)
    else:
        print("Skipping revision test because plan was approved.")

if __name__ == "__main__":
    asyncio.run(test_strict_qa_loop())
