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

def debug_granular():
    print("="*60)
    print("GOOGLE API GRANULAR DEBUG")
    print("="*60)

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"✗ File {CREDENTIALS_FILE} not found!")
        return

    # 1. Load Credentials
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        print(f"✓ Loaded credentials from {CREDENTIALS_FILE}")
        print(f"  - Service Account Email: {creds.service_account_email}")
        print(f"  - Project ID: {creds.project_id}")
    except Exception as e:
        print(f"✗ Failed to load credentials: {e}")
        return

    # 2. Check Drive API identity (Who am I?)
    try:
        service = build('drive', 'v3', credentials=creds)
        about = service.about().get(fields="user,storageQuota").execute()
        user = about.get('user', {})
        print("\n[Drive API Identity Check]")
        print(f"  - Authenticated as: {user.get('emailAddress')}")
        print(f"  - Display Name: {user.get('displayName')}")
    except HttpError as e:
        print(f"✗ Drive API 'about' check failed: {e}")
    
    # 3. Test File Creation (Drive API)
    print("\n[Test 1: Create Text File via Drive API]")
    try:
        file_metadata = {'name': 'Debug Test File.txt'}
        media_body = 'Hello World'
        # Note: We are NOT putting it in a folder yet to rule out folder permissions
        file = service.files().create(
            body=file_metadata, 
            fields='id'
        ).execute()
        print(f"✓ Success! File ID: {file.get('id')}")
        
        # Clean up
        service.files().delete(fileId=file.get('id')).execute()
        print("  (Cleaned up test file)")
    except HttpError as e:
        print(f"✗ Drive Create Failed: {e}")

    # 4. Test Sheets Create (Sheets API)
    print("\n[Test 2: Create Sheet via Sheets API]")
    try:
        sheets_service = build('sheets', 'v4', credentials=creds)
        spreadsheet = {'properties': {'title': 'Debug Sheet Test'}}
        ss = sheets_service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId'
        ).execute()
        print(f"✓ Success! Spreadsheet ID: {ss.get('spreadsheetId')}")
        
        # Clean up
        service.files().delete(fileId=ss.get('spreadsheetId')).execute()
        print("  (Cleaned up test sheet)")
    except HttpError as e:
        print(f"✗ Sheets Create Failed: {e}")
        print("  Possible causes:")
        print("  - Google Sheets API is not enabled on console.cloud.google.com")
        print("  - Service Account does not have correct scopes (checked: OK)")

    # 5. Test Docs Create (Docs API)
    print("\n[Test 3: Create Doc via Docs API]")
    try:
        docs_service = build('docs', 'v1', credentials=creds)
        doc = docs_service.documents().create(body={'title': 'Debug Doc Test'}).execute()
        print(f"✓ Success! Doc ID: {doc.get('documentId')}")
        
        # Clean up
        service.files().delete(fileId=doc.get('documentId')).execute()
        print("  (Cleaned up test doc)")
    except HttpError as e:
        print(f"✗ Docs Create Failed: {e}")
        print("  Possible causes:")
        print("  - Google Docs API is not enabled on console.cloud.google.com")

if __name__ == "__main__":
    debug_granular()
