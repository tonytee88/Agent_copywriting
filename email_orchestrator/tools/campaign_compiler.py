"""
Campaign Compiler Module
Merges multiple email drafts into a SINGLE Google Doc.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from email_orchestrator.tools.google_docs_export import write_email_to_doc

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
DEFAULT_CREDENTIALS_PATH = Path(__file__).parent.parent.parent / "google_credentials.json"

class CampaignCompiler:
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            str(DEFAULT_CREDENTIALS_PATH)
        )
        self.docs_service = None
        self.drive_service = None
        self._authenticate()
    
    def _authenticate(self):
        try:
            creds = None
            token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            elif os.path.exists(self.credentials_path):
                creds = service_account.Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
            else:
                raise FileNotFoundError("No valid credentials found.")
            
            self.docs_service = build('docs', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
                
        except Exception as e:
            raise Exception(f"Failed to authenticate: {e}")

    def compile_campaign(self, 
                         brand_name: str, 
                         campaign_id: str, 
                         target_month: str,
                         drafts: List[Dict[str, Any]], 
                         folder_id: Optional[str] = None) -> str:
        """
        Creates ONE Google Doc with all drafts.
        File Name: BRAND-MONTH-CAMPAIGN ID_Drafts
        """
        doc_title = f"{brand_name}-{target_month}-{campaign_id}"
        
        # 1. Create Doc
        doc = self.docs_service.documents().create(body={'title': doc_title}).execute()
        doc_id = doc.get('documentId')
        
        # 2. Move to folder
        if folder_id:
            self._move_to_folder(doc_id, folder_id)
            
        # 3. Batch Update Content (Legacy Format)
        
        # We need to construct the full text and formatting requests exactly like the legacy exporter.
        # Legacy exporter builds a list of content items with 'text', 'bold', 'h1' attributes.
        # We can reuse that logic logic here for each draft.
        
        all_requests = []
        full_text_buffer = "" # We don't really use this for batch updates if we use index 1 inserts.
        # Actually legacy exporter inserts at index 1 REPEATEDLY (Reverse Order construction).
        # Wait, legacy exporter builds a 'requests' list and sends it.
        # Inside _build_email_content_requests, it appends to 'content_items' list, then processes it.
        # It creates ONE big 'insertText' at index 1 for the whole body, then formatting on top.
        
        # So for compilation, we should:
        # 1. Iterate drafts in REVERSE order (Email N ... Email 1)
        # 2. For each draft, build its content items (using legacy logic)
        # 3. Add a separator if it's not the last one (first in reverse)
        # 4. Concatenate all content items into one big list
        # 5. Then finalize the big text insert and formatting requests.
        
        content_items = []
        
        # Title of the Compiled Doc
        content_items.append({"text": f"CAMPAIGN DRAFTS: {doc_title}\nGenerated: {datetime.now()}\n\n", "bold": True, "h1": True})
        content_items.append({"text": "\n", "bold": False, "h1": False})
        
        # Sort drafts
        sorted_drafts = sorted(drafts, key=lambda x: x.get('slot_number', 0))
        
        for draft in sorted_drafts:
            # Use shared exporter logic to write formatted content (Tables, Lists, etc.)
            structure = draft.get('structure_id', 'Unknown')
            lang = draft.get('language', 'English')
            
            try:
                # Add Header text e.g. "--- EMAIL #1 ---"
                slot_header = f"--- EMAIL #{draft.get('slot_number', '?')} ---"
                write_email_to_doc(self.docs_service, doc_id, draft, structure, lang, header_text=slot_header)
                
                # RATE LIMIT PROTECTION: Sleep 2s between writes
                import time
                time.sleep(2)
            except Exception as e:
                print(f"[Compiler] Error writing draft {draft.get('slot_number')}: {e}")
                # Continue to next draft
        
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        print(f"[Compiler] Created Compiled Doc: {doc_url}")
        return doc_url

    def _move_to_folder(self, file_id: str, folder_id: str):
        try:
            file = self.drive_service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
        except Exception:
            pass

def compile_campaign_doc(brand_name, campaign_id, target_month, drafts, folder_id=None):
    compiler = CampaignCompiler()
    return compiler.compile_campaign(brand_name, campaign_id, target_month, drafts, folder_id)
