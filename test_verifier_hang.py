
import asyncio
import json
from email_orchestrator.subagents.campaign_plan_verifier_agent import campaign_plan_verifier_agent
from email_orchestrator.schemas import CampaignPlan, BrandBio, EmailSlot

async def test_hang():
    print("Testing verifier for hang...")
    
    # Mock data
    brand_bio = BrandBio(
        brand_name="PopBrush",
        industry="Hair",
        target_audience="Women",
        unique_selling_proposition="Easy brushing",
        brand_voice="Fun"
    )
    
    plan = CampaignPlan(
        campaign_id="test_id",
        brand_name="PopBrush",
        campaign_name="Test Campaign",
        campaign_goal="Sales",
        duration="1 week",
        total_emails=3,
        overarching_narrative="Buy now",
        promotional_balance="High",
        created_at="2025-01-01",
        status="draft",
        email_slots=[
            EmailSlot(
                slot_number=1,
                email_purpose="promotional",
                intensity_level="hard_sell",
                transformation_description="Bad hair days to good",
                structure_id="STRUCT_IMAGE_FOCUS",
                angle_description="Save time",
                persona_description="Best friend",
                cta_description="Shop now",
                theme="New Year",
                key_message="Buy it"
            ),
             EmailSlot(
                slot_number=2,
                email_purpose="promotional",
                intensity_level="hard_sell",
                transformation_description="Tangled to smooth",
                structure_id="STRUCT_BEFORE_AFTER",
                angle_description="No pain",
                persona_description="Expert",
                cta_description="Get yours",
                theme="New Year",
                key_message="Buy it now"
            )
        ]
    )
    
    # Call agent
    print("Calling agent...")
    result = await campaign_plan_verifier_agent(plan, brand_bio)
    print("Agent returned!")
    print(f"Approved: {result.approved}")

if __name__ == "__main__":
    asyncio.run(test_hang())
