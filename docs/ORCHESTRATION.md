# JARVIS - Orchestration & Daily Flow

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JARVIS ORCHESTRATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ALWAYS RUNNING (24/7)                             │   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │  Clawdbot   │  │    Data     │  │    Home     │  │   Voice    │  │   │
│  │  │   Daemon    │  │    Sync     │  │  Assistant  │  │  Listener  │  │   │
│  │  │             │  │  Scheduler  │  │             │  │ (Porcupine)│  │   │
│  │  │ Listens to: │  │             │  │ Tracks:     │  │            │  │   │
│  │  │ - WhatsApp  │  │ Every 15m:  │  │ - Location  │  │ Waits for: │  │   │
│  │  │ - Telegram  │  │ - Whoop     │  │ - Devices   │  │ "Hey Life  │  │   │
│  │  │ - Slack     │  │ - Garmin    │  │ - Sensors   │  │    OS"     │  │   │
│  │  │ - Web       │  │ - Calendars │  │             │  │            │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## What Runs When?

### 1. Background Services (Always On)

| Service | Location | What It Does |
|---------|----------|--------------|
| **Clawdbot Daemon** | Pi 5 | Listens for messages on all channels |
| **Voice Listener** | Pi 5 | Waits for wake word via microphone |
| **Data Sync** | Pi 5 | Pulls API data every 15 minutes |
| **Home Assistant** | Pi 4 | Tracks location, manages devices |
| **SQLite/Redis** | Pi 4 | Stores data, caches API responses |

### 2. Scheduled Events (Cron/Timers)

| Time | Event | What Happens | Output |
|------|-------|--------------|--------|
| **6:30 AM** | Morning Briefing | Aggregates overnight data → generates summary | **Speaker announces** + push notification |
| **Every 2h** | Health Check | Analyzes HRV, recovery, strain | Alert to phone **only if anomaly** |
| **12:00 PM** | Midday Sync | Refresh calendars, check afternoon schedule | Silent (data only) |
| **6:00 PM** | Evening Prep | Check tomorrow's calendar, suggest prep | Push notification |
| **9:00 PM** | Evening Reflection | Summarize day, preview tomorrow | **Speaker announces** (optional) |
| **Every 15m** | Data Sync | Pull from Whoop, Garmin, Calendars | Silent (background) |

### 3. User-Triggered Events

| Trigger | How | What Happens | Output |
|---------|-----|--------------|--------|
| **Voice** | Say "Hey JARVIS" | Wake word detected → listens → processes → responds | **Speaker responds** |
| **WhatsApp** | Send message | Clawdbot receives → processes → responds | WhatsApp reply |
| **Telegram** | Send message | Clawdbot receives → processes → responds | Telegram reply |
| **Smart Home** | Motion/sensor | HA triggers automation → may notify JARVIS | Depends on automation |

---

## A Day in the Life (Detailed Timeline)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TYPICAL DAY TIMELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

 6:00 AM  ┌─────────────────────────────────────────────────────────────────┐
          │ [BACKGROUND] Data sync runs - pulls overnight Whoop sleep data  │
          └─────────────────────────────────────────────────────────────────┘

 6:30 AM  ┌─────────────────────────────────────────────────────────────────┐
          │ [SCHEDULED] ★ MORNING BRIEFING ★                                │
          │                                                                  │
          │ 1. System aggregates:                                           │
          │    - Whoop: Sleep score (85%), HRV (45ms), Recovery (78%)       │
          │    - Garmin: Resting HR, Body Battery                           │
          │    - Google Cal: Personal events today                          │
          │    - Outlook: Work meetings                                     │
          │    - Training Plan: Today's workout                             │
          │    - Weather: Current conditions                                │
          │                                                                  │
          │ 2. Claude generates natural language summary                    │
          │                                                                  │
          │ 3. OUTPUT:                                                      │
          │    🔊 SPEAKER: "Good morning! You slept 7 hours with 85%        │
          │       quality. Recovery is good at 78%. You have a 9 AM         │
          │       standup and a 2 PM design review. Today's training        │
          │       is an easy 5K run. Weather is 15°C and sunny."            │
          │    📱 PUSH: Summary card to phone                               │
          └─────────────────────────────────────────────────────────────────┘

 7:15 AM  ┌─────────────────────────────────────────────────────────────────┐
          │ [USER-TRIGGERED] Voice interaction                              │
          │                                                                  │
          │ You: "Hey JARVIS"                                              │
          │ 🎤 [Wake word detected - Porcupine activates]                   │
          │ 🔊 SPEAKER: *chime*                                             │
          │                                                                  │
          │ You: "What should I eat for breakfast given my workout?"        │
          │ 🎤 [Whisper STT transcribes]                                    │
          │                                                                  │
          │ [System processes]:                                             │
          │ - Checks training plan: Easy 5K run                             │
          │ - Checks recovery: 78% (good)                                   │
          │ - Queries food preferences from Obsidian                        │
          │                                                                  │
          │ 🔊 SPEAKER: "For an easy run day with good recovery, I'd        │
          │    suggest oatmeal with banana and a coffee. Light carbs        │
          │    will fuel your run without being heavy."                     │
          └─────────────────────────────────────────────────────────────────┘

 8:30 AM  ┌─────────────────────────────────────────────────────────────────┐
          │ [BACKGROUND] Health check runs (every 2 hours)                  │
          │                                                                  │
          │ - HRV: 45ms (normal for you)                                    │
          │ - No anomalies detected                                         │
          │ - OUTPUT: None (silent, all good)                               │
          └─────────────────────────────────────────────────────────────────┘

 9:00 AM  ┌─────────────────────────────────────────────────────────────────┐
          │ [LOCATION-TRIGGERED] You arrive at office                       │
          │                                                                  │
          │ HA Companion App detects location change → Home Assistant       │
          │                                                                  │
          │ [Optional automation]:                                          │
          │ - Turn off home lights                                          │
          │ - Arm security system                                           │
          │ - Log arrival time                                              │
          │                                                                  │
          │ OUTPUT: Silent (or optional push confirmation)                  │
          └─────────────────────────────────────────────────────────────────┘

10:30 AM  ┌─────────────────────────────────────────────────────────────────┐
          │ [USER-TRIGGERED] WhatsApp message                               │
          │                                                                  │
          │ You (WhatsApp): "What's my afternoon look like?"                │
          │                                                                  │
          │ [Clawdbot receives, processes]:                                 │
          │ - Checks Google Calendar                                        │
          │ - Checks Outlook Calendar                                       │
          │ - Merges and formats                                            │
          │                                                                  │
          │ 📱 WhatsApp Reply:                                              │
          │    "Your afternoon:                                             │
          │    • 2:00 PM - Design Review (Zoom, 1 hour)                     │
          │    • 4:00 PM - Free block                                       │
          │    • 5:30 PM - Easy 5K run (training plan)                      │
          │    • 7:00 PM - Dinner with Alex (personal)"                     │
          └─────────────────────────────────────────────────────────────────┘

10:30 AM  ┌─────────────────────────────────────────────────────────────────┐
          │ [BACKGROUND] Health check runs                                  │
          │                                                                  │
          │ - Detects: HRV dropped to 28ms (unusual)                        │
          │ - Strain accumulating faster than normal                        │
          │                                                                  │
          │ ⚠️ ANOMALY DETECTED                                             │
          │                                                                  │
          │ 📱 PUSH NOTIFICATION:                                           │
          │    "Health Alert: Your HRV dropped to 28ms (usually 45ms).      │
          │    Combined with rising strain, you might be fighting           │
          │    something. Consider taking it easy today."                   │
          │                                                                  │
          │ [Optional] 🔊 SPEAKER: Same message if at home                  │
          └─────────────────────────────────────────────────────────────────┘

12:30 PM  ┌─────────────────────────────────────────────────────────────────┐
          │ [USER-TRIGGERED] Telegram message                               │
          │                                                                  │
          │ You (Telegram): "Log lunch: chicken salad, sparkling water"     │
          │                                                                  │
          │ [System processes]:                                             │
          │ - Parses food items                                             │
          │ - Appends to today's Obsidian daily note under ## Food          │
          │                                                                  │
          │ 📱 Telegram Reply: "✓ Logged lunch to your daily note"          │
          └─────────────────────────────────────────────────────────────────┘

 5:30 PM  ┌─────────────────────────────────────────────────────────────────┐
          │ [LOCATION-TRIGGERED] You arrive home                            │
          │                                                                  │
          │ HA Companion detects home zone                                  │
          │                                                                  │
          │ [Automations trigger]:                                          │
          │ - Turn on living room lights                                    │
          │ - Set thermostat to preferred temp                              │
          │ - Disarm security                                               │
          │                                                                  │
          │ 🔊 SPEAKER: "Welcome home! Lights are on. Remember you have     │
          │    dinner with Alex at 7. Your easy 5K is ready when you are." │
          └─────────────────────────────────────────────────────────────────┘

 5:45 PM  ┌─────────────────────────────────────────────────────────────────┐
          │ [USER-TRIGGERED] Voice command                                  │
          │                                                                  │
          │ You: "Hey JARVIS, start my running playlist"                   │
          │                                                                  │
          │ [If Spotify integrated]:                                        │
          │ 🔊 SPEAKER: Starts playlist on connected speaker                │
          │                                                                  │
          │ You: "Hey JARVIS, I'm heading out for my run"                  │
          │ 🔊 SPEAKER: "Got it! I'll log your run when Garmin syncs.       │
          │    Have a good one!"                                            │
          └─────────────────────────────────────────────────────────────────┘

 9:00 PM  ┌─────────────────────────────────────────────────────────────────┐
          │ [SCHEDULED] ★ EVENING REFLECTION ★                              │
          │                                                                  │
          │ 1. System aggregates:                                           │
          │    - Completed activities (run logged via Garmin)               │
          │    - Food intake from Obsidian                                  │
          │    - Meetings attended                                          │
          │    - Tomorrow's schedule preview                                │
          │                                                                  │
          │ 2. Claude generates reflection                                  │
          │                                                                  │
          │ 3. OUTPUT:                                                      │
          │    📱 PUSH: Day summary card                                    │
          │    🔊 SPEAKER (optional, configurable):                         │
          │       "Good evening! Today you completed your 5K in 28 minutes. │
          │       You had 3 meetings and logged 3 meals. Tomorrow you have  │
          │       intervals scheduled - get good sleep! First meeting       │
          │       is at 10 AM."                                             │
          │                                                                  │
          │ 4. Writes daily summary to Obsidian daily note                  │
          └─────────────────────────────────────────────────────────────────┘

11:00 PM  ┌─────────────────────────────────────────────────────────────────┐
          │ [BACKGROUND] Overnight mode                                     │
          │                                                                  │
          │ - Data sync continues every 15 min                              │
          │ - Voice listener remains active (quieter chime)                 │
          │ - Health alerts still enabled but silent unless critical        │
          │ - Whoop tracks sleep automatically                              │
          └─────────────────────────────────────────────────────────────────┘
```

---

## Voice Flow (Detailed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VOICE INTERACTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │   MICROPHONE     │  (Always listening for wake word only)
    │   (Pi 5)         │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   PORCUPINE      │  Lightweight wake word detection
    │   Wake Word      │  "Hey JARVIS" (or custom)
    │   Engine         │  Runs locally, no cloud
    └────────┬─────────┘
             │
             │ Wake word detected!
             ▼
    ┌──────────────────┐
    │   🔊 CHIME       │  Audio feedback: "I'm listening"
    │   (Speaker)      │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   AUDIO CAPTURE  │  Records your question
    │   (pyaudio)      │  Stops on silence detection
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   WHISPER STT    │  Transcribes speech to text
    │   (Local)        │  "What's my recovery score?"
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   CLAWDBOT /     │  Routes to appropriate skill
    │   SKILL ROUTER   │  Determines: health skill needed
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   SKILL:         │  Queries Whoop adapter
    │   health.ts      │  Gets recovery: 78%
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   CLAUDE         │  Generates natural response
    │   (via Clawdbot) │  "Your recovery is 78%, which is good..."
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   PIPER TTS      │  Converts text to speech
    │   (Local)        │  Natural voice synthesis
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   🔊 SPEAKER     │  Speaks the response
    │   (Bluetooth)    │  "Your recovery is 78%..."
    └──────────────────┘

    Total latency: ~2-4 seconds (all local except Claude API)
```

---

## When Does the Speaker Trigger?

| Scenario | Speaker Output | Configurable? |
|----------|----------------|---------------|
| **Morning Briefing** (6:30 AM) | Full briefing spoken | Yes - can disable or change time |
| **Voice Wake Word** | Chime, then response | Always on if voice enabled |
| **Arriving Home** | Welcome message | Yes - can disable |
| **Health Alert** | Alert spoken | Yes - can be push-only |
| **Evening Reflection** | Summary spoken | Yes - can be push-only |
| **Smart Home Confirm** | "Lights on" etc. | Yes - can disable confirmations |
| **Timer/Reminder** | Reminder spoken | Yes - per reminder |

### Speaker Configuration

```yaml
# config/settings.yaml
speaker:
  enabled: true
  device: "bluetooth"  # or "3.5mm", "hdmi"

  # When to use speaker vs silent
  morning_briefing: "speak"      # speak | push | both | off
  evening_reflection: "push"     # quieter evening
  health_alerts: "both"          # important - both channels
  welcome_home: "speak"
  voice_responses: "speak"       # always speak voice responses
  smart_home_confirm: "off"      # silent confirmations

  # Quiet hours (speaker muted, push only)
  quiet_hours:
    enabled: true
    start: "22:00"
    end: "07:00"
    exceptions: ["critical_health_alert"]
```

---

## Autonomous Agent: When Does It Run?

### Ralph (Development Mode)
Ralph runs **only during development** to build JARVIS:
```bash
# You run this manually when developing
ralph --verbose

# Ralph loops: reads PROMPT.md → executes Claude Code → updates @fix_plan.md → repeats
```
Once JARVIS is built, Ralph is not needed for daily operation.

### Clawdbot Daemon (Always Running)
```bash
# Starts on boot, runs forever
clawdbot daemon start

# This is what runs 24/7:
# - Listens for messages (WhatsApp, Telegram, etc.)
# - Executes scheduled cron jobs
# - Processes incoming requests
```

### Scheduled Jobs (APScheduler / Clawdbot Cron)

```python
# src/jarvis/autonomous/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# These run automatically, no human trigger needed
scheduler.add_job(morning_briefing, 'cron', hour=6, minute=30)
scheduler.add_job(health_check, 'interval', hours=2)
scheduler.add_job(evening_reflection, 'cron', hour=21, minute=0)
scheduler.add_job(data_sync, 'interval', minutes=15)
scheduler.add_job(midday_calendar_check, 'cron', hour=12, minute=0)

scheduler.start()  # Runs in background forever
```

---

## Summary: What Triggers What

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRIGGER → ACTION → OUTPUT                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SCHEDULED (Automatic)                                          │
│  ────────────────────                                           │
│  Timer 6:30 AM    → Morning Briefing   → 🔊 Speaker + 📱 Push   │
│  Timer every 2h   → Health Check       → 📱 Push (if anomaly)   │
│  Timer 9:00 PM    → Evening Reflection → 📱 Push (+ 🔊 optional)│
│  Timer every 15m  → Data Sync          → Silent (background)    │
│                                                                  │
│  USER-TRIGGERED                                                  │
│  ──────────────                                                  │
│  "Hey JARVIS"    → Voice Pipeline     → 🔊 Speaker response    │
│  WhatsApp msg     → Clawdbot Skill     → 📱 WhatsApp reply      │
│  Telegram msg     → Clawdbot Skill     → 📱 Telegram reply      │
│                                                                  │
│  LOCATION-TRIGGERED (via Home Assistant)                        │
│  ──────────────────                                              │
│  Arrive home      → Welcome Routine    → 🔊 Speaker + 💡 Lights │
│  Leave home       → Away Routine       → 🔒 Lock + 💡 Off       │
│  Enter zone       → Zone Automation    → Configurable           │
│                                                                  │
│  EVENT-TRIGGERED                                                 │
│  ───────────────                                                 │
│  Calendar event   → Reminder           → 📱 Push (+ 🔊 optional)│
│  Whoop recovery   → Training adjust    → 📱 Push suggestion     │
│  Motion sensor    → HA Automation      → 💡 Lights etc.         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Process Architecture (What's Running)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Pi 5 (Brain)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Process 1: clawdbot daemon                                     │
│  ├── Listens on WhatsApp, Telegram, Slack, Web                  │
│  ├── Routes to skills                                           │
│  ├── Runs cron jobs (morning briefing, etc.)                    │
│  └── PID file: /var/run/clawdbot.pid                            │
│                                                                  │
│  Process 2: jarvis-voice                                        │
│  ├── Porcupine wake word listener                               │
│  ├── Whisper STT                                                │
│  ├── Piper TTS                                                  │
│  └── Bluetooth audio output                                     │
│                                                                  │
│  Process 3: jarvis-sync                                         │
│  ├── APScheduler running data sync jobs                         │
│  ├── Whoop, Garmin, Calendar adapters                           │
│  └── Writes to SQLite on Pi 4                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Pi 4 (Data)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Process 1: Home Assistant                                      │
│  ├── Docker container                                           │
│  ├── Manages smart home devices                                 │
│  ├── Receives location from HA Companion App                    │
│  └── REST API for JARVIS                                       │
│                                                                  │
│  Process 2: Redis                                               │
│  ├── Caches API responses                                       │
│  └── Session state                                              │
│                                                                  │
│  Process 3: SQLite (file-based)                                 │
│  └── /data/jarvis/main.db                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Card

| I want to... | How | Response |
|--------------|-----|----------|
| Get morning briefing | Wait for 6:30 AM | Speaker + Push |
| Ask a question by voice | "Hey JARVIS, [question]" | Speaker |
| Ask via phone | WhatsApp/Telegram message | Reply in app |
| Log food | "Log lunch: [food]" via any channel | Confirmation |
| Check schedule | "What's my schedule?" | List of events |
| Control home | "Turn on lights" | Action + optional confirm |
| Check health | "How's my recovery?" | Health summary |
| Get training | "What's my workout?" | Today's plan |
| Search notes | "Search notes for [topic]" | Relevant notes |
