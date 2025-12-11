"""
One-time OAuth 2.0 Setup Script.
Run this locally to login and generate 'token.json'.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes we need permissions for
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def setup_oauth():
    print("=" * 60)
    print("GOOGLE OAUTH SETUP")
    print("=" * 60)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"✗ File {CREDENTIALS_FILE} not found!")
        print("Please download your OAuth Desktop Client credentials from Google Cloud Console")
        print("and save them as 'credentials.json' in this directory.")
        return

    creds = None
    
    # Load existing token if valid
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                print("✓ Found valid existing token.json")
                return
        except Exception as e:
            print(f"Existing token invalid: {e}")

    # If no valid credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception:
                print("Refresh failed. Starting new login flow...")
                creds = None
        
        if not creds:
            print("Launching browser for login...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            
            # This will open a local browser
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        print(f"Saving new token to {TOKEN_FILE}...")
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    print("\n✓ AUTHENTICATION SUCCESSFUL!")
    print("You can now run the export tests.")

if __name__ == "__main__":
    setup_oauth()
