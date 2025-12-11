import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CREDENTIALS_FILE = 'google_credentials.json'

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents'
]

def test_workaround():
    print("="*60)
    print("TESTING WORKAROUND: Create via Drive, Edit via API")
    print("="*60)

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )

    # 1. Create Sheet via Drive API (MimeType)
    print("\n[Step 1: Create Sheet via Drive API]")
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': 'Workaround Test Sheet',
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        file = drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        spreadsheet_id = file.get('id')
        print(f"✓ Success! Spreadsheet ID: {spreadsheet_id}")
    except HttpError as e:
        print(f"✗ Drive Create Failed: {e}")
        return

    # 2. Try to Edit via Sheets API
    print("\n[Step 2: Write Data via Sheets API]")
    try:
        sheets_service = build('sheets', 'v4', credentials=creds)
        body = {
            'values': [['Workaround', 'Successful!']]
        }
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body=body
        ).execute()
        print("✓ Success! Data written to sheet.")
    except HttpError as e:
        print(f"✗ Sheets Write Failed: {e}")
        
    # Clean up
    try:
        drive_service.files().delete(fileId=spreadsheet_id).execute()
        print("  (Cleaned up test file)")
    except:
        pass

    # 3. Create Doc via Drive API
    print("\n[Step 3: Create Doc via Drive API]")
    try:
        file_metadata = {
            'name': 'Workaround Test Doc',
            'mimeType': 'application/vnd.google-apps.document'
        }
        file = drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        doc_id = file.get('id')
        print(f"✓ Success! Doc ID: {doc_id}")
    except HttpError as e:
        print(f"✗ Drive Doc Create Failed: {e}")
        return

    # 4. Try to Edit via Docs API
    print("\n[Step 4: Write Data via Docs API]")
    try:
        docs_service = build('docs', 'v1', credentials=creds)
        requests = [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': 'Workaround Successful!'
                }
            }
        ]
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        print("✓ Success! Data written to doc.")
    except HttpError as e:
        print(f"✗ Docs Write Failed: {e}")
        
    # Clean up
    try:
        drive_service.files().delete(fileId=doc_id).execute()
        print("  (Cleaned up test file)")
    except:
        pass

if __name__ == "__main__":
    test_workaround()
