
import asyncio
import os
import json
from email_orchestrator.schemas import EmailBlueprint, BrandBio
from email_orchestrator.subagents.drafter_agent import drafter_agent
from email_orchestrator.tools.campaign_compiler import compile_campaign_doc

FOLDER_ID = "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y"

async def test_cta_flow():
    print("--- Testing CTA Descriptive Flow ---")
    
    # 1. Mock Input
    blueprint = EmailBlueprint(
        email_id="TEST_CTA",
        slot_number=1,
        send_date="2026-01-01",
        stage="nurture",
        goal="Education",
        structure_id="STRUCT_NARRATIVE_PARAGRAPH",
        angle_id="ANG_STORY",
        persona_id="PER_FOUNDER",
        target_audience="General",
        product_focus="Hydration Bottle",
        transformation_description="Dehydrated -> Healthy",
        angle_description="Story of why we started",
        cta_guidance="View the Bottle",
        campaign_theme="Test Theme",
        structure_execution_map={"instruction": "Use paragraphs"},
        offer_details="None",
        subject_ideas=["Idea 1"],
        preview_text_ideas=["Preview 1"],
        key_points_for_descriptive_block=["Point 1", "Point 2"]
    )
    
    brand_bio = BrandBio(
        brand_name="TestBrand",
        industry="Health",
        target_audience="Families",
        unique_selling_proposition="Quality bottles",
        brand_voice="Friendly"
    )
    
    # 2. Run Drafter (Real Call)
    print("Generating draft...")
    draft = await drafter_agent(blueprint, brand_bio, language="English")
    
    print(f"\n[Result] CTA Descriptive: {draft.cta_descriptive}")
    
    if draft.cta_descriptive:
        print("✅ SUCCESS: CTA Descriptive found in draft.")
    else:
        print("❌ FAILURE: CTA Descriptive missing.")
    
    # 3. Export to Doc
    print("\nExporting to Google Doc...")
    # Convert draft to dict (simulate main.py)
    draft_dict = draft.model_dump()
    draft_dict['language'] = "EN"
    
    doc_url = compile_campaign_doc(
         brand_name="TestBrand",
         campaign_id="TEST_CTA_EXPORT",
         target_month="Jan2026",
         drafts=[draft_dict],
         folder_id=FOLDER_ID
    )
    
    print(f"Doc URL: {doc_url}")

if __name__ == "__main__":
    asyncio.run(test_cta_flow())
