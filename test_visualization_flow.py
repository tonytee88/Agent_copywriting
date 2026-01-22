import asyncio
import json
from email_orchestrator.subagents.content_enricher import ContentEnricher
from email_orchestrator.subagents.drafter_agent import DraftingSession
from email_orchestrator.tools.brand_bio_manager import BrandBioManager
from email_orchestrator.schemas import EmailBlueprint
from email_orchestrator.tools.google_docs_export import GoogleDocsExporter

async def test_visualization():
    print("Initializing components...")
    manager = BrandBioManager()
    brand_bio = manager.get_bio("ohydration.com")
    if not brand_bio:
        print("Error: Could not load Ohydration bio.")
        return

    enricher = ContentEnricher()
    exporter = GoogleDocsExporter()
    
    enrichment_log = {}

    # === TEST 1: STAT ATTACK ===
    print("\n\n=== RUNNING TEST 1: STAT ATTACK ===")
    
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
        campaign_theme="Optimization",
        cta_description="See the science",
        cta_style_id="LINK_BUTTON",
        subject_ideas=["Idea 1"],
        preview_text_ideas=["Preview 1"],
        key_points_for_descriptive_block=["Point 1", "Point 2"],
        structure_execution_map={"STRUCT_STAT_ATTACK": "Do specific things"}
    )
    
    # 1. Fetch Stats
    print("Fetching Stats...")
    stats_data = await enricher.find_stats(brand_bio.brand_name, brand_bio.product_description)
    enrichment_log["test_1_stats"] = stats_data
    
    # 2. Draft Email
    print("Drafting Email...")
    session = DraftingSession(blueprint_stat, brand_bio, language="English")
    draft_stat = await session.start(real_world_data=stats_data)
    
    # 3. Export to Google Doc
    print("Exporting to Google Doc...")
    res_stat = exporter.create_email_doc(
        email_draft=draft_stat.model_dump(),
        brand_name="Ohydration Test",
        folder_id=None, # Root
        structure_name="STRUCT_STAT_ATTACK",
        language="English"
    )
    print(f"✅ STAT ATTACK DOC: {res_stat['document_url']}")


    # === TEST 2: SOCIAL PROOF ===
    print("\n\n=== RUNNING TEST 2: SOCIAL PROOF QUOTE ===")
    
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
    
    # 1. Fetch Reviews
    print("Fetching Reviews...")
    review_data = await enricher.find_reviews(brand_bio.brand_name, brand_bio.product_description)
    enrichment_log["test_2_reviews"] = review_data
    
    # 2. Draft Email
    print("Drafting Email...")
    session = DraftingSession(blueprint_review, brand_bio, language="English")
    draft_review = await session.start(real_world_data=review_data)
    
    # 3. Export to Google Doc
    print("Exporting to Google Doc...")
    res_review = exporter.create_email_doc(
        email_draft=draft_review.model_dump(),
        brand_name="Ohydration Test",
        folder_id=None,
        structure_name="STRUCT_SOCIAL_PROOF_QUOTE",
        language="English"
    )
    print(f"✅ RELATIONAL PROOF DOC: {res_review['document_url']}")
    
    # === SAVE RAW OUTPUT ===
    with open("enricher_output.json", "w") as f:
        json.dump(enrichment_log, f, indent=4)
    print("\n✓ Saved raw enrichment data to enricher_output.json")

if __name__ == "__main__":
    asyncio.run(test_visualization())
