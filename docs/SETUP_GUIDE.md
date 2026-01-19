# JARVIS Setup Guide

This guide covers setting up all adapters for JARVIS.

## Current Status

After initial deployment, check status with:
```bash
ssh pi@10.0.0.7 "cd ~/jarvis && source ~/.local/bin/env && uv run jarvis status"
```

---

## 1. Garmin Connect

**Prerequisites:** Garmin account

**Steps:**

1. Add credentials to `.env`:
```bash
GARMIN_EMAIL=your.email@example.com
GARMIN_PASSWORD=your_password
```

2. Sync to Pi and test:
```bash
scp .env pi@10.0.0.7:~/jarvis/.env
ssh pi@10.0.0.7 "cd ~/jarvis && source ~/.local/bin/env && uv run jarvis status"
```

---

## 2. Home Assistant

**Prerequisites:** Home Assistant running on Pi 4

**Steps:**

1. Access Home Assistant at `http://10.0.0.223:8123`

2. Complete the onboarding wizard

3. Create a long-lived access token:
   - Click your profile (bottom left)
   - Go to "Security" tab
   - Scroll to "Long-Lived Access Tokens"
   - Click "Create Token" → name it "JARVIS"
   - Copy the token

4. Add to `.env`:
```bash
HOME_ASSISTANT_URL=http://10.0.0.223:8123
HOME_ASSISTANT_TOKEN=your_long_lived_token_here
```

5. Sync to Pi:
```bash
scp .env pi@10.0.0.7:~/jarvis/.env
```

---

## 3. Whoop

**Prerequisites:** Whoop account and device

**Steps:**

1. Get API credentials from Whoop Developer Portal:
   - Go to https://developer.whoop.com
   - Create an application
   - Note your Client ID and Client Secret

2. Install whoop library locally:
```bash
cd /Users/prakyath/developments/life_os
uv sync --extra whoop
```

3. Add initial credentials to `.env`:
```bash
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
WHOOP_REDIRECT_URI=http://localhost:8080/callback
```

4. Run OAuth flow (opens browser):
```bash
uv run python -c "
from whoopy import WhoopClient
client = WhoopClient.authorize(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    redirect_uri='http://localhost:8080/callback'
)
print('Access Token:', client.token['access_token'])
print('Refresh Token:', client.token['refresh_token'])
"
```

5. Copy the tokens to `.env`:
```bash
WHOOP_ACCESS_TOKEN=<access_token_from_output>
WHOOP_REFRESH_TOKEN=<refresh_token_from_output>
```

6. Sync to Pi:
```bash
scp .env pi@10.0.0.7:~/jarvis/.env
```

---

## 4. Google Calendar

**Prerequisites:** Google account

**Steps:**

1. Go to [Google Cloud Console](https://console.cloud.google.com)

2. Create a new project (or select existing):
   - Click project dropdown → New Project
   - Name: "JARVIS"

3. Enable the Google Calendar API:
   - Go to APIs & Services → Library
   - Search "Google Calendar API"
   - Click Enable

4. Configure OAuth consent screen:
   - APIs & Services → OAuth consent screen
   - User Type: External
   - Fill in app name: "JARVIS"
   - Add your email as test user

5. Create OAuth credentials:
   - APIs & Services → Credentials
   - Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Name: "JARVIS Desktop"
   - Download JSON

6. Save the credentials file:
```bash
mkdir -p ~/.config/jarvis
mv ~/Downloads/client_secret_*.json ~/.config/jarvis/google_credentials.json
```

7. Run OAuth flow (on Mac):
```bash
cd /Users/prakyath/developments/life_os
uv run python scripts/oauth_setup.py
```
This opens a browser for Google login and creates `~/.config/jarvis/google_token.json`

8. Copy credentials to Pi:
```bash
ssh pi@10.0.0.7 "mkdir -p ~/.config/jarvis"
scp ~/.config/jarvis/google_credentials.json pi@10.0.0.7:~/.config/jarvis/
scp ~/.config/jarvis/google_token.json pi@10.0.0.7:~/.config/jarvis/
```

9. Verify `.env` has correct paths:
```bash
GOOGLE_CREDENTIALS_FILE=~/.config/jarvis/google_credentials.json
GOOGLE_TOKEN_FILE=~/.config/jarvis/google_token.json
```

---

## 5. Outlook / Microsoft Calendar

**Prerequisites:** Microsoft account (personal or work)

**Steps:**

1. Go to [Azure Portal](https://portal.azure.com)

2. Navigate to Azure Active Directory → App registrations → New registration:
   - Name: "JARVIS"
   - Supported account types:
     - "Personal Microsoft accounts only" (for personal Outlook)
     - OR "Accounts in any organizational directory" (for work accounts)
   - Redirect URI: `http://localhost:8080/callback` (Web type)

3. After creation, note these values:
   - Application (client) ID → `MICROSOFT_CLIENT_ID`
   - Directory (tenant) ID → `MICROSOFT_TENANT_ID`
     - Use `common` for personal accounts

4. Create a client secret:
   - Certificates & secrets → New client secret
   - Description: "JARVIS"
   - Copy the Value (not the ID) → `MICROSOFT_CLIENT_SECRET`

5. Add API permissions:
   - API permissions → Add a permission → Microsoft Graph
   - Delegated permissions:
     - `Calendars.Read`
     - `Calendars.ReadWrite`
     - `User.Read`
   - Click "Grant admin consent" if available

6. Add to `.env`:
```bash
MICROSOFT_CLIENT_ID=your_application_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret_value
MICROSOFT_TENANT_ID=common
```

7. Sync to Pi:
```bash
scp .env pi@10.0.0.7:~/jarvis/.env
```

---

## 6. Obsidian (via Syncthing)

**Prerequisites:** Obsidian vault on your Mac with Obsidian Sync

**Steps:**

### On Mac:

1. Install Syncthing:
```bash
brew install syncthing
brew services start syncthing
```

2. Open Syncthing UI: http://localhost:8384

3. Note your Device ID (Actions → Show ID)

### On Pi 5:

1. Install Syncthing:
```bash
ssh pi@10.0.0.7
sudo apt update && sudo apt install -y syncthing
sudo systemctl enable --now syncthing@pi
```

2. Open Pi Syncthing UI: http://10.0.0.7:8384

3. Note the Pi's Device ID

### Connect the devices:

1. On Mac Syncthing UI:
   - Add Remote Device → paste Pi's Device ID
   - Name: "Pi 5"

2. On Pi Syncthing UI:
   - Add Remote Device → paste Mac's Device ID
   - Name: "Mac"

3. On Mac Syncthing UI:
   - Add Folder
   - Folder Path: `/path/to/your/obsidian/vault`
   - Share with: Pi 5

4. On Pi Syncthing UI:
   - Accept the incoming folder share
   - Set path to: `/home/pi/obsidian`

### Configure JARVIS:

1. Update `.env`:
```bash
OBSIDIAN_VAULT_PATH=/home/pi/obsidian
OBSIDIAN_DAILY_NOTES_FOLDER=Daily Notes
OBSIDIAN_DAILY_NOTE_FORMAT=%Y-%m-%d
```

2. Sync to Pi:
```bash
scp .env pi@10.0.0.7:~/jarvis/.env
```

---

## Complete .env Template

```bash
# =============================================================================
# GARMIN
# =============================================================================
GARMIN_EMAIL=your.email@example.com
GARMIN_PASSWORD=your_password

# =============================================================================
# WHOOP (OAuth)
# =============================================================================
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
WHOOP_REDIRECT_URI=http://localhost:8080/callback
WHOOP_ACCESS_TOKEN=
WHOOP_REFRESH_TOKEN=

# =============================================================================
# GOOGLE CALENDAR (OAuth)
# =============================================================================
GOOGLE_CREDENTIALS_FILE=~/.config/jarvis/google_credentials.json
GOOGLE_TOKEN_FILE=~/.config/jarvis/google_token.json

# =============================================================================
# MICROSOFT / OUTLOOK (OAuth)
# =============================================================================
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_TENANT_ID=common

# =============================================================================
# OBSIDIAN
# =============================================================================
OBSIDIAN_VAULT_PATH=/home/pi/obsidian
OBSIDIAN_DAILY_NOTES_FOLDER=Daily Notes
OBSIDIAN_DAILY_NOTE_FORMAT=%Y-%m-%d

# =============================================================================
# HOME ASSISTANT
# =============================================================================
HOME_ASSISTANT_URL=http://10.0.0.223:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token

# =============================================================================
# VOICE (Optional)
# =============================================================================
PICOVOICE_ACCESS_KEY=your_access_key
WAKE_WORD=jarvis
WHISPER_MODEL=base

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL=sqlite:///~/.local/share/jarvis/jarvis.db
REDIS_URL=redis://localhost:6379/0

# =============================================================================
# GENERAL
# =============================================================================
ENVIRONMENT=development
LOG_LEVEL=INFO
TIMEZONE=America/Los_Angeles

# =============================================================================
# RASPBERRY PI
# =============================================================================
PI5_HOST=10.0.0.7
PI5_USER=pi
PI4_HOST=10.0.0.223
PI4_USER=pi
```

---

## Verification

After setting up each service, verify with:

```bash
# Sync .env to Pi
scp .env pi@10.0.0.7:~/jarvis/.env

# Check status
ssh pi@10.0.0.7 "cd ~/jarvis && source ~/.local/bin/env && uv run jarvis status"
```

Expected output when all services are configured:
```
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Service         ┃ Status         ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Garmin          │ ✓ Connected    │
│ Whoop           │ ✓ Connected    │
│ Google Calendar │ ✓ Connected    │
│ Outlook         │ ✓ Connected    │
│ Obsidian        │ ✓ Connected    │
│ Home Assistant  │ ✓ Connected    │
└─────────────────┴────────────────┘
```

---

## Troubleshooting

### Garmin "401 Unauthorized"
- Double-check email/password
- Try logging into Garmin Connect website first
- Garmin may require 2FA - use app-specific password if available

### Home Assistant "Connection failed"
- Verify HA is running: `curl http://10.0.0.223:8123/api/`
- Check token is valid (not expired)
- Ensure URL uses IP, not hostname

### Google Calendar "Credentials not found"
- Verify files exist: `ls ~/.config/jarvis/`
- Re-run OAuth flow if token expired

### Obsidian "Vault not found"
- Check Syncthing is running: `systemctl status syncthing@pi`
- Verify path exists: `ls /home/pi/obsidian`
- Check Syncthing UI for sync status
