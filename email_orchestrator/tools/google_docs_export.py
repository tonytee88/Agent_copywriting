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
    virtual_cursor_index = curr_doc_end_index
    
    # State tracking to prevent style bleeding and overwrites
    is_at_start_of_paragraph = True
    
    def flush_and_refresh():
        nonlocal requests_queue
        nonlocal curr_doc_end_index
        nonlocal virtual_cursor_index
        if requests_queue:
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests_queue}
            ).execute()
            requests_queue = []
        
        # Always refresh index to be safe
        doc = docs_service.documents().get(documentId=document_id).execute()
        curr_doc_end_index = doc.get('body').get('content')[-1].get('endIndex') - 1
        virtual_cursor_index = curr_doc_end_index

    def get_utf16_len(s: str) -> int:
        """Returns length of string in UTF-16 code units (for Google Docs Indexing)"""
        return len(s.encode('utf-16-le')) // 2

    # Helper: Add Text Block (Auto-Flushes)
    def add_text_block(text: str, bold: bool = False, h1: bool = False, bullets: bool = False, styles_override: List[Dict] = None):
        """
        Inserts a block of text and applies styles using DYNAMIC indexing.
        """
        nonlocal virtual_cursor_index
        nonlocal is_at_start_of_paragraph
        
        if not text: return
        
        # 1. Insert at current virtual tip
        requests_queue.append({
            'insertText': {
                'location': {'index': virtual_cursor_index},
                'text': text
            }
        })
        
        start = virtual_cursor_index
        text_len_utf16 = get_utf16_len(text)
        end = start + text_len_utf16
        
        # UPDATE CURSOR immediately
        virtual_cursor_index += text_len_utf16
        
        # 2. Styling
        
        # 2a. PARAGRAPH STYLE (Structure)
        # Only apply if we are H1 OR if we are at the start of a paragraph (reset to Normal).
        # We do NOT apply Normal mid-paragraph because it wipes inline character styles (like Bold).
        if h1:
            requests_queue.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'
                }
            })
            # Heading implies we're setting a block.
            # Usually headings end with newline? The inputs usually have \n.
        else:
             if is_at_start_of_paragraph:
                # Explicitly reset to NORMAL_TEXT at the *start* of the paragraph
                # to prevent H1 bleed from previous line.
                requests_queue.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {'namedStyleType': 'NORMAL_TEXT'},
                        'fields': 'namedStyleType'
                    }
                })

        # 2b. TEXT STYLE (Emphasis)
        if styles_override:
            # Safe reset for this block
            requests_queue.append({
                'updateTextStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'textStyle': {'bold': False, 'italic': False, 'underline': False},
                    'fields': 'bold,italic,underline'
                }
            })
            
            # Apply mixed styles
            for s in styles_override:
                # relative to start of THIS block
                s_start = start + s.get('start', 0)
                s_end = start + s.get('end', 0)
                
                style_type = s.get('type', 'bold')
                
                if style_type == 'bold' or s.get('bold'):
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
            # Apply uniform style if requested
            text_style_mask = {
                'bold': True if bold else False,
                'italic': False,
                'underline': False
            }
            # Only apply if we actually need to set BOLD (or if we need to reset).
            # Actually, safe to validly apply 'text_style_mask' on top.
            requests_queue.append({
                'updateTextStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'textStyle': text_style_mask,
                    'fields': 'bold,italic,underline'
                }
            })
            
        if bullets:
             requests_queue.append({
                'createParagraphBullets': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                }
            })
        
        # 3. State Update
        # If text ends with newline, next block is start of paragraph.
        if text.endswith('\n'):
            is_at_start_of_paragraph = True
        else:
            is_at_start_of_paragraph = False
        
        # 4. Batch Control
        if len(requests_queue) >= 30:
            flush_and_refresh()
            import time
            time.sleep(1)

    # --- CONTENT CONSTRUCTION ---
    # Removed duplicate header/language block
    # (Logic is handled at the end of the function)

    # Helper: Process Ops (Shared for all rich text fields)
    def process_html_ops(ops):
        nonlocal curr_doc_end_index # Used in table logic
        
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
                            'bold': True # Default legacy
                        })
                        # Note: We rely on 'bold' key for bullets, but could expand
                    
                    full_list_text += txt
                
                add_text_block(full_list_text, bullets=True, styles_override=combined_styles)
                
            elif op['type'] == 'table':
                # TABLE HANDLING
                
                # IMPORTANT: Flush any pending text requests (which use virtual_cursor)
                # BEFORE inserting table. This ensures curr_doc_end_index is valid
                flush_and_refresh() 
                
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
                flush_and_refresh() 
                
                # Logic to find table (heuristic: last structure with table)
                doc = docs_service.documents().get(documentId=document_id).execute()
                body_content = doc.get('body', {}).get('content', [])
                validation_table = None
                
                # Improved Search: Find the LAST *EMPTY* table
                # We assume the newly created table is empty (cells just have \n)
                # while previous tables have content.
                
                def is_table_empty(t):
                    # Checks if a table is effectively empty (just newlines)
                    for row in t.get('tableRows', []):
                        for cell in row.get('tableCells', []):
                            content = cell.get('content', [])
                            for elem in content:
                                if 'paragraph' in elem:
                                    for elem2 in elem['paragraph'].get('elements', []):
                                        txt = elem2.get('textRun', {}).get('content', '')
                                        if txt.strip(): # If it has non-whitespace text
                                            return False
                    return True

                for element in reversed(body_content):
                    if 'table' in element:
                        potential_table = element['table']
                        if is_table_empty(potential_table):
                            validation_table = potential_table
                            break
                        # If not empty, it's likely an old table, keep searching (backward)
                        # Wait, reversed means we see Last (Newest) first.
                        # If the Newest is Empty, we take it.
                        # If the Newest is NOT Empty, then... we have a problem?
                        # No, if we just inserted a table, it SHOULD be the last one and it SHOULD be empty.
                        # If for some reason the API hasn't updated, we might not see it at all.
                        # If we see the *previous* table, it will NOT be empty.
                        # So this filter prevents selecting the previous table.
                
                if not validation_table:
                    print("[GoogleDocs] Warning: precise table target not found. Retrying fetch...")
                    import time
                    time.sleep(2)
                    doc = docs_service.documents().get(documentId=document_id).execute()
                    body_content = doc.get('body', {}).get('content', [])
                    for element in reversed(body_content):
                        if 'table' in element and is_table_empty(element['table']):
                            validation_table = element['table']
                            break
                
                if validation_table:
                    cell_requests = []
                    rows = validation_table.get('tableRows', [])
                    op_cells = op['cells']
                    
                    # Iterate in REVERSE to prevent index shifting issues during batch insertion
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
                            
                            text_len = len(cell_data['text'])
                            
                            # Insert
                            cell_requests.append({
                                'insertText': {
                                    'location': {'index': cell_insert_index},
                                    'text': cell_data['text']
                                }
                            })
                            
                            # Style (Must match the inserted text)
                            
                            # 0. SAFE RESET for Table Cell Content
                            cell_requests.append({
                                'updateTextStyle': {
                                    'range': {'startIndex': cell_insert_index, 'endIndex': cell_insert_index + text_len},
                                    'textStyle': {'bold': False, 'italic': False, 'underline': False},
                                    'fields': 'bold,italic,underline'
                                }
                            })
                            
                            
                            for s in cell_data['styles']:
                                # relative to cell_insert_index because we insert at START of cell
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

    def render_rich_field(text: str):
        """Safely renders text that might contain HTML tags (bold, etc.)"""
        if not text: return
        # Ensure newline if needed? add_text_block adds explicit newlines usually.
        # But parser strips them.
        # Let's clean it first.
        # Use parser.
        ops = parser.parse_to_ops(text)
        process_html_ops(ops)

    # --- CONTENT CONSTRUCTION ---
    if header_text:
        add_text_block(f"{header_text}\n", h1=True)
        add_text_block("##########\n\n")

    # Removed redundant LANGUAGE line
    # add_text_block(f"LANGUAGE: {language.upper()}\n\n")

    add_text_block("SUBJECT: ", bold=True)
    render_rich_field(f"{email_draft.get('subject', '')}")
    add_text_block("\n")
    
    add_text_block("PREVIEW: ", bold=True)
    render_rich_field(f"{email_draft.get('preview', '')}")
    add_text_block("\n")
    add_text_block("\n") # Just a spacer
    
    add_text_block("Hero Banner Title : ", bold=True)
    render_rich_field(f"{email_draft.get('hero_title', '')}")
    add_text_block("\n")
    
    add_text_block("Hero Banner Subtitle : ", bold=True)
    render_rich_field(f"{email_draft.get('hero_subtitle', '')}")
    add_text_block("\n")
    
    if email_draft.get('cta_hero'):
        add_text_block("CTA : ", bold=True)
        render_rich_field(f"{email_draft.get('cta_hero', '')}")
        add_text_block("\n\n")
    else:
        add_text_block("\n")
    
    add_text_block("Descriptive Block Title : ", bold=True)
    render_rich_field(f"{email_draft.get('descriptive_block_title', '')}")
    add_text_block("\n")
    
    add_text_block("Sub-title : ", bold=True)
    render_rich_field(f"{email_draft.get('descriptive_block_subtitle', '')}")
    add_text_block("\n\n")
    
    add_text_block(f"[[{structure_name}]]\n")
    
    # HTML BLOCK
    html_content = email_draft.get('descriptive_block_content', '')
    ops = parser.parse_to_ops(html_content)
    process_html_ops(ops)
    
    # NEW: Render Descriptive CTA Button (After HTML Block)
    cta_descriptive = email_draft.get('cta_descriptive')
    if cta_descriptive:
        add_text_block(f"\nCTA : ", bold=True)
        add_text_block(f"{cta_descriptive}\n")

    # Footer
    add_text_block("\n\n")
    add_text_block("Product Block: ", bold=True)
    add_text_block(f"{email_draft.get('product_block_title', '')}\n")
    products = email_draft.get('products', [])
    for prod in products:
         add_text_block(f"- {prod}\n")
    add_text_block("CTA: ", bold=True)
    add_text_block(f"{email_draft.get('cta_product', '')}\n")
    add_text_block("="*30 + "\n\n")

    # Final Flush of any remaining text
    flush_and_refresh()

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
