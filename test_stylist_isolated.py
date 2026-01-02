import asyncio
from email_orchestrator.subagents.stylist_agent import StylistAgent
from email_orchestrator.tools.google_docs_export import export_email_to_google_docs

# Mock Data for Testing
MOCK_STRUCTURE = "STRUCT_NARRATIVE_PARAGRAPH"
MOCK_BRAND_VOICE = "Friendly, empathetic, warm, inviting. Focus on relief and happiness."
MOCK_CONTENT = """
Imaginez des matins sans pleurs — et sans cris. Avec la brosse PopBrush, le démêlage devient un moment de douceur - vraiment - et de complicité avec votre enfant. Plus de nœuds, plus de douleur, juste des cheveux soyeux et un sourire retrouvé en quelques secondes. C'est la magie d'une routine apaisée.
"""

async def run_test():
    print("--- STARTING ISOLATED STYLIST TEST ---")
    print(f"Structure: {MOCK_STRUCTURE}")
    print("Raw Content:")
    print(MOCK_CONTENT.strip())
    print("-" * 30)

    agent = StylistAgent()
    
    try:
        styled_html = await agent.style_content(
            content=MOCK_CONTENT,
            structure_id=MOCK_STRUCTURE,
            brand_voice=MOCK_BRAND_VOICE,
            language="French"
        )
        
        print("\n--- STYLED OUTPUT (HTML) ---")
        print(styled_html)
        print("-" * 30)
        
        # EXPORT TO GOOGLE DOCS FOR VISUAL VERIFICATION
        print("\n[Visual Verification] Exporting to Google Docs...")
        
        mock_draft = {
            "subject": "[TEST] Stylist Visualization",
            "preview": "Visual check of Stylist output",
            "hero_title": "Stylist Agent Test",
            "hero_subtitle": f"Structure: {MOCK_STRUCTURE}",
            "cta_hero": "Check Below",
            "descriptive_block_title": "Styled Content",
            "descriptive_block_subtitle": "Below is the output from the Stylist Agent:",
            "descriptive_block_content": styled_html,
            "product_block_title": "End of Test",
            "product_block_subtitle": "",
            "products": [],
            "cta_product": "Done"
        }
        
        result = export_email_to_google_docs(
            email_draft=mock_draft,
            brand_name="StylistTest",
            structure_name=MOCK_STRUCTURE,
            language="French"
        )
        
        print(f"✅ EXPORT SUCCESS! View formatting here:\n{result['document_url']}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
