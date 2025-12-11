import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file'
]

CREDENTIALS_FILE = 'google_credentials.json'

def diagnose():
    print("Diagnosis Start...")
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )

    # 1. Test Drive API (List files)
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        print("Attempting to list files (Drive API)...")
        results = drive_service.files().list(pageSize=1).execute()
        print("✓ Drive API working. File count:", len(results.get('files', [])))
    except HttpError as e:
        print(f"✗ Drive API Failed: {e}")

    # 2. Test Docs API (Create doc)
    try:
        docs_service = build('docs', 'v1', credentials=creds)
        print("Attempting to create doc (Docs API)...")
        doc = docs_service.documents().create(body={'title': 'Test Doc'}).execute()
        print(f"✓ Docs API working. Doc ID: {doc.get('documentId')}")
    except HttpError as e:
        print(f"✗ Docs API Failed: {e}")

if __name__ == "__main__":
    diagnose()
