"""
Google Docs Export Module for Email Drafts

Requirements:
1. Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
2. Set up credentials (see GOOGLE_SETUP.md)
3. Add credentials file to project root or set GOOGLE_APPLICATION_CREDENTIALS env var
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes required
# Scopes required
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents'
]

# Credentials file path (can be overridden by env var)
DEFAULT_CREDENTIALS_PATH = Path(__file__).parent.parent.parent / "google_credentials.json"

class GoogleDocsExporter:
    """
    Exports email drafts to Google Docs with proper formatting.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Docs exporter.
        
        Args:
            credentials_path: Path to service account JSON or OAuth credentials
        """
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            str(DEFAULT_CREDENTIALS_PATH)
        )
        
        self.docs_service = None
        self.drive_service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google APIs using OAuth token or Service Account."""
        try:
            # 1. Try OAuth 2.0 Token (User Auth)
            token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
            if os.path.exists(token_path):
                from google.oauth2.credentials import Credentials
                credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
                print(f"[GoogleDocs] ✓ Authenticated using User Token (OAuth)")
            
            # 2. Key File (Service Account)
            elif os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=SCOPES
                )
                print(f"[GoogleDocs] ✓ Authenticated using Service Account")
            
            else:
                raise FileNotFoundError(
                    f"No credentials found. Please run 'python3 setup_oauth.py' to login,\n"
                    f"or ensure 'google_credentials.json' (Service Account) exists."
                )
            
            # Build services
            self.docs_service = build('docs', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google: {e}")

    def _move_to_folder(self, file_id: str, folder_id: str):
        """Move file to specific Drive folder."""
        try:
            # Retrieve the existing parents to remove
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            previous_parents = ",".join(file.get('parents'))
            
            # Move the file by adding the new parent and removing the old one
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            print(f"[GoogleDocs] ✓ Moved to folder: {folder_id}")
        except HttpError as e:
            print(f"[GoogleDocs] Warning: Could not move to folder {folder_id}: {e}")
    
    def create_email_doc(
        self,
        email_draft: Dict[str, Any],
        brand_name: str,
        folder_id: Optional[str] = None,
        structure_name: str = "Unknown",
        language: str = "English"
    ) -> Dict[str, str]:
        """
        Create a Google Doc with the email draft.
        
        Args:
            email_draft: EmailDraft dict with all email components
            brand_name: Brand name for the document title
            folder_id: Optional Google Drive folder ID to save in
        
        Returns:
            Dict with document_id and document_url
        """
        try:
            # Create document title
            subject = email_draft.get('subject', 'Untitled Email')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            doc_title = f"{brand_name} - {subject} - {timestamp}"
            
            # Create empty document
            doc = self.docs_service.documents().create(
                body={'title': doc_title}
            ).execute()
            
            document_id = doc.get('documentId')
            print(f"[GoogleDocs] Created document: {doc_title}")
            
            # Build formatted content
            requests = self._build_email_content_requests(email_draft, structure_name, language)
            
            # Update document with content
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
                print(f"[GoogleDocs] ✓ Content added to document")
            
            # Move to folder if specified
            if folder_id:
                self._move_to_folder(document_id, folder_id)
            
            # Get shareable link
            doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
            
            return {
                'document_id': document_id,
                'document_url': doc_url,
                'title': doc_title
            }
            
        except HttpError as e:
            raise Exception(f"Google Docs API error: {e}")
    
    def _build_email_content_requests(
        self, 
        email_draft: Dict[str, Any],
        structure_name: str,
        language: str
    ) -> list:
        """
        Build Google Docs API requests to format the email content.
        
        Layout:
        H1: Email [Auto-numbered if possible, or just Email]
        
        LANGUAGE: [Language]
        Subject Line (Bold Title): [Text]
        Preview Text (Bold Title): [Text]
        
        Hero Banner Title (Bold): [Text]
        Hero Banner Subtitle (Bold): [Text]
        CTA: [Text]
        
        Descriptive Block Title (Bold): [Text]
        Sub-title (Bold): [Text]
        [[Structure Name]]
        
        [Content] is BODY
        
        CTA: [Text]
        
        Product Block Title (Bold): [Text]
        Product Block Subtitle (Bold): [Text]
        Images : 
        [Product Link]
        CTA: [Text]
        """
        requests = []
        index = 1
        
        def insert_text(text):
            nonlocal index
            req = {'insertText': {'location': {'index': index}, 'text': text}}
            index += len(text)
            return req

        def insert_paragraph_break():
            nonlocal index
            req = {'insertText': {'location': {'index': index}, 'text': "\n"}}
            index += 1
            return req
            
        def format_bold(start_index, end_index):
            return {
                'updateTextStyle': {
                    'range': {'startIndex': start_index, 'endIndex': end_index},
                    'textStyle': {'bold': True},
                    'fields': 'bold'
                }
            }
            
        def format_h1(start_index, end_index):
             return {
                'updateParagraphStyle': {
                    'range': {'startIndex': start_index, 'endIndex': end_index},
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'
                }
            }

        # We build the doc essentially in reverse order if we insert at index 1 always,
        # OR we track the index. Tracking index is safer for complex formatting.
        # But wait, batchUpdate executes in order. So we can just append text and formatting requests.
        # It's easier to build the whole text string first, insert it, then apply formatting ranges?
        # No, because calculating ranges on a moving target is hard.
        # The best way is to insert at the end? Docs API insert at 'end' via segment ID?
        # Actually, inserting at index 1 pushes everything down.
        # Let's try to build a list of (text, is_bold, is_h1) tuples and process them.
        
        content_items = []
        
        # Helper to add items
        def add(text, bold=False, h1=False):
            content_items.append({"text": text, "bold": bold, "h1": h1})
        def add_br():
            content_items.append({"text": "\n", "bold": False, "h1": False})

        # --- CONTENT CONSTRUCTION ---
        
        # H1: Email Title (We don't have the slot number here easily passing from tool? 
        # actually we don't. Let's just say "Email Draft" or use the subject as H1?)
        # User said "Email number should be H1". 
        # I'll rely on the caller or just "Email Draft" for now if slot missing.
        add("Email Draft", h1=True) 
        add_br()
        
        add("##########")
        add_br()
        add_br()
        
        add("LANGUAGE: ")
        add(language.upper())
        add_br()
        add_br()
        
        add("Subject Line : ", bold=True)
        add(email_draft.get('subject', ''))
        add_br()
        
        add("Preview Text : ", bold=True)
        add(email_draft.get('preview', ''))
        add_br()
        add_br()
        
        add("Hero Banner Title : ", bold=True)
        add(email_draft.get('hero_title', ''))
        add_br()
        
        add("Hero Banner Subtitle : ", bold=True)
        add(email_draft.get('hero_subtitle', ''))
        add_br()
        
        add("CTA : ", bold=True) # User requested "CTA (2-3 words)" label? No "CTA : "
        add(email_draft.get('cta_hero', ''))
        add_br() 
        add_br()
        
        add("Descriptive Block Title : ", bold=True)
        add(email_draft.get('descriptive_block_title', ''))
        add_br()

        add("Sub-title : ", bold=True)
        add(email_draft.get('descriptive_block_subtitle', ''))
        add_br()
        add_br()
        
        add(f"[[{structure_name}]]")
        add_br()
        
        # Body Content
        body_text = email_draft.get('descriptive_block_content', '')
        add(body_text)
        add_br()
        add_br()
        
        # Offer/VIP section often in body, handled by content generation.
        
        add("CTA : ", bold=True)
        # We don't have a specific secondary CTA field in schema? 
        # Typically body CTA is same as hero or product.
        # Let's use cta_hero for now or empty if not distinct.
        add(email_draft.get('cta_hero', '')) 
        add_br()
        add_br()
        
        add("Product Block Title : ", bold=True)
        add(email_draft.get('product_block_title', 'Shop the Collection')) 
        add_br()
        
        add("Product Block Subtitle : ", bold=True)
        add(email_draft.get('product_block_subtitle', ''))
        add_br()
        add_br()
        
        # Iterate products
        products = email_draft.get('products', [])
        # Fallback if list is empty but old content exists
        if not products and email_draft.get('product_block_content'):
             add(email_draft.get('product_block_content'))
             add_br()
        else:
             for i, prod in enumerate(products):
                 # Simple clean list 1 per line as requested
                 add(prod)
                 add_br()
        
        add("CTA : ", bold=True)
        add(email_draft.get('cta_product', ''))
        add_br()
        
        add("##########")
        add_br()

        # --- EXECUTE REQUESTS ---
        # We insert text in bulk? No, to bold specific ranges, we need to know indices.
        # Strategies:
        # 1. Insert all text at once, then apply style ranges.
        #    Detailed index calculation required.
        # 2. Insert piece by piece? Inefficient.
        # Let's go with 1.
        
        full_text = ""
        style_ranges = [] # list of (start, end, type)
        
        current_idx = 1
        
        for item in content_items:
            text = item['text']
            # Basic sanitization of $ and % if needed? User said "Use signs $ and %".
            # I assume content has them. 
            
            start = current_idx
            full_text += text
            end = current_idx + len(text)
            
            if item['bold']:
                style_ranges.append((start, end, 'bold'))
            if item['h1']:
                style_ranges.append((start, end, 'h1'))
            
            current_idx = end
            
        # 1. Insert all text
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': full_text
            }
        })
        
        # 2. Apply styles
        for start, end, style_type in style_ranges:
            if style_type == 'bold':
                requests.append(format_bold(start, end))
            elif style_type == 'h1':
                requests.append(format_h1(start, end))
                
        return requests
    
    def share_document(self, document_id: str, email: str, role: str = 'writer'):
        """
        Share document with a specific email address.
        
        Args:
            document_id: Google Doc ID
            email: Email address to share with
            role: 'reader', 'writer', or 'owner'
        """
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            self.drive_service.permissions().create(
                fileId=document_id,
                body=permission,
                fields='id'
            ).execute()
            
            print(f"[GoogleDocs] ✓ Shared with {email} as {role}")
            
        except HttpError as e:
            print(f"[GoogleDocs] Warning: Could not share document: {e}")


# Convenience function
def export_email_to_google_docs(
    email_draft: Dict[str, Any],
    brand_name: str,
    folder_id: Optional[str] = None,
    share_with: Optional[str] = None,
    structure_name: str = "Unknown Structure",
    language: str = "English"
) -> Dict[str, str]:
    """
    Export an email draft to Google Docs.
    
    Args:
        email_draft: EmailDraft dictionary
        brand_name: Brand name
        folder_id: Optional Google Drive folder ID
        share_with: Optional email address to share with
        structure_name: Name of the structure used
        language: Language of the email
    
    Returns:
        Dict with document_id and document_url
    """
    exporter = GoogleDocsExporter()
    # Note: create_email_doc needs update too
    # I'll update create_email_doc to take the new params and pass them
    
    # Wait, I can't easily change the class method signature in this replace block without changing the call inside create_email_doc.
    # The previous block didn't include create_email_doc.
    # I will override `create_email_doc` as well in this block to be safe and clean.
    
    return exporter.create_email_doc(email_draft, brand_name, folder_id, structure_name, language)

