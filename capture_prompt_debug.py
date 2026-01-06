
import asyncio
import json
from pathlib import Path
from email_orchestrator.schemas import EmailBlueprint, BrandBio, EmailDraft
from email_orchestrator.subagents.drafter_agent import DraftingSession

# Mock Client to intercept prompt
class MockClient:
    async def generate_text(self, prompt, model):
        # Save prompt to file (SLIM VERSION)
        with open("outputs/debug/drafter_revision_prompt_slim.txt", "w", encoding="utf-8") as f:
            f.write(prompt)
        print("Prompt captured to outputs/debug/drafter_revision_prompt_slim.txt")
        return "{}" # Return empty JSON to satisfy parser (it will look for {})

async def capture_prompt():
    # 1. Mock Data (Reconstructed from Email 1 context)
    blueprint = EmailBlueprint(
        email_id="EMAIL_1_FR",
        slot_number=1,
        send_date="2026-01-05",
        stage="promo",
        goal="Sales",
        structure_id="STRUCT_MINI_GRID",
        structure_execution_map={"instruction": "Use 2x2 grid for product benefits"},
        angle_id="ANG_URGENCY",
        angle_description="Focus on the limited time Winter Sale discounts.",
        persona_id="PER_FOUNDER",
        persona_description="Warm, helpful, parent-to-parent advice.",
        target_audience="Busy parents struggling with hair brushing.",
        product_focus="Pack Confort (Brush + Spray + Clips)",
        transformation_description="From chaotic mornings with tears to calm, smooth brushing routines.",
        cta_guidance="Order the Pack Now",
        campaign_theme="Winter Sales & Family Hydration",
        offer_details="65% OFF Pack Confort",
        offer_placement="Hero",
        subject_ideas=["Soldes d'hiver : -65%", "Fini les pleurs ce matin ?"],
        preview_text_ideas=["Profitez-en vite.", "Offre limitée."],
        key_points_for_descriptive_block=["Detangles gently", "Ends tears", "Complete kit"]
        # campaign_context is NOT in EmailBlueprint, pass separately
    )
    
    campaign_context_str = "Language: French. Focus on 'Winter Hair Care'."
    
    brand_bio = BrandBio(
        brand_name="PopBrush",
        industry="Hair Care",
        target_audience="Parents of young children",
        unique_selling_proposition="Detangling brush that stops tears.",
        brand_voice="Empathetic, cheerful, helpful."
    )
    
    # 2. Previous Draft (from file)
    previous_draft_content = json.dumps({
        "subject": "Soldes d'Hiver : -65% sur le Pack Confort",
        "preview": "Routine capillaire simplifiée, stocks limités.",
        "hero_title": "Offre exceptionnelle : Pack Confort à -65%",
        "hero_subtitle": "Débutez les Soldes avec le Pack Confort PopBrush à prix mini.",
        "cta_hero": "Saisir l'offre",
        "descriptive_block_title": "Simplifiez votre routine capillaire",
        "descriptive_block_subtitle": "Fin des cheveux emmêlés, place à la douceur.",
        "descriptive_block_content": "<table>...</table>",
        "cta_descriptive": "Commandez maintenant",
        "products": ["Pack Confort", "Brosse", "Spray"],
        "product_block_title": "Stocks limités",
        "product_block_subtitle": "Offre exclusive hiver.",
        "cta_product": "Profitez vite"
    }, indent=2)
    
    
    # 3. Simulate Session
    session = DraftingSession(blueprint, brand_bio, language="Français", campaign_context=campaign_context_str)
    session.client = MockClient() # Inject Mock
    
    # Inject History (System Prompt + First Draft)
    # Note: Real session instantiates prompt. We need to call start() to populate history?
    # Or just manual injection.
    # To be accurate to 'revise', we need history populated.
    
    # Let's perform a 'dry run' of start() if possible, but start() calls client.
    # We can just manually populate history to simulate state after 1st Generation.
    
    # Fetch Prompt Template
    prompt_path = Path("email_orchestrator/prompts/drafter/v2.txt")
    template = prompt_path.read_text(encoding="utf-8")
    
    # Mock Format Guide
    format_guide = "Ensure strict Type #1 format..."
    
    # Construct Initial Prompt
    initial_prompt = template.format(
        format_guide=format_guide,
        blueprint=blueprint.model_dump_json(indent=2),
        brand_bio=brand_bio.model_dump_json(indent=2),
        revision_feedback="N/A - First draft"
    )
    initial_prompt += "\n\nCRITICAL: You MUST write the email in Français."
    
    session.history.append({"role": "user", "content": initial_prompt})
    session.history.append({"role": "assistant", "content": previous_draft_content})
    
    # 4. Trigger Revision
    print("Triggering revision...")
    feedback = "STRICT RULES VIOLATION: [hero_subtitle] Text too long. Shorten to 80 chars."
    await session.revise(feedback)

if __name__ == "__main__":
    asyncio.run(capture_prompt())
