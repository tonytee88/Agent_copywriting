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
    
    def create_email_doc(
        self,
        email_draft: Dict[str, Any],
        brand_name: str,
        folder_id: Optional[str] = None
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
            requests = self._build_email_content_requests(email_draft)
            
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
    
    def _build_email_content_requests(self, email_draft: Dict[str, Any]) -> list:
        """
        Build Google Docs API requests to format the email content.
        
        Returns:
            List of API requests for batchUpdate
        """
        requests = []
        
        # Build content text
        content_parts = []
        
        # Header
        content_parts.append("=" * 60)
        content_parts.append("EMAIL DRAFT")
        content_parts.append("=" * 60)
        content_parts.append("")
        
        # Subject Line
        content_parts.append("SUBJECT LINE")
        content_parts.append(email_draft.get('subject', 'N/A'))
        content_parts.append("")
        
        # Preview Text
        content_parts.append("PREVIEW TEXT")
        content_parts.append(email_draft.get('preview', 'N/A'))
        content_parts.append("")
        
        # Hero Section
        content_parts.append("=" * 60)
        content_parts.append("HERO SECTION")
        content_parts.append("=" * 60)
        content_parts.append("")
        content_parts.append(f"Title: {email_draft.get('hero_title', 'N/A')}")
        content_parts.append(f"Subtitle: {email_draft.get('hero_subtitle', 'N/A')}")
        content_parts.append(f"CTA: {email_draft.get('cta_hero', 'N/A')}")
        content_parts.append("")
        
        # Descriptive Block
        content_parts.append("=" * 60)
        content_parts.append("DESCRIPTIVE BLOCK")
        content_parts.append("=" * 60)
        content_parts.append("")
        content_parts.append(f"Title: {email_draft.get('descriptive_block_title', 'N/A')}")
        content_parts.append(f"Subtitle: {email_draft.get('descriptive_block_subtitle', 'N/A')}")
        content_parts.append("")
        content_parts.append("Content:")
        content_parts.append(email_draft.get('descriptive_block_content', 'N/A'))
        content_parts.append("")
        
        # Product Block (if present)
        if email_draft.get('product_block_title'):
            content_parts.append("=" * 60)
            content_parts.append("PRODUCT BLOCK")
            content_parts.append("=" * 60)
            content_parts.append("")
            content_parts.append(f"Title: {email_draft.get('product_block_title', 'N/A')}")
            content_parts.append(f"Subtitle: {email_draft.get('product_block_subtitle', 'N/A')}")
            content_parts.append(f"CTA: {email_draft.get('cta_product', 'N/A')}")
            content_parts.append("")
        
        # Story Block (if present)
        if email_draft.get('story_block_title'):
            content_parts.append("=" * 60)
            content_parts.append("STORY BLOCK")
            content_parts.append("=" * 60)
            content_parts.append("")
            content_parts.append(f"Title: {email_draft.get('story_block_title', 'N/A')}")
            content_parts.append(f"Subtitle: {email_draft.get('story_block_subtitle', 'N/A')}")
            content_parts.append(f"CTA: {email_draft.get('cta_story', 'N/A')}")
            content_parts.append("")
        
        # Full formatted text (if available)
        if email_draft.get('full_text_formatted'):
            content_parts.append("=" * 60)
            content_parts.append("FULL EMAIL (FORMATTED)")
            content_parts.append("=" * 60)
            content_parts.append("")
            content_parts.append(email_draft.get('full_text_formatted'))
        
        # Join all parts
        full_text = "\n".join(content_parts)
        
        # Insert text at beginning of document
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': full_text
            }
        })
        
        return requests
    
    def _move_to_folder(self, document_id: str, folder_id: str):
        """Move document to a specific Google Drive folder."""
        try:
            # Get current parents
            file = self.drive_service.files().get(
                fileId=document_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move to new folder
            self.drive_service.files().update(
                fileId=document_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            print(f"[GoogleDocs] ✓ Moved to folder: {folder_id}")
            
        except HttpError as e:
            print(f"[GoogleDocs] Warning: Could not move to folder: {e}")
    
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
    share_with: Optional[str] = None
) -> Dict[str, str]:
    """
    Export an email draft to Google Docs.
    
    Args:
        email_draft: EmailDraft dictionary
        brand_name: Brand name
        folder_id: Optional Google Drive folder ID
        share_with: Optional email address to share with
    
    Returns:
        Dict with document_id and document_url
    """
    exporter = GoogleDocsExporter()
    result = exporter.create_email_doc(email_draft, brand_name, folder_id)
    
    if share_with:
        exporter.share_document(result['document_id'], share_with)
    
    return result
