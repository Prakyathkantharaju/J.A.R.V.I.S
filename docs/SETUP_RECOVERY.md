# JARVIS Complete Setup & Recovery Guide

## Overview

This guide documents the complete JARVIS setup for disaster recovery. If the Pi goes down, follow these steps to restore everything.

## Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                           │
│  Web Dashboard │ CLI │ WhatsApp (Clawdbot) │ Voice (Future) │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                 Pi 5 (10.0.0.7) - Brain                      │
│  • JARVIS API Server (port 8000)                            │
│  • Clawd AI Agent (GPT-5.2 via OpenRouter)                  │
│  • Obsidian (Flatpak)                                       │
│  • Clawdbot Gateway (WhatsApp bridge)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                    DATA SOURCES                              │
│  Whoop │ Garmin │ Google Calendar │ Obsidian │ Home Assistant│
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                 Pi 4 (10.0.0.223) - Data                     │
│  • Home Assistant                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 1: Fresh Pi Setup

### 1.1 Prerequisites on Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Install Node.js 22 (for Clawdbot)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Flatpak (for Obsidian)
sudo apt install -y flatpak
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install Obsidian
flatpak install -y flathub md.obsidian.Obsidian
```

### 1.2 Clone Repository

```bash
cd ~
git clone git@github.com:Prakyathkantharaju/J.A.R.V.I.S.git life_os
cd life_os
```

### 1.3 Install Python Dependencies

```bash
uv sync --extra whoop
```

---

## Part 2: Configuration

### 2.1 Environment Variables

Create `~/life_os/.env`:

```bash
# General
ENVIRONMENT=production
LOG_LEVEL=INFO
TIMEZONE=America/New_York

# Garmin
GARMIN_EMAIL=your_email@gmail.com
GARMIN_PASSWORD=your_garmin_password

# Whoop (OAuth)
WHOOP_CLIENT_ID=68664ac0-a6b3-4f6b-904b-db5a8cf1c0bf
WHOOP_CLIENT_SECRET=your_whoop_client_secret
WHOOP_REDIRECT_URI=http://localhost:8080/callback
WHOOP_ACCESS_TOKEN=  # Will be auto-managed
WHOOP_REFRESH_TOKEN= # Will be auto-managed

# Google Calendar
GOOGLE_CREDENTIALS_FILE=~/.config/jarvis/google_credentials.json
GOOGLE_TOKEN_FILE=~/.config/jarvis/google_token.json

# Obsidian
OBSIDIAN_VAULT_PATH=/home/pi/Documents/all-notes-nopass
OBSIDIAN_DAILY_NOTES_FOLDER=Daily Notes
OBSIDIAN_DAILY_NOTE_FORMAT=%Y-%m-%d

# Home Assistant
HOME_ASSISTANT_URL=http://10.0.0.223:8123
HOME_ASSISTANT_TOKEN=your_ha_long_lived_token

# OpenRouter (for Clawd AI)
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key
OPENROUTER_MODEL=openai/gpt-5.2

# Anthropic (optional)
ANTHROPIC_API_KEY=your_anthropic_key
```

### 2.2 Whoop OAuth Setup (One-time)

```bash
# 1. Open this URL in browser:
https://api.prod.whoop.com/oauth/oauth2/auth?client_id=68664ac0-a6b3-4f6b-904b-db5a8cf1c0bf&redirect_uri=http://localhost:8080/callback&response_type=code&scope=read:recovery%20read:cycles%20read:sleep%20read:workout%20read:profile%20read:body_measurement%20offline&state=jarvis-life-os-auth

# 2. Authorize and copy the 'code' from redirect URL

# 3. Exchange code for tokens:
curl -s -X POST "https://api.prod.whoop.com/oauth/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=http://localhost:8080/callback" \
  -d "code=PASTE_CODE_HERE"

# 4. Save tokens to ~/.config/jarvis/whoop_tokens.json
mkdir -p ~/.config/jarvis
cat > ~/.config/jarvis/whoop_tokens.json << 'EOF'
{
  "access_token": "FROM_RESPONSE",
  "refresh_token": "FROM_RESPONSE",
  "expires_in": 3600
}
EOF
```

### 2.3 Google Calendar OAuth (One-time)

```bash
# 1. Create OAuth credentials at https://console.cloud.google.com
# 2. Download credentials.json to ~/.config/jarvis/google_credentials.json
# 3. Run:
uv run python scripts/oauth_setup.py google
```

---

## Part 3: Install Systemd Services

### 3.1 Run Setup Script

```bash
bash ~/life_os/scripts/setup_services.sh
```

This installs:
- `jarvis-api.service` - Web dashboard & API (port 8000)
- `whoop-refresh.timer` - Token refresh every 30 min
- `obsidian.service` - Obsidian app (user service)

### 3.2 Manual Service Installation (if script fails)

```bash
# Copy service files
sudo cp ~/life_os/deploy/systemd/jarvis-api.service /etc/systemd/system/
sudo cp ~/life_os/deploy/systemd/whoop-refresh.service /etc/systemd/system/
sudo cp ~/life_os/deploy/systemd/whoop-refresh.timer /etc/systemd/system/

# Obsidian (user service)
mkdir -p ~/.config/systemd/user
cp ~/life_os/deploy/systemd/obsidian.service ~/.config/systemd/user/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis-api.service
sudo systemctl enable --now whoop-refresh.timer
systemctl --user daemon-reload
systemctl --user enable obsidian.service
sudo loginctl enable-linger pi
```

### 3.3 Verify Services

```bash
# Check status
sudo systemctl status jarvis-api
sudo systemctl list-timers whoop-refresh.timer
systemctl --user status obsidian

# View logs
sudo journalctl -u jarvis-api -f
sudo journalctl -u whoop-refresh

# Test API
curl http://localhost:8000/api/health
```

---

## Part 4: WhatsApp Integration (Clawdbot)

### 4.1 Install Clawdbot

```bash
sudo npm install -g clawdbot@latest
```

### 4.2 Configure Clawdbot

```bash
# Run onboarding
clawdbot onboard --install-daemon

# Create config
mkdir -p ~/.clawdbot
cat > ~/.clawdbot/clawdbot.json << 'EOF'
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1YOURNUMBER"]
    }
  },
  "agent": {
    "type": "custom",
    "endpoint": "http://localhost:8000/api/chat"
  }
}
EOF
```

### 4.3 Pair WhatsApp

```bash
# This shows a QR code - scan with WhatsApp
clawdbot channels login
```

### 4.4 Create Chat API Endpoint

Add to JARVIS API (`src/jarvis/api.py`):

```python
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    from jarvis.clawd import run_clawd
    response = await run_clawd(request.message)
    return {"response": response}
```

### 4.5 Clawdbot Systemd Service

```bash
# Create service file
sudo cat > /etc/systemd/system/clawdbot.service << 'EOF'
[Unit]
Description=Clawdbot WhatsApp Gateway
After=network.target jarvis-api.service

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/clawdbot gateway
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now clawdbot.service
```

---

## Part 5: CLI Commands Reference

```bash
# Health & Status
jarvis status              # Check all adapter connections
jarvis health              # Show Whoop + Garmin data
jarvis briefing            # Daily briefing

# Calendar & Notes
jarvis calendar            # Show merged calendar
jarvis notes "query"       # Search Obsidian

# Clawd AI Chat
jarvis chat                # Interactive chat mode
jarvis chat "question"     # Single question
jarvis ask "question"      # Quick alias

# Server
jarvis serve               # Start web dashboard (port 8000)

# Home Control
jarvis home on light.living_room
jarvis speak "Hello world"
```

---

## Part 6: Troubleshooting

### Whoop Token Expired
```bash
# Check logs
sudo journalctl -u whoop-refresh --since "1 hour ago"

# Manual refresh
cd ~/life_os && uv run python scripts/refresh_whoop_token.py

# If refresh fails, re-authorize (see Part 2.2)
```

### API Not Responding
```bash
# Check if port in use
sudo fuser -k 8000/tcp

# Restart service
sudo systemctl restart jarvis-api

# Check logs
sudo journalctl -u jarvis-api -f
```

### Obsidian Not Starting
```bash
# Check if display available
echo $DISPLAY

# Manual start
flatpak run md.obsidian.Obsidian &
```

### Clawdbot WhatsApp Disconnected
```bash
# Re-pair
clawdbot channels login

# Check status
clawdbot status
```

---

## Part 7: Backup & Restore

### What to Backup
```bash
# Critical files
~/.config/jarvis/              # OAuth tokens
~/life_os/.env                 # Configuration
~/.clawdbot/                   # Clawdbot credentials
~/Documents/all-notes-nopass/  # Obsidian vault
```

### Backup Script
```bash
#!/bin/bash
BACKUP_DIR=~/backups/jarvis-$(date +%Y%m%d)
mkdir -p $BACKUP_DIR
cp -r ~/.config/jarvis $BACKUP_DIR/
cp ~/life_os/.env $BACKUP_DIR/
cp -r ~/.clawdbot $BACKUP_DIR/
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
echo "Backup saved to $BACKUP_DIR.tar.gz"
```

---

## Part 8: Quick Recovery Checklist

If Pi dies, on fresh Pi:

1. [ ] Install prerequisites (uv, node, flatpak)
2. [ ] Clone repo: `git clone git@github.com:Prakyathkantharaju/J.A.R.V.I.S.git life_os`
3. [ ] Install deps: `cd life_os && uv sync --extra whoop`
4. [ ] Restore `.env` from backup
5. [ ] Restore `~/.config/jarvis/` from backup
6. [ ] Run `bash scripts/setup_services.sh`
7. [ ] Install Obsidian: `flatpak install -y flathub md.obsidian.Obsidian`
8. [ ] Install Clawdbot: `sudo npm install -g clawdbot@latest`
9. [ ] Restore `~/.clawdbot/` from backup (or re-pair WhatsApp)
10. [ ] Verify: `curl http://localhost:8000/api/health`

---

## Verification

After setup, verify everything works:

```bash
# 1. API Health
curl http://localhost:8000/api/health | jq

# 2. Clawd Chat
jarvis ask "How did I sleep?"

# 3. Dashboard
# Open http://10.0.0.7:8000 in browser

# 4. WhatsApp
# Send message to your number, should get response

# 5. Services running
sudo systemctl status jarvis-api
sudo systemctl list-timers
systemctl --user status obsidian
```
