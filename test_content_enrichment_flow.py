import asyncio
import json
from email_orchestrator.subagents.content_enricher import ContentEnricher
from email_orchestrator.subagents.drafter_agent import DraftingSession
from email_orchestrator.tools.brand_bio_manager import BrandBioManager
from email_orchestrator.schemas import EmailBlueprint

async def test_enrichment():
    # 1. Load Real Brand Bio
    manager = BrandBioManager()
    brand_bio = manager.get_bio("ohydration.com")
    if not brand_bio:
        print("Error: Could not load Ohydration bio.")
        return

    enricher = ContentEnricher()
    output_log = ""
    
    # === TEST 1: STAT ATTACK ===
    print("Running Test 1: Stat Attack...")
    
    blueprint_stat = EmailBlueprint(
        brand_name="Ohydration",
        email_purpose="educational",
        target_audience="Health-conscious moms",
        structure_id="STRUCT_STAT_ATTACK",
        angle_description="Hydration is faster with electrolytes",
        offer_placement="none",
        offer_details="None",
        transformation_description="From tired to energized",
        theme="Energy",
        campaign_theme="Optimization", # Required
        cta_description="See the science",
        cta_style_id="LINK_BUTTON",
        # Mocking fields required by Schema
        subject_ideas=["Idea 1"],
        preview_text_ideas=["Preview 1"],
        key_points_for_descriptive_block=["Point 1", "Point 2"],
        structure_execution_map={"STRUCT_STAT_ATTACK": "Do specific things"}
    )
    
    stats_data = await enricher.find_stats(brand_bio.brand_name, brand_bio.product_description)
    
    session = DraftingSession(blueprint_stat, brand_bio, language="English")
    draft_stat = await session.start(real_world_data=stats_data)
    
    output_log += f"=== TEST 1: STAT ATTACK (Ohydration) ===\n\n"
    output_log += f"[Enricher Found Stats]:\n{stats_data}\n\n"
    output_log += f"[Drafter Generated Email]:\n"
    output_log += f"Subject: {draft_stat.subject}\n"
    output_log += f"Descriptive Block HTML:\n{draft_stat.descriptive_block_content}\n"
    output_log += f"Full Draft JSON:\n{draft_stat.model_dump_json(indent=2)}\n\n"


    # === TEST 2: SOCIAL PROOF ===
    print("Running Test 2: Social Proof...")
    
    blueprint_review = EmailBlueprint(
        brand_name="Ohydration",
        email_purpose="promotional",
        target_audience="Athletes",
        structure_id="STRUCT_SOCIAL_PROOF_QUOTE",
        angle_description="Don't just take our word for it",
        offer_placement="bottom",
        offer_details="20% Off",
        transformation_description="Taste the difference",
        theme="Social Proof",
        campaign_theme="Trust",
        cta_description="Shop Now",
        cta_style_id="MAIN_BUTTON",
        subject_ideas=["Idea 1"],
        preview_text_ideas=["Preview 1"],
        key_points_for_descriptive_block=["Point 1", "Point 2"],
        structure_execution_map={"STRUCT_SOCIAL_PROOF_QUOTE": "Use Quote"}
    )
    
    review_data = await enricher.find_reviews(brand_bio.brand_name, brand_bio.product_description)
    
    session = DraftingSession(blueprint_review, brand_bio, language="English")
    draft_review = await session.start(real_world_data=review_data)
    
    output_log += f"--------------------------------------------------\n\n"
    output_log += f"=== TEST 2: SOCIAL PROOF QUOTE (Ohydration) ===\n\n"
    output_log += f"[Enricher Found Reviews]:\n{review_data}\n\n"
    output_log += f"[Drafter Generated Email]:\n"
    output_log += f"Subject: {draft_review.subject}\n"
    output_log += f"Descriptive Block HTML:\n{draft_review.descriptive_block_content}\n"
    output_log += f"Full Draft JSON:\n{draft_review.model_dump_json(indent=2)}\n"
    
    with open("test_enrichment_results.txt", "w") as f:
        f.write(output_log)
        
    print("\n✓ Results saved to test_enrichment_results.txt")

if __name__ == "__main__":
    asyncio.run(test_enrichment())
