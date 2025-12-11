"""
Google Sheets Export Module for Campaign Plans

Requirements:
1. Google Sheets API enabled
2. Credentials with https://www.googleapis.com/auth/spreadsheets scope
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email_orchestrator.schemas import CampaignPlan, EmailSlot

# Credentials file path (can be overridden by env var)
DEFAULT_CREDENTIALS_PATH = Path(__file__).parent.parent.parent / "google_credentials.json"

class GoogleSheetsExporter:
    """
    Exports campaign plans to Google Sheets.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Sheets exporter.
        """
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            str(DEFAULT_CREDENTIALS_PATH)
        )
        
        self.SCOPES = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        self.sheets_service = None
        self.drive_service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google APIs using OAuth token or Service Account."""
        try:
            # 1. Try OAuth 2.0 Token (User Auth)
            token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
            if os.path.exists(token_path):
                from google.oauth2.credentials import Credentials
                credentials = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                print(f"[GoogleSheets] ✓ Authenticated using User Token (OAuth)")
            
            # 2. Key File (Service Account)
            elif os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=self.SCOPES
                )
                print(f"[GoogleSheets] ✓ Authenticated using Service Account")
            
            else:
                raise FileNotFoundError(
                    f"No credentials found. Please run 'python3 setup_oauth.py' to login,\n"
                    f"or ensure 'google_credentials.json' (Service Account) exists."
                )
            
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google: {e}")

    def create_campaign_sheet(
        self,
        campaign_plan: CampaignPlan,
        folder_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a spreadsheet for a campaign plan.
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            title = f"Campaign Plan: {campaign_plan.campaign_name} ({timestamp})"
            
            # Create spreadsheet
            spreadsheet = {'properties': {'title': title}}
            spreadsheet = self.sheets_service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            print(f"[GoogleSheets] Created spreadsheet: {title}")
            
            # Move to folder if requested
            if folder_id:
                self._move_to_folder(spreadsheet_id, folder_id)
            
            # Format and populate data
            self._write_campaign_data(spreadsheet_id, campaign_plan)
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            
            return {
                'spreadsheet_id': spreadsheet_id,
                'spreadsheet_url': sheet_url,
                'title': title
            }
            
        except HttpError as e:
            raise Exception(f"Google Sheets API error: {e}")

    def _write_campaign_data(self, spreadsheet_id: str, plan: CampaignPlan):
        """Write campaign data and apply formatting."""
        
        # 1. Prepare Overview Data
        overview_data = [
            ["CAMPAIGN SUMMARY", ""],
            ["Campaign Name", plan.campaign_name],
            ["Brand", plan.brand_name],
            ["Goal", plan.campaign_goal],
            ["Duration", plan.duration],
            ["Total Emails", str(plan.total_emails)],
            ["Status", plan.status],
            ["Promotional Balance", plan.promotional_balance],
            ["Narrative", plan.overarching_narrative],
            ["", ""]  # Spacer
        ]
        
        # 2. Prepare Emails Data
        # Headers
        headers = [
            "Slot #", "Send Date", "Theme", "Purpose", "Intensity",
            "Transformation", "Angle", "Structure", "Persona",
            "Key Message", "Offer Details", "Placement"
        ]
        
        email_rows = []
        for slot in plan.email_slots:
            row = [
                slot.slot_number,
                slot.send_date,
                slot.theme,
                slot.email_purpose,
                slot.intensity_level,
                slot.assigned_transformation,
                slot.assigned_angle,
                slot.assigned_structure,
                slot.assigned_persona,
                slot.key_message,
                slot.offer_details or "None",
                slot.offer_placement or "None"
            ]
            email_rows.append(row)
        
        all_values = overview_data + [headers] + email_rows
        
        # Write Data
        body = {
            'values': all_values
        }
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body=body
        ).execute()
        
        # Apply Formatting (Bold headers, column widths)
        self._format_sheet(spreadsheet_id, len(overview_data), len(email_rows))

    def _format_sheet(self, spreadsheet_id: str, overview_rows: int, email_rows: int):
        """Apply formatting to make it readable."""
        
        header_row_index = overview_rows  # 0-based index
        
        requests = [
            # 1. Bold Campaign Summary Title
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 2},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 12}}},
                    "fields": "userEnteredFormat(textFormat)"
                }
            },
            # 2. Bold Labels in Overview
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": overview_rows-1, "startColumnIndex": 0, "endColumnIndex": 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat(textFormat)"
                }
            },
            # 3. Format Header Row (Bold, Background Color, Wrapped text)
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
            # 4. Wrap text for all email rows
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": header_row_index + 1},
                    "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                    "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"
                }
            },
            # 5. Set Column Widths
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                    "properties": {"pixelSize": 50},  # Slot #
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
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 10},
                    "properties": {"pixelSize": 150},  # Content columns
                    "fields": "pixelSize"
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 9, "endIndex": 10},
                    "properties": {"pixelSize": 250},  # Key Message (Wider)
                    "fields": "pixelSize"
                }
            }
        ]
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    def _move_to_folder(self, file_id: str, folder_id: str):
        """Move file to specific folder."""
        # Reuse logic from Docs exporter or just reimplement
        try:
            file = self.drive_service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
        except Exception as e:
            print(f"[GoogleSheets] Warning: Could not move to folder: {e}")

    def share_sheet(self, spreadsheet_id: str, email: str, role: str = 'writer'):
        """Share spreadsheet with email."""
        try:
            self.drive_service.permissions().create(
                fileId=spreadsheet_id,
                body={'type': 'user', 'role': role, 'emailAddress': email},
                fields='id'
            ).execute()
            print(f"[GoogleSheets] Shared with {email}")
        except Exception as e:
            print(f"[GoogleSheets] Warning: Could not share: {e}")

def export_campaign_to_sheets(
    campaign_plan: CampaignPlan,
    folder_id: Optional[str] = None,
    share_with: Optional[str] = None
) -> Dict[str, str]:
    """Export campaign plan to Google Sheets."""
    exporter = GoogleSheetsExporter()
    result = exporter.create_campaign_sheet(campaign_plan, folder_id)
    if share_with:
        exporter.share_sheet(result['spreadsheet_id'], share_with)
    return result
