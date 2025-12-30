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
        doc_title = f"{brand_name}-{target_month}-{campaign_id}_Drafts"
        
        # 1. Create Doc
        doc = self.docs_service.documents().create(body={'title': doc_title}).execute()
        doc_id = doc.get('documentId')
        
        # 2. Move to folder
        if folder_id:
            self._move_to_folder(doc_id, folder_id)
            
        # 3. Batch Update Content
        requests = []
        index = 1
        
        # Add Title
        requests.append({
            'insertText': {
                'location': {'index': index},
                'text': f"CAMPAIGN DRAFTS: {doc_title}\n\n"
            }
        })
        index += len(f"CAMPAIGN DRAFTS: {doc_title}\n\n")
        
        # Sort drafts by slot number
        sorted_drafts = sorted(drafts, key=lambda x: x.get('slot_number', 0))
        
        for draft in sorted_drafts:
            slot_num = draft.get('slot_number')
            subject = draft.get('subject', 'No Subject')
            body = draft.get('body', '')
            
            # Header
            header = f"--- EMAIL #{slot_num} ---\nSubject: {subject}\n\n"
            requests.append({
                'insertText': {
                    'location': {'index': index},
                    'text': header
                }
            })
            # index is tricky with batch updates because earlier inserts shift indices.
            # Best practice: Insert in REVERSE order or calculate offsets carefully.
            # BUT: If we chain requests in one batch, the API handles indices based on state BEFORE the batch (if using logic) OR strictly sequential.
            # Actually, the Docs API documentation says: "The index must be relative to the beginning of the document."
            # AND "All indexes in a batch request are relative to the state of the document BEFORE any of the requests in the batch are applied." -> THIS IS WRONG.
            # CORRECTION: "The index of the text location. You can insert text into the document body, headers, footers, or footnotes."
            # Actually, standard practice for appending is easier: Just insert at end, but getting "end" index is hard without reading.
            # Alternative: Reverse order insertion at index 1.
            pass

        # Let's switch to a simpler "Append in Reverse" strategy to avoid index math hell.
        # We want Email 1 first, then Email 2.
        # If we insert Email 2 at Index 1, then insert Email 1 at Index 1, the result is Email 1 followed by Email 2.
        # Perfect.
        
        requests = []
        
        # Iterate REVERSE
        for draft in reversed(sorted_drafts):
            slot_num = draft.get('slot_number')
            subject = draft.get('subject', 'No Subject')
            body = draft.get('html_content', '') or draft.get('content', '') # Prefer plain text if available
            
            # Simple conversion of HTML breaks to newlines if needed, or just dump content.
            # Assuming 'content' is the text version from drafter.
            text_body = draft.get('content', body)
            
            # Content Block
            block = f"--- EMAIL #{slot_num} ---\nSubject: {subject}\n\n{text_body}\n\n"
            block += "="*30 + "\n\n" # Page break simulation
            
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': block
                }
            })
            
        # Finally Insert Title at Index 1
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': f"CAMPAIGN DRAFTS: {doc_title}\nGenerated: {datetime.now()}\n\n"
            }
        })
        
        self.docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
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
