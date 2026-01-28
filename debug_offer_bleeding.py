
import asyncio
from email_orchestrator.subagents.drafter_agent import drafter_agent
from email_orchestrator.schemas import EmailBlueprint, BrandBio

async def test_offer_bleeding():
    print("--- TESTING OFFER BLEEDING FIX ---")
    
    # 1. Global Context (The "Noise")
    context = "BLACK FRIDAY SALE! 50% OFF EVERYTHING! USE CODE BF50. URGENT SALE ENDS TONIGHT."
    
    # 2. Specific Blueprint (The "Signal" - Educational)
    blueprint = EmailBlueprint(
        brand_name="PopBrush",
        campaign_theme="Hair Health Education",
        transformation_description="From confused to informed",
        structure_id="STRUCT_NARRATIVE_PARAGRAPH",
        structure_execution_map={"descriptive_block": "Explain why hair breaks in winter"},
        persona_description="Helpful expert, calm, scientific",
        angle_description="Winter is harsh on hair",
        offer_details="NONE (Pure Value)",
        offer_placement="None",
        cta_description="Read more tips",
        cta_style_id="CTA_SOFT",
        subject_ideas=["Why your hair breaks in winter"],
        preview_text_ideas=["It's not just the cold."],
        key_points_for_descriptive_block=["Cold air sucks moisture", "Scarves cause friction", "Indoor heat dries scalp"]
    )
    
    # 3. Brand Bio
    brand = BrandBio(
        brand_name="PopBrush",
        industry="Hair Care",
        target_audience="Women 25-45",
        brand_voice="Gentle, Educational",
        unique_selling_proposition="No pain detangling"
    )
    
    # 4. Run Drafter
    print(f"Context: {context}")
    print(f"Blueprint Offer: {blueprint.offer_details}")
    print("Generating Draft...")
    
    draft = await drafter_agent(blueprint, brand, language="English", campaign_context=context)
    
    print("\n--- GENERATED DRAFT ---")
    print(draft.full_text_formatted)
    
    # 5. Check for Bleeding
    lower_text = draft.full_text_formatted.lower()
    if "black friday" in lower_text or "BF50" in lower_text or "50%" in lower_text:
        print("\n[FAIL] OFFER BLEEDING DETECTED! 'Black Friday' found in text.")
    else:
        print("\n[SUCCESS] NO OFFER BLEEDING. Context was correctly treated as background.")

if __name__ == "__main__":
    asyncio.run(test_offer_bleeding())
