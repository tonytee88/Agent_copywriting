# Google API Setup Guide (OAuth 2.0 User Auth)

## Overview

We are using **OAuth 2.0 Client ID** (Desktop App) to authenticate as *YOU*.
This avoids Service Account quota limits and permission issues.

---

## Step 1: Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Select your project: `email-agents-480902` (or whichever you are using)
3. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
4. **Application Type:** Choose **Desktop app**
5. **Name:** `Email Orchestrator Desktop` (or default)
6. Click **CREATE**

---

## Step 2: Download Credentials

1. A popup will show "OAuth client created"
2. Click the **DOWNLOAD JSON** button
3. Save the file as **`credentials.json`** in your project root folder:
   `/Users/tonytran/Coding2025/Agent_copywriting/credentials.json`

   *(Note: The downloaded name is long like `client_secret_xxxx.json`. Rename it!)*

---

## Step 3: Configure Consent Screen (If First Time)

If you haven't set this up yet:
1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** (unless you have a G-Suite org) → Create
3. **App Name:** `Email Orchestrator`
4. **User Support Email:** Select yours
5. **Developer Contact Info:** Select yours
6. Click **Save and Continue**
7. **Scopes:** Add `.../auth/drive.file`, `.../auth/spreadsheets`, `.../auth/documents` (Optional but good practice)
8. **Test Users:** **CRITICAL!** Add your own email address here so you can login.
9. Save and Finish.

---

## Step 4: First Run

1. Run the test script:
   ```bash
   python3 test_oauth_setup.py
   ```
2. A browser window will open asking you to login.
3. **"Google hasn't verified this app"** warning is normal (since it's your own private app).
   - Click **Advanced** → **Go to Email Orchestrator (unsafe)**
4. Click **Continue** → **Allow**
5. Authentication is complete! A `token.json` file will be created.

ALL DONE! verification will now work automatically.
