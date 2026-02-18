# JARVIS - Implementation Plan

## Overview

JARVIS is a personal AI-powered operating system built using **Ralph-Claude-Code** for autonomous development and **OpenClaw** as the conversational interface. It integrates all your life data sources and provides intelligent assistance across multiple channels.

## Architecture (Ralph + OpenClaw)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                          │
│  OpenClaw (WhatsApp/Telegram/Slack/Voice/Web)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│              OPENCLAW + SKILLS LAYER                         │
│   JARVIS Skills: health, calendar, notes, home, training   │
│   Built-in: browser, camera, screen, notifications          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                    DATA ADAPTERS                             │
│  Whoop │ Garmin │ Google Cal │ Outlook │ Obsidian │ Home Asst│
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│              DATA LAYER (Pi 4)                               │
│   SQLite │ Redis (cache) │ Home Assistant                    │
└─────────────────────────────────────────────────────────────┘
```

## Ralph Project Structure

```
jarvis/
├── PROMPT.md                    # Ralph: Core development instructions
├── @fix_plan.md                 # Ralph: Prioritized task checklist
├── @AGENT.md                    # Ralph: Build/execution instructions
├── specs/                       # Technical specifications
│   ├── architecture.md
│   ├── adapters.md
│   └── skills.md
│
├── pyproject.toml
├── src/jarvis/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   │
│   ├── skills/                  # OpenClaw skills (TypeScript/Python)
│   │   ├── health.ts            # Whoop + Garmin queries
│   │   ├── calendar.ts          # Google + Outlook merged
│   │   ├── notes.ts             # Obsidian search
│   │   ├── training.ts          # Marathon/workout plans
│   │   ├── home.ts              # Home Assistant control
│   │   └── briefing.ts          # Daily summary skill
│   │
│   ├── adapters/                # Python data adapters
│   │   ├── base.py
│   │   ├── whoop.py
│   │   ├── garmin.py
│   │   ├── google_calendar.py
│   │   ├── outlook.py
│   │   ├── obsidian.py
│   │   └── home_assistant.py
│   │
│   └── db/
│       └── models.py
│
├── scripts/
│   ├── setup.sh                 # One-command setup
│   └── oauth_setup.py
│
└── deploy/
    ├── docker-compose.yml       # Full stack deployment
    └── pi/                      # Raspberry Pi configs
```

## Key Integration Points

### 1. Ralph for Development
```bash
# Initialize Ralph in this project
ralph-setup jarvis

# Run autonomous development loop
ralph --verbose
```

Ralph will use PROMPT.md to understand the project and @fix_plan.md to track tasks.

### 2. OpenClaw for Interface
```bash
# Install OpenClaw
npm install -g openclaw@latest
openclaw onboard --install-daemon

# Install JARVIS skills
openclaw skill install ./src/jarvis/skills/
```

OpenClaw provides the conversational interface via WhatsApp, Telegram, etc.

## Your Configuration

| Setting | Choice |
|---------|--------|
| **Obsidian Vault** | Local path |
| **Food Logging** | Daily notes `## Food` section |
| **Training Plan** | Calendar-linked markdown |
| **Home Assistant** | Docker on Pi 4 |
| **Location** | HA Companion App |
| **Speaker** | Bluetooth on Pi 5 |
| **Interface** | OpenClaw (WhatsApp/Telegram) |

## Implementation Timeline (2-3 Days)

### Day 1: Foundation + Core Adapters
**Morning:**
- [ ] Set up Ralph project structure (PROMPT.md, @fix_plan.md, @AGENT.md)
- [ ] Initialize Python project with uv
- [ ] Create base adapter interface
- [ ] Implement Whoop adapter (whoopy)
- [ ] Implement Garmin adapter (garmy)

**Afternoon:**
- [ ] Implement Google Calendar adapter
- [ ] Implement Outlook adapter (MSAL)
- [ ] Implement Obsidian adapter (local vault)
- [ ] Basic health aggregator (Whoop + Garmin)

**Evening:**
- [ ] Set up OpenClaw locally
- [ ] Create first skill: `health` (query sleep, recovery, HRV)
- [ ] Test via Telegram/WhatsApp

### Day 2: Full Integration
**Morning:**
- [ ] Implement Home Assistant adapter
- [ ] Create `calendar` skill (merged view)
- [ ] Create `notes` skill (Obsidian search)
- [ ] Create `training` skill (marathon plan)

**Afternoon:**
- [ ] Create `home` skill (device control)
- [ ] Create `briefing` skill (daily summary)
- [ ] Set up Home Assistant on Pi 4 (Docker)
- [ ] Configure HA Companion App for location

**Evening:**
- [ ] Pi 5 deployment (OpenClaw + skills)
- [ ] Bluetooth speaker setup
- [ ] End-to-end testing all skills

### Day 3: Polish + Voice
**Morning:**
- [ ] Voice input via OpenClaw (or Porcupine wake word)
- [ ] TTS output to Bluetooth speaker
- [ ] Autonomous routines (morning briefing cron)

**Afternoon:**
- [ ] Documentation
- [ ] Final testing
- [ ] Git push - ready to clone

## OpenClaw Skills to Build

| Skill | Command | Function |
|-------|---------|----------|
| `health` | "How did I sleep?" | Whoop/Garmin sleep, recovery, HRV |
| `calendar` | "What's my schedule?" | Merged Google + Outlook events |
| `notes` | "Search my notes for X" | Semantic search Obsidian |
| `training` | "What's my workout today?" | Marathon/workout plan |
| `home` | "Turn on lights" | Home Assistant control |
| `briefing` | "Morning briefing" | Full daily summary |
| `food` | "What did I eat yesterday?" | Parse Obsidian food logs |
| `location` | "Where am I?" | HA Companion location |

## Autonomous Routines (Cron via OpenClaw)

| Routine | Schedule | Action |
|---------|----------|--------|
| Morning Briefing | 6:30 AM | Push summary to phone + speak |
| Health Check | Every 2h | Alert if anomalies detected |
| Evening Reflection | 9:00 PM | Day summary + tomorrow preview |
| Data Sync | Every 15m | Refresh all adapters |

## Quick Start (After Implementation)

```bash
# Clone
git clone https://github.com/prakyath/life-os.git
cd life-os

# Setup Python environment
uv sync

# Configure secrets
cp .env.example .env
# Edit .env with API credentials

# Run OAuth setup for services
uv run python scripts/oauth_setup.py

# Install OpenClaw + JARVIS skills
npm install -g openclaw@latest
openclaw onboard
openclaw skill install ./src/jarvis/skills/

# Start (or use Docker)
docker-compose up -d

# Or run Ralph for continued development
ralph --verbose
```

## Hardware Deployment

| Device | Role | Services |
|--------|------|----------|
| **Pi 5** | Brain | OpenClaw daemon, Skills, Bluetooth audio |
| **Pi 4** | Data | Home Assistant, SQLite, Redis |

## Key Dependencies

```toml
# Python (pyproject.toml)
dependencies = [
    "whoopy",                    # Whoop API
    "garminconnect",             # Garmin API
    "google-api-python-client",  # Google Calendar
    "msal",                      # Microsoft Graph
    "homeassistant-api",         # Home Assistant
    "httpx",                     # Async HTTP
    "pydantic-settings",         # Config
    "apscheduler",               # Cron jobs
]
```

```json
// OpenClaw skills (package.json in skills/)
{
  "dependencies": {
    "@anthropic-ai/sdk": "latest"
  }
}
```

## References

- [Ralph-Claude-Code](https://github.com/frankbria/ralph-claude-code) - Autonomous development loop
- [OpenClaw](https://openclaw.ai/) - Personal AI agent
- [OpenClaw GitHub](https://github.com/openclaw/openclaw) - Source code
- [OpenClaw Docs](https://docs.openclaw.ai/) - Skills development
- [whoopy](https://pypi.org/project/whoopy/) - Whoop Python library
- [garminconnect](https://github.com/cyberjunky/python-garminconnect) - Garmin Python library
- [Home Assistant](https://www.home-assistant.io/) - Smart home hub

## Obsidian Formats

### Food (Daily Notes)
```markdown
## Food
- **Breakfast**: Oatmeal, coffee
- **Lunch**: Salad, chicken
- **Dinner**: Salmon, rice
```

### Training (Calendar-Linked)
```markdown
# Marathon Training Plan

## Week 5 (Jan 20-26)
| Day | Workout | Distance |
|-----|---------|----------|
| Mon | Easy Run | 5 km |
| Tue | Intervals | 8 km |
| Thu | Tempo | 10 km |
| Sat | Long Run | 18 km |
```
