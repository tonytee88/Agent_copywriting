"""
Google Docs Export Module for Email Drafts

Requirements:
1. Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
2. Set up credentials (see GOOGLE_SETUP.md)
3. Add credentials file to project root or set GOOGLE_APPLICATION_CREDENTIALS env var
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
        Parses <b>...</b> tags for inline bolding.
        """
        content_items = []
        
        def add(text, bold=False, h1=False):
            if not text: return
            content_items.append({"text": str(text), "bold": bold, "h1": h1})
        def add_br():
            content_items.append({"text": "\n", "bold": False, "h1": False})

        # --- CONTENT CONSTRUCTION ---
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
        add("CTA : ", bold=True)
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
        add(email_draft.get('descriptive_block_content', ''))
        add_br()
        add_br()
        add("CTA : ", bold=True)
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
        products = email_draft.get('products', [])
        if not products and email_draft.get('product_block_content'):
             add(email_draft.get('product_block_content'))
             add_br()
        else:
             for prod in products:
                 add(prod)
                 add_br()
        add("CTA : ", bold=True)
        add(email_draft.get('cta_product', ''))
        add_br()
        add("##########")
        add_br()

        # --- PARSE & EXECUTE ---
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
                
        return requests
    
    def share_document(self, document_id: str, email: str, role: str = 'writer'):
        """
        Share document with a specific email address.
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
    """
    exporter = GoogleDocsExporter()
    return exporter.create_email_doc(email_draft, brand_name, folder_id, structure_name, language)
