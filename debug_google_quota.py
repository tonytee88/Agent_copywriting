import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CREDENTIALS_FILE = 'google_credentials.json'
FOLDER_ID = "1pAK5hmb2Kvn2KUOwxXVfOptvfUqDGu4Y"

SCOPES = [
    'https://www.googleapis.com/auth/drive',  # Need full drive scope to empty trash? or drive.file is enough diff
    'https://www.googleapis.com/auth/drive.file'
]

def attempt_fix_quota():
    print("="*60)
    print("DEBUG: FIX QUOTA & CREATE IN FOLDER")
    print("="*60)

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    drive_service = build('drive', 'v3', credentials=creds)

    # 1. Check Quota
    try:
        about = drive_service.about().get(fields="storageQuota").execute()
        quota = about.get('storageQuota', {})
        print(f"Usage: {quota.get('usage')} / {quota.get('limit')}")
    except Exception as e:
        print(f"Could not check quota: {e}")

    # 2. Empty Trash
    print("\n[Step 1: Emptying Trash...]")
    try:
        drive_service.files().emptyTrash().execute()
        print("✓ Trash emptied.")
    except HttpError as e:
        print(f"✗ Could not empty trash: {e}")

    # 3. Create File INSIDE User Folder
    print(f"\n[Step 2: Create Sheet inside Folder {FOLDER_ID}]")
    try:
        file_metadata = {
            'name': 'Quota Test Sheet',
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [FOLDER_ID]
        }
        file = drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        print(f"✓ Success! Created file ID: {file.get('id')}")
    except HttpError as e:
        print(f"✗ Creation Failed: {e}")

if __name__ == "__main__":
    attempt_fix_quota()
