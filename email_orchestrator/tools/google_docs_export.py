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
from email_orchestrator.tools.html_to_docs_parser import HtmlToDocsParser

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
            subject = email_draft.get('subject', 'Untitled Email').strip()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            doc_title = f"{brand_name} - {subject} - {timestamp}"
            
            # Create empty document
            doc = self.docs_service.documents().create(
                body={'title': doc_title}
            ).execute()
            
            document_id = doc.get('documentId')
            print(f"[GoogleDocs] Created document: {doc_title}")
            
            # --- EXECUTE CONTENT ---
            write_email_to_doc(self.docs_service, document_id, email_draft, structure_name, language)
            
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

# --- REUSABLE WRITER FUNCTION ---
def write_email_to_doc(docs_service, document_id: str, email_draft: Dict[str, Any], structure_name: str, language: str, header_text: Optional[str] = None):
    """
    Writes formatted email content (with HTML tables/lists) to the end of a Google Doc.
    Reusable by Exporter and Compiler.
    Uses aggressive flushing (Fetch-Insert-Fetch) to ensure perfect index tracking.
    """
    parser = HtmlToDocsParser()
    requests_queue = []
    
    # 1. Get Initial End Index
    doc = docs_service.documents().get(documentId=document_id).execute()
    curr_doc_end_index = doc.get('body').get('content')[-1].get('endIndex') - 1
    
    def flush_and_refresh():
        nonlocal requests_queue
        nonlocal curr_doc_end_index
        if requests_queue:
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests_queue}
            ).execute()
            requests_queue = []
        
        # Always refresh index to be safe
        doc = docs_service.documents().get(documentId=document_id).execute()
        curr_doc_end_index = doc.get('body').get('content')[-1].get('endIndex') - 1

    # Helper: Add Text Block (Auto-Flushes)
    def add_text_block(text: str, bold: bool = False, h1: bool = False, bullets: bool = False, styles_override: List[Dict] = None):
        """
        Inserts a block of text and applies styles.
        styles_override: List of {'start': int (relative), 'end': int, 'bold': bool} for mixed styling.
        """
        nonlocal curr_doc_end_index
        if not text: return
        
        # 1. Insert
        requests_queue.append({
            'insertText': {
                'location': {'index': curr_doc_end_index},
                'text': text
            }
        })
        
        start = curr_doc_end_index
        end = start + len(text)
        
        # 2. Styling (Base)
        if styles_override:
            # 2a. SAFE RESET: Force 'Normal' style first to prevent inheritance
            # This ensures "bold" from previous block doesn't bleed in.
            requests_queue.append({
                'updateTextStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'textStyle': {'bold': False, 'italic': False, 'underline': False},
                    'fields': 'bold,italic,underline'
                }
            })
            
            # 2b. Apply mixed styles
            for s in styles_override:
                # relative to start
                s_start = start + s.get('start', 0)
                s_end = start + s.get('end', 0)
                
                style_type = s.get('type', 'bold') # Default to bold for back-compat
                
                if style_type == 'bold' or s.get('bold'): # Handle legacy dict key 'bold': True
                    requests_queue.append({
                        'updateTextStyle': {
                            'range': {'startIndex': s_start, 'endIndex': s_end},
                            'textStyle': {'bold': True},
                            'fields': 'bold'
                        }
                    })
                elif style_type == 'italic':
                     requests_queue.append({
                        'updateTextStyle': {
                            'range': {'startIndex': s_start, 'endIndex': s_end},
                            'textStyle': {'italic': True},
                            'fields': 'italic'
                        }
                    })
                elif style_type == 'underline':
                     requests_queue.append({
                        'updateTextStyle': {
                            'range': {'startIndex': s_start, 'endIndex': s_end},
                            'textStyle': {'underline': True},
                            'fields': 'underline'
                        }
                    })
        else:
            # Apply uniform style (Explicit reset)
            text_style_mask = {'bold': True} if bold else {'bold': False}
            requests_queue.append({
                'updateTextStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'textStyle': text_style_mask,
                    'fields': 'bold'
                }
            })

        if h1:
            requests_queue.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'
                }
            })
            
        if bullets:
             requests_queue.append({
                'createParagraphBullets': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                }
            })
        
        # 3. Synchronize
        flush_and_refresh()

    # --- CONTENT CONSTRUCTION ---
    if header_text:
        add_text_block(f"{header_text}\n", h1=True)
        add_text_block("##########\n\n")

    add_text_block(f"SUBJECT: {email_draft.get('subject', '')}\n", bold=True)
    add_text_block(f"PREVIEW: {email_draft.get('preview', '')}\n", bold=False)
    add_text_block("##########\n\n")
    add_text_block(f"LANGUAGE: {language.upper()}\n\n")
    
    add_text_block("Hero Banner Title : ", bold=True)
    add_text_block(f"{email_draft.get('hero_title', '')}\n")
    add_text_block("Hero Banner Subtitle : ", bold=True)
    add_text_block(f"{email_draft.get('hero_subtitle', '')}\n")
    add_text_block("CTA : ", bold=True)
    add_text_block(f"{email_draft.get('cta_hero', '')}\n\n")
    
    add_text_block("Descriptive Block Title : ", bold=True)
    add_text_block(f"{email_draft.get('descriptive_block_title', '')}\n")
    add_text_block("Sub-title : ", bold=True)
    add_text_block(f"{email_draft.get('descriptive_block_subtitle', '')}\n\n")
    
    add_text_block(f"[[{structure_name}]]\n")
    
    # HTML BLOCK
    html_content = email_draft.get('descriptive_block_content', '')
    ops = parser.parse_to_ops(html_content)
    
    for op in ops:
        if op['type'] == 'text':
            # Use add_text_block with complex styles
            data = op['data']
            add_text_block(data['text'], styles_override=data['styles'])
            
        elif op['type'] == 'list':
            # Construct full list text
            full_list_text = ""
            combined_styles = []
            
            for item_data in op['items']:
                # The text for this item
                txt = item_data['text'] + "\n"
                
                # Adjust styles for this chunk to be relative to the full block start
                offset = len(full_list_text)
                for s in item_data['styles']:
                    combined_styles.append({
                        'start': offset + s['start'],
                        'end': offset + s['end'],
                        'bold': True
                    })
                
                full_list_text += txt
            
            add_text_block(full_list_text, bullets=True, styles_override=combined_styles)
            
        elif op['type'] == 'table':
            # TABLE HANDLING
            insert_idx = curr_doc_end_index
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': [{
                    'insertTable': {
                        'rows': op['rows'],
                        'columns': op['columns'],
                        'location': {'index': insert_idx}
                    }
                }]}
            ).execute()
            
            # Refresh to find table
            flush_and_refresh() # This updates curr_doc_end_index, but we need to find the table element
            
            # Logic to find table (heuristic: last structure with table)
            doc = docs_service.documents().get(documentId=document_id).execute()
            body_content = doc.get('body', {}).get('content', [])
            validation_table = None
            for element in reversed(body_content):
                if 'table' in element and element['startIndex'] >= insert_idx:
                    validation_table = element['table']
                    break
            
            if validation_table:
                cell_requests = []
                rows = validation_table.get('tableRows', [])
                op_cells = op['cells']
                
                # Iterate in REVERSE to prevent index shifting issues during batch insertion
                # If we insert Text A (len 10) at Index 100, then Text B at Index 200...
                # If we do Index 200 first, it's at 200. Index 100 is still at 100.
                # If we do Index 100 first, Index 200 shifts to 210.
                
                # Use strict reversed iteration
                for r_idx in reversed(range(len(rows))):
                    if r_idx >= len(op_cells): continue
                    
                    row = rows[r_idx]
                    row_cells = row.get('tableCells', [])
                    op_row = op_cells[r_idx]
                    
                    for c_idx in reversed(range(len(row_cells))):
                        if c_idx >= len(op_row): continue
                        
                        cell = row_cells[c_idx]
                        
                        # Find insertion point in cell
                        cell_content_nodes = cell.get('content', [])
                        if not cell_content_nodes: continue
                        
                        cell_insert_index = cell_content_nodes[0].get('startIndex')
                        
                        cell_data = op_row[c_idx]
                        if not cell_data['text']: continue
                        
                        # 1. Style Text (Applied after insert in queue, but indices are relative)
                        # Actually, Insert shifts content.
                        # If we mix Insert and Style in one batch:
                        # Request N: Insert at X
                        # Request N+1: Style at Range [X, X+Len] (using pre-batch indices?? or post?)
                        # Docs API: "The index is relative to the document state at the start of the batch EXCEPT for insertions within the same batch which shift subsequent indices."
                        # Wait, "The indices are technically relative to start of batch, but insertions affect subsequent commands."
                        # Actually, safest is to calculate Style Range based on Insertion.
                        # And since we go Reverse, Insert at late index doesn't affect early index.
                        
                        # BUT! We insert at X. Then Style at [X, X+Len].
                        # In the SAME batch (cell_requests).
                        # Docs order in batch matters.
                        # We append [Insert, Style].
                        # Since we go Reverse Cells, we do Cell Z, then Cell Y.
                        # Cell Z Insert/Style doesn't affect Cell Y indices.
                        
                        text_len = len(cell_data['text'])
                        
                        # Insert
                        cell_requests.append({
                            'insertText': {
                                'location': {'index': cell_insert_index},
                                'text': cell_data['text']
                            }
                        })
                        
                        # Style (Must match the inserted text)
                        # Since we process this cell "first" in our queue (actually last in document), 
                        # subsequent requests (previous cells) won't be shifted by this one?
                        # Wait. requests in batch are executed in order.
                        # If we append Z, then Y.
                        # Execution:
                        # 1. Insert Z (at 200). Doc len += 5.
                        # 2. Style Z (at 200).
                        # 3. Insert Y (at 100). Valid? Yes, 100 is still 100.
                        # CORRECT using Reverse Iteration + Sequential Append.
                        
                        for s in cell_data['styles']:
                            # relative to cell_insert_index because we insert at START of cell
                            # Paragraph stub moves forward.
                            s_start = cell_insert_index + s.get('start', 0)
                            s_end = cell_insert_index + s.get('end', 0)
                            
                            style_type = s.get('type', 'bold')
                            
                            style_mask = {}
                            fields = ''
                            
                            if style_type == 'bold' or s.get('bold'):
                                style_mask = {'bold': True}
                                fields = 'bold'
                            elif style_type == 'italic':
                                style_mask = {'italic': True}
                                fields = 'italic'
                            elif style_type == 'underline':
                                style_mask = {'underline': True}
                                fields = 'underline'
                            
                            if fields:
                                cell_requests.append({
                                    'updateTextStyle': {
                                        'range': {'startIndex': s_start, 'endIndex': s_end},
                                        'textStyle': style_mask,
                                        'fields': fields
                                    }
                                })
                
                # Execute Cell Updates
                if cell_requests:
                    docs_service.documents().batchUpdate(documentId=document_id, body={'requests': cell_requests}).execute()
            
            # Final refresh after table
            flush_and_refresh()
    
    # Footer
    add_text_block("\n\n")
    add_text_block("Product Block: ", bold=True)
    add_text_block(f"{email_draft.get('product_block_title', '')}\n")
    products = email_draft.get('products', [])
    for prod in products:
         add_text_block(f"- {prod}\n")
    add_text_block(f"CTA: {email_draft.get('cta_product', '')}\n")
    add_text_block("="*30 + "\n\n")

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
