
import os
import sys
from email_orchestrator.tools.google_docs_export import export_email_to_google_docs

# Mock Data
MOCK_DRAFT = {
    "subject": "Test HTML Export Table",
    "preview": "Checking table rendering...",
    "hero_title": "Visual Test",
    "hero_subtitle": "This is a <i>subtle</i> subtitle.",
    "cta_hero": "Click Me NOW",
    "descriptive_block_title": "Why Choose Us?",
    "descriptive_block_subtitle": "Here is the <u>truth</u> about our product.",
    "descriptive_block_content": """
    <p>This is a paragraph with <b>bold text</b> and <i>italic text</i> and <u>underlined text</u>.</p>
    <ul>
        <li>Item 1: <b>Bold</b> start</li>
        <li>Item 2: <i>Italic</i> middle</li>
        <li>Item 3: <u>Underline</u> end</li>
    </ul>
    <table>
        <tr>
            <td><b>Bold Cell</b></td>
            <td><i>Italic Cell</i></td>
        </tr>
        <tr>
            <td><u>Underline Cell</u></td>
            <td>Mixed <b>B</b><i>I</i><u>U</u></td>
        </tr>
    </table>
    """,
    "product_block_title": "Products",
    "product_block_subtitle": "The goods",
    "products": ["Prod A", "Prod B"],
    "cta_product": "Buy Now"
}

def run_test():
    print("Running HTML Export Test...")
    try:
        result = export_email_to_google_docs(
            email_draft=MOCK_DRAFT,
            brand_name="TestBrand",
            structure_name="STRUCT_STAT_ATTACK",
            language="English"
        )
        print("SUCCESS!")
        print(f"Doc URL: {result['document_url']}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
