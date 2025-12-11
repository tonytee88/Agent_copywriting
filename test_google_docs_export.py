"""
Test Google Docs export functionality.
Run this after setting up Google credentials.
"""

import asyncio
import json
from email_orchestrator.tools.google_docs_export import export_email_to_google_docs
from email_orchestrator.tools.campaign_tools import generate_email_campaign

async def test_google_docs_export():
    """Test exporting an email to Google Docs."""
    
    print("=" * 80)
    print("TESTING GOOGLE DOCS EXPORT")
    print("=" * 80)
    
    # Option 1: Export existing email from outputs/
    print("\n[Option 1] Export existing email draft from file...")
    
    # You can load an existing email from outputs/
    # For now, let's generate a fresh one
    
    # Option 2: Generate and export new email
    print("\n[Option 2] Generate new email and export to Google Docs...")
    
    result = await generate_email_campaign(
        brand_name="PopBrush",
        offer="25% off all brushes",
        angle="New Year hair care reset"
    )
    
    # Parse result
    try:
        email_data = json.loads(result)
        
        if email_data.get("status") == "APPROVED":
            draft = email_data.get("draft", {})
            
            print("\n✓ Email generated successfully")
            print(f"  Subject: {draft.get('subject')}")
            
            # Export to Google Docs
            print("\n[Exporting to Google Docs...]")
            
            # Optional: Set folder ID from environment
            import os
            folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            share_with = os.getenv('GOOGLE_DOCS_SHARE_EMAIL')  # Optional
            
            doc_result = export_email_to_google_docs(
                email_draft=draft,
                brand_name="PopBrush",
                folder_id=folder_id,
                share_with=share_with
            )
            
            print("\n" + "=" * 80)
            print("✓ EXPORT SUCCESSFUL!")
            print("=" * 80)
            print(f"Document Title: {doc_result['title']}")
            print(f"Document URL: {doc_result['document_url']}")
            print("\nOpen the link above to view your email in Google Docs!")
            print("=" * 80)
            
        else:
            print(f"\n✗ Email generation failed: {email_data.get('status')}")
            
    except json.JSONDecodeError:
        print("\n✗ Could not parse email result")
        print(result[:500])

if __name__ == "__main__":
    print("\nMake sure you've completed Google API setup (see GOOGLE_SETUP.md)")
    print("Press Enter to continue or Ctrl+C to cancel...")
    input()
    
    asyncio.run(test_google_docs_export())
