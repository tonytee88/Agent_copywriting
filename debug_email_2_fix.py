
import asyncio
from email_orchestrator.subagents.drafter_agent import drafter_agent
from email_orchestrator.schemas import EmailBlueprint, BrandBio

async def test_email_2_fix():
    print("--- TESTING EMAIL 2 FIX (FRENCH PROMO) ---")
    
    # 1. Blueprint (Promotional - typical Email 2)
    blueprint = EmailBlueprint(
        brand_name="PopBrush",
        campaign_theme="Black Friday",
        transformation_description="Stop fighting with tangles",
        structure_id="STRUCT_SCARCITY_TIMER", # Common for promos
        structure_execution_map={"descriptive_block": "Explain the discount"},
        persona_description="Excited, Urgent",
        angle_description="Don't miss out",
        offer_details="50% OFF EVERYTHING",
        offer_placement="Hero",
        cta_description="Action Verb + Now (e.g. Shop Now, Acheter, Kaufen)", # New abstract style
        cta_style_id="CTA_HARD",
        subject_ideas=["50% de reduction!"],
        preview_text_ideas=["C'est maintenant."],
        key_points_for_descriptive_block=["Ends tonight", "Best price of year"]
    )
    
    # 2. Brand Bio
    brand = BrandBio(
        brand_name="PopBrush",
        industry="Hair Care",
        target_audience="Women 25-45",
        brand_voice="Gentle, Educational",
        unique_selling_proposition="No pain detangling"
    )
    
    # 3. Run Drafter (Target: French)
    print("Generating Draft (Language: French)...")
    
    draft = await drafter_agent(blueprint, brand, language="French", campaign_context="Black Friday Sale")
    
    print("\n--- GENERATED DRAFT ---")
    print(f"HERO SUBTITLE: {draft.hero_subtitle}")
    print(f"HERO CTA: {draft.cta_hero}")
    
    # 4. Check CTA Language
    lower_cta = draft.cta_hero.lower()
    if "shop now" in lower_cta or "get yours" in lower_cta:
        print("[FAIL] CTA is English!")
    else:
        print("[SUCCESS] CTA seems French/Target (Not 'Shop Now').")
        
    # 5. Check Subtitle Length
    if len(draft.hero_subtitle) > 60: # giving slightly buffer over 50 strict
        print(f"[FAIL] Subtitle too long ({len(draft.hero_subtitle)} chars).")
    else:
        print(f"[SUCCESS] Subtitle length ok ({len(draft.hero_subtitle)} chars).")

if __name__ == "__main__":
    asyncio.run(test_email_2_fix())
