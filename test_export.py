import json
import os
from email_orchestrator.tools.campaign_compiler import compile_campaign_doc

DRAFT_FILE = "outputs/drafts/test_tables.json"
FOLDER_ID = "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y"

def test_export():
    print(f"Loading drafts from {DRAFT_FILE}...")
    with open(DRAFT_FILE, 'r') as f:
        drafts = json.load(f)
    
    print(f"Loaded {len(drafts)} drafts.")
    
    # Run Compiler
    print("Compiling document (Verify Rate Limits & Formatting)...")
    doc_url = compile_campaign_doc(
        brand_name="PopBrush",
        campaign_id="TEST_EXPORT",
        target_month="Jan2026",
        drafts=drafts,
        folder_id=FOLDER_ID
    )
    print(f"Success! Doc: {doc_url}")

if __name__ == "__main__":
    test_export()
