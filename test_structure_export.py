
import asyncio
import os
from datetime import datetime
from email_orchestrator.subagents.stylist_agent import StylistAgent
from email_orchestrator.tools.google_docs_export import GoogleDocsExporter, write_email_to_doc

# Mock Content for Watercolor Paints
RAW_CONTENT = """
Unlock your inner artist with our Professional Watercolor Set. 
These high-pigment paints blend effortlessly to create stunning, vibrant landscapes. 
Whether you are a beginner or a pro, you will love the smooth texture and rich colors. 
Includes 24 pans, a travel brush, and a mixing palette. 
Perfect for plein air painting or studio work. 
Capture the light and shadow like the old masters.
"""

STRUCTURES = [
    "STRUCT_STAT_ATTACK",
    "STRUCT_GIF_PREVIEW"
]

async def main():
    print("=== STARTING STRUCTURE VISUALIZATION TEST ===")
    
    stylist = StylistAgent()
    exporter = GoogleDocsExporter()
    
    # 1. Create a blank document
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    doc_title = f"STRUCTURE VISUALIZATION TEST - {timestamp}"
    
    doc = exporter.docs_service.documents().create(
        body={'title': doc_title}
    ).execute()
    doc_id = doc.get('documentId')
    print(f"Created Doc: https://docs.google.com/document/d/{doc_id}/edit")
    
    # 2. Iterate and Append
    for struct_id in STRUCTURES:
        print(f"\n>>> Processing: {struct_id}")
        
        # Style the content
        html_output = await stylist.style_content(
            content=RAW_CONTENT,
            structure_id=struct_id,
            brand_voice="Inspiring, Artistic, Professional",
            language="English"
        )
        
        # Create Dummy Draft for Exporter
        dummy_draft = {
            "subject": f"Test: {struct_id}",
            "preview": "Visual test of structure layout.",
            "hero_title": "Watercolor Mastery",
            "hero_subtitle": "Experience the flow of color.",
            "cta_hero": "Shop Paint",
            
            "descriptive_block_title": f"Layout: {struct_id}",
            "descriptive_block_subtitle": "See how this block renders below.",
            "descriptive_block_content": html_output,
            "cta_descriptive": "Buy This Kit",
            
            "product_block_title": "Featured Tools",
            "product_block_subtitle": "Essentials for your art.",
            "products": ["Pro Brush Set", "Canvas Pad", "Ease"],
            "cta_product": "View All"
        }
        
        # Write to Doc
        write_email_to_doc(
            docs_service=exporter.docs_service,
            document_id=doc_id,
            email_draft=dummy_draft,
            structure_name=struct_id,
            language="English",
            header_text=f"=== {struct_id} ==="
        )
        
    print(f"\n\nSUCCESS! View results here:\nhttps://docs.google.com/document/d/{doc_id}/edit")

if __name__ == "__main__":
    asyncio.run(main())
