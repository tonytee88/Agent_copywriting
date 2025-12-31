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
            # We want to use the EXACT logic from _build_email_content_requests
            # Let's inline a simplified version of that helper here
            
            slot_num = draft.get('slot_number')
            
            # Helper to add to our local list
            def add(text, bold=False, h1=False):
                if not text: return
                content_items.append({"text": str(text), "bold": bold, "h1": h1})
            def add_br():
                content_items.append({"text": "\n", "bold": False, "h1": False})

            add(f"--- EMAIL #{slot_num} ---", h1=True) 
            add_br()
            add("##########")
            add_br()
            add_br()
            add(f"LANGUAGE: {draft.get('language', 'English')}")
            add_br()
            add_br()
            add("Subject Line : ", bold=True)
            add(draft.get('subject', ''))
            add_br()
            add("Preview Text : ", bold=True)
            add(draft.get('preview', ''))
            add_br()
            add_br()
            add("Hero Banner Title : ", bold=True)
            add(draft.get('hero_title', ''))
            add_br()
            add("Hero Banner Subtitle : ", bold=True)
            add(draft.get('hero_subtitle', ''))
            add_br()
            add("CTA : ", bold=True)
            add(draft.get('cta_hero', ''))
            add_br() 
            add_br()
            add("Descriptive Block Title : ", bold=True)
            add(draft.get('descriptive_block_title', ''))
            add_br()
            add("Sub-title : ", bold=True)
            add(draft.get('descriptive_block_subtitle', ''))
            add_br()
            add_br()
            add(f"[[{draft.get('structure_id', 'Unknown Pattern')}]]")
            add_br()
            add(draft.get('descriptive_block_content', ''))
            add_br()
            add_br()
            add("CTA : ", bold=True)
            add(draft.get('cta_hero', ''))  # Legacy used cta_hero again here? Checking legacy code. Yes.
            add_br()
            add_br()
            add("Product Block Title : ", bold=True)
            add(draft.get('product_block_title', 'Shop the Collection')) 
            add_br()
            add("Product Block Subtitle : ", bold=True)
            add(draft.get('product_block_subtitle', ''))
            add_br()
            add_br()
            products = draft.get('products', [])
            if not products and draft.get('product_block_content'):
                 add(draft.get('product_block_content'))
                 add_br()
            else:
                 for prod in products:
                     add(prod)
                     add_br()
            add("CTA : ", bold=True)
            add(draft.get('cta_product', ''))
            add_br()
            add("##########")
            add_br()
            add_br()
            add("="*30) # Separator between emails
            add_br()
            add_br()
            
        # --- PARSE & EXECUTE (Legacy Logic Adapted) ---
        import re
        full_text = ""
        style_requests = []
        current_idx = 1
        
        for item in content_items:
            text = item['text']
            is_static_bold = item['bold']
            is_h1 = item['h1']

            # Parse <b> tags for inline bolding
            parts = re.split(r'(<b>.*?</b>)', text, flags=re.DOTALL)
            
            for part in parts:
                if part.startswith('<b>') and part.endswith('</b>'):
                    clean_part = part[3:-4]
                    start = current_idx
                    full_text += clean_part
                    end = current_idx + len(clean_part)
                    style_requests.append({'startIndex': start, 'endIndex': end, 'bold': True})
                    current_idx = end
                else:
                    start = current_idx
                    full_text += part
                    end = current_idx + len(part)
                    if is_static_bold:
                        style_requests.append({'startIndex': start, 'endIndex': end, 'bold': True})
                    current_idx = end
            
            if is_h1:
                # Approximate H1 range
                style_requests.append({'startIndex': current_idx - len(text), 'endIndex': current_idx, 'h1': True})

        requests = []
        # 1. Insert Text
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': full_text
            }
        })
        # 2. Apply Formatting
        for style in style_requests:
            if style.get('bold'):
                requests.append({
                    'updateTextStyle': {
                        'range': {'startIndex': style['startIndex'], 'endIndex': style['endIndex']},
                        'textStyle': {'bold': True},
                        'fields': 'bold'
                    }
                })
            if style.get('h1'):
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': style['startIndex'], 'endIndex': style['endIndex']},
                        'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                        'fields': 'namedStyleType'
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
