"""
Google Sheets Importer Module
Reads a Campaign Plan back from a Google Sheet to allow User Review syncing.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Reuse scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

DEFAULT_CREDENTIALS_PATH = Path(__file__).parent.parent.parent / "google_credentials.json"

class GoogleSheetsImporter:
    """Imports campaign plans from Google Sheets."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            str(DEFAULT_CREDENTIALS_PATH)
        )
        self.sheets_service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google APIs."""
        try:
            creds = None
            token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            elif os.path.exists(self.credentials_path):
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=SCOPES
                )
            else:
                raise FileNotFoundError("No valid credentials found.")
            
            self.sheets_service = build('sheets', 'v4', credentials=creds)
                
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google: {e}")

    def import_plan(self, sheet_url: str) -> Dict[str, Any]:
        """
        Reads the Google Sheet and returns a partial Plan dictionary
        containing the USER-EDITABLE fields.
        """
        spreadsheet_id = self._extract_id_from_url(sheet_url)
        print(f"[Importer] Reading Sheet ID: {spreadsheet_id}")
        
        # Read the entire first sheet
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1:Z500" # Read ample range
        ).execute()
        
        rows = result.get('values', [])
        if not rows:
            raise ValueError("Sheet is empty.")
            
        return self._parse_rows(rows)

    def _extract_id_from_url(self, url: str) -> str:
        # https://docs.google.com/spreadsheets/d/ID/edit...
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        raise ValueError(f"Invalid Google Sheet URL: {url}")

    def _parse_rows(self, rows: List[List[str]]) -> Dict[str, Any]:
        """
        Parses the raw rows into a clean dictionary structure.
        """
        # 1. Parse Overview (Rows 0-9 approx)
        # We look for Key-Value pairs in Column A and B
        overview = {}
        header_row_index = -1
        
        for i, row in enumerate(rows):
            if not row: continue
            
            # Check for header row to stop overview parsing
            if "Slot #" in row:
                header_row_index = i
                break
            
            if len(row) >= 2:
                key = row[0].strip().replace(":", "")
                val = row[1].strip()
                if key:
                    overview[key] = val
        
        # 2. Parse Email Slots
        if header_row_index == -1:
            raise ValueError("Could not find 'Slot #' header row.")
            
        headers = rows[header_row_index]
        # Map header name to index
        header_map = {h.strip(): i for i, h in enumerate(headers)}
        
        email_slots = []
        for i in range(header_row_index + 1, len(rows)):
            row = rows[i]
            if not row or not row[0]: continue # Empty slot number
            
            # Safe get with cleanup
            def get_col(name):
                idx = header_map.get(name)
                if idx is not None and idx < len(row):
                    val = row[idx].strip()
                    if val == "None" or val == "":
                        return None
                    return val
                return None

            slot_data = {
                "slot_number": int(get_col("Slot #") or 0), # Fallback for int
                "theme": get_col("Theme"),
                "email_purpose": get_col("Purpose"),
                "intensity_level": get_col("Intensity"),
                "transformation_description": get_col("Transformation"),
                "angle_description": get_col("Angle"),
                "structure_id": get_col("Structure"),
                "persona_description": get_col("Persona"),
                "key_message": get_col("Key Message"),
                "offer_details": get_col("Offer Details"),
                "offer_placement": get_col("Placement"),
                "cta_description": get_col("CTA")
            }
            email_slots.append(slot_data)
            
        return {
            "campaign_id": overview.get("Campaign ID"),
            "campaign_name": overview.get("Campaign Name"),
            "email_slots": email_slots
        }

def import_plan_from_sheet(sheet_url: str) -> Dict[str, Any]:
    importer = GoogleSheetsImporter()
    return importer.import_plan(sheet_url)
