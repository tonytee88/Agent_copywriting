"""
Google Sheets Export Module for Campaign Plans
Uses native google-api-python-client for robustness.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Scopes required
# Scopes required
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents'
]

DEFAULT_CREDENTIALS_PATH = Path(__file__).parent.parent.parent / "google_credentials.json"

class GoogleSheetsExporter:
    """Exports campaign plans to Google Sheets using native API."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            str(DEFAULT_CREDENTIALS_PATH)
        )
        self.sheets_service = None
        self.drive_service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google APIs."""
        try:
            creds = None
            # 1. Try OAuth 2.0 Token (User Auth)
            token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                print(f"[GoogleSheets] ✓ Authenticated using User Token (OAuth)")
                
            # 2. Key File (Service Account)
            elif os.path.exists(self.credentials_path):
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=SCOPES
                )
                print(f"[GoogleSheets] ✓ Authenticated using Service Account")
            
            else:
                raise FileNotFoundError("No valid credentials found.")
            
            self.sheets_service = build('sheets', 'v4', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
                
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google: {e}")

    def export_plan(
        self,
        plan_data: Dict[str, Any],
        folder_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Creates a formatted Google Sheet for the campaign plan.
        """
    def _get_target_month(self, plan_data: Dict[str, Any]) -> str:
        """Derives the target month from duration or start_date."""
        try:
            # 1. Try explicit duration string (e.g. "January 2026")
            duration = plan_data.get('duration', '')
            if duration:
                # Naive check: if it contains a month name
                for month in ["January", "February", "March", "April", "May", "June", 
                              "July", "August", "September", "October", "November", "December"]:
                    if month.lower() in duration.lower():
                        return month
            
            # 2. Try start_date
            start_date = plan_data.get('start_date')
            if start_date:
                # Assuming YYYY-MM-DD
                dt = datetime.strptime(start_date, '%Y-%m-%d')
                return dt.strftime('%B')
                
        except Exception:
            pass
            
        # Fallback to current month
        return datetime.now().strftime('%B')

    def export_plan(
        self,
        plan_data: Dict[str, Any],
        folder_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Creates a formatted Google Sheet for the campaign plan.
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            # Handle possible missing keys gracefully
            c_name = plan_data.get('campaign_name', 'Untitled Campaign')
            brand_name = plan_data.get('brand_name', 'Brand')
            campaign_id = plan_data.get('campaign_id', 'UNKNOWN_ID')
            
            target_month = self._get_target_month(plan_data)
            
            # FILE NAMING: BRAND-MONTH-CAMPAIGN ID
            sheet_title = f"{brand_name}-{target_month}-{campaign_id}"
            
            # Create spreadsheet
            spreadsheet = {'properties': {'title': sheet_title}}
            spreadsheet = self.sheets_service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            
            # Move to folder if specified
            if folder_id:
                self._move_to_folder(spreadsheet_id, folder_id)
            
            # Populate Data
            self._write_campaign_data(spreadsheet_id, plan_data)
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            print(f"[GoogleSheets] Created sheet: {sheet_url}")
            
            return {
                'spreadsheet_id': spreadsheet_id,
                'spreadsheet_url': sheet_url
            }
            
        except Exception as e:
            raise Exception(f"Google Sheets Export Error: {e}")

    def _write_campaign_data(self, spreadsheet_id: str, plan: Dict[str, Any]):
        """Write campaign data and apply formatting."""
        
        def safe(key): return str(plan.get(key) or "")
        
        # 1. Prepare Overview Data
        overview_data = [
            ["CAMPAIGN SUMMARY", ""],
            ["Campaign ID", safe('campaign_id')], # Added ID for re-import
            ["Campaign Name", safe('campaign_name')],
            ["Brand", safe('brand_name')],
            ["Goal", safe('campaign_goal')],
            ["Duration", safe('duration')],
            ["Total Emails", str(plan.get('total_emails', 0))],
            ["Status", safe('status')],
            ["Promotional Balance", safe('promotional_balance')],
            ["Narrative", safe('overarching_narrative')],
            ["Campaign Context", safe('campaign_context')], # ADDED: Visibility for User
            ["", ""]  # Spacer
        ]

        
        # 2. Prepare Emails Data headers
        headers = [
            "Slot #", "Send Date", "Theme", "Purpose", "Intensity",
            "Transformation", "Angle", "Structure", "Persona",
            "Key Message", "Offer Details", "Placement", "CTA"
        ]
        
        email_rows = []
        for slot in plan.get('email_slots', []):
            def s_get(k): return str(slot.get(k) or "None")
            row = [
                str(slot.get('slot_number', '')),
                s_get('send_date'),
                s_get('theme'),
                s_get('email_purpose'),
                s_get('intensity_level'),
                s_get('transformation_description'),
                s_get('angle_description'),
                s_get('structure_id'),
                s_get('persona_description'),
                s_get('key_message'),
                s_get('offer_details'),
                s_get('offer_placement'),
                s_get('cta_description')
            ]
            email_rows.append(row)
        
        all_values = overview_data + [headers] + email_rows
        
        # Write Data
        body = {'values': all_values}
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body=body
        ).execute()
        
        # Format
        self._format_sheet(spreadsheet_id, len(overview_data), len(email_rows))

    def _format_sheet(self, spreadsheet_id: str, overview_rows: int, email_rows: int):
        """Apply formatting to make it readable."""
        header_row_index = overview_rows
        
        requests = [
            # Bold Campaign Summary Title
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 2},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 12}}},
                    "fields": "userEnteredFormat(textFormat)"
                }
            },
            # Bold Overview Labels
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": overview_rows-1, "startColumnIndex": 0, "endColumnIndex": 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat(textFormat)"
                }
            },
            # Format Table Header (Bold, Color, Wrap)
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": header_row_index, "endRowIndex": header_row_index + 1},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            "textFormat": {"bold": True},
                            "wrapStrategy": "WRAP"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)"
                }
            },
            # Wrap text for data rows
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": header_row_index + 1},
                    "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                    "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"
                }
            },
            # Set Column Widths (Approximation in pixels)
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                    "properties": {"pixelSize": 60},  # Slot #
                    "fields": "pixelSize"
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                    "properties": {"pixelSize": 100},  # Date
                    "fields": "pixelSize"
                }
            },
            {
                 "updateDimensionProperties": {
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 4}, # Theme, Purpose
                    "properties": {"pixelSize": 150},
                    "fields": "pixelSize"
                }
            },
             {
                 "updateDimensionProperties": {
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 9}, # IDs
                    "properties": {"pixelSize": 180},
                    "fields": "pixelSize"
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 9, "endIndex": 10},
                    "properties": {"pixelSize": 300},  # Key Message (Wide)
                    "fields": "pixelSize"
                }
            }
        ]
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    def _move_to_folder(self, file_id: str, folder_id: str):
        """Move file to specific folder using shared Drive service."""
        try:
            file = self.drive_service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            print(f"[GoogleSheets] ✓ Moved to folder: {folder_id}")
        except Exception as e:
            print(f"[GoogleSheets] Warning: Could not move to folder: {e}")

# Convenience function
def export_plan_to_google_sheets(
    plan_data: Dict[str, Any],
    folder_id: Optional[str] = None
) -> Dict[str, str]:
    exporter = GoogleSheetsExporter()
    return exporter.export_plan(plan_data, folder_id)
