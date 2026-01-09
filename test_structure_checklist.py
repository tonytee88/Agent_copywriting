import asyncio
from email_orchestrator.subagents.stylist_agent import StylistAgent

async def test_checklist_structure():
    stylist = StylistAgent()
    
    # Mock input from Drafter (Block 2: Descriptive)
    # The title is separate. The content has both the intro sentence and the bullets.
    mock_email_data = {
        "descriptive_block_title": "Routine Matinale Simplifiée",
        "descriptive_block_content": "Rendez vos matins plus sereins. ✨ Gain de temps : Cheveux coiffés vite, matin sans cris. ✨ Utilisation facile : Pour tous, même les enfants. ✨ Pack complet : Tout pour douceur et discipline. Retrouvez la sérénité chaque matin.",
        # Other required fields to prevent errors
        "subject": "Test Subject",
        "preview": "Test Preview",
        "hero_title": "Hero Title", 
        "hero_subtitle": "Hero Subtitle",
        "cta_hero": "CTA",
        "descriptive_block_subtitle": "Sub",
        "cta_descriptive": "CTA",
        "product_block_title": "Prod",
        "product_block_subtitle": "Sub",
        "products": ["P1"],
        "cta_product": "CTA"
    }
    
    structure_id = "STRUCT_EMOJI_CHECKLIST"
    
    print(f"Testing {structure_id}...")
    print(f"Input Content: {mock_email_data['descriptive_block_content'][:50]}...")
    
    # Stylist processes just the content block
    styled_html = await stylist.style_content(
        content=mock_email_data["descriptive_block_content"],
        structure_id=structure_id,
        brand_voice="Professional yet Friendly",
        language="French"
    )
    
    # Extract the relevant part
    print("\n=== GENERATED HTML SNIPPET ===")
    print(styled_html)
    
    snippet = styled_html
    # Validation
    if "<p>" in snippet and "<ul>" in snippet:
         print("\n✅ SUCCESS: Found both paragraph (Intro) and list (Bullets).")
    else:
         print("\n❌ FAILURE: Missing p or ul tags.")

if __name__ == "__main__":
    asyncio.run(test_checklist_structure())
