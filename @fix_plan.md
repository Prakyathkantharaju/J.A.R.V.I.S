# JARVIS - Task List

## Project Setup (COMPLETE)

- [x] Project structure (pyproject.toml, directories)
- [x] Ralph files (PROMPT.md, @fix_plan.md, @AGENT.md)
- [x] Configuration (settings.py, .env.example)
- [x] All adapters (Garmin, Whoop, Google Calendar, Outlook, Obsidian, Home Assistant)
- [x] Aggregators (Health, Calendar, Daily)
- [x] CLI entry point
- [x] Voice pipeline skeleton
- [x] Autonomous scheduler
- [x] Database models
- [x] Setup scripts (setup.sh, oauth_setup.py)
- [x] Pi deployment scripts (setup_pi5.sh, setup_pi4.sh)
- [x] Docker compose files
- [x] Systemd service files
- [x] Tests structure

## Ready for Development

### Before Pi Deployment
- [ ] Fill in .env with your actual credentials
- [ ] Run oauth_setup.py for Google Calendar
- [ ] Test Garmin connection locally
- [ ] Configure Home Assistant URL and token

### Pi 5 (Brain) Tasks
- [ ] SSH access configured
- [ ] Run setup_pi5.sh
- [ ] Pair Bluetooth speaker
- [ ] Configure Picovoice API key (for wake word)
- [ ] Test voice pipeline

### Pi 4 (Data) Tasks
- [ ] SSH access configured
- [ ] Run setup_pi4.sh
- [ ] Complete Home Assistant onboarding
- [ ] Create long-lived access token
- [ ] Install HA Companion App on phone

### Integration Testing
- [ ] Test: `jarvis status` - all adapters connect
- [ ] Test: `jarvis briefing` - generates morning briefing
- [ ] Test: `jarvis health` - shows sleep/recovery
- [ ] Test: `jarvis calendar` - shows merged events
- [ ] Test: `jarvis home on light.living_room` - controls device
- [ ] Test: Voice wake word "Hey JARVIS"

## Current Focus

**READY**: Waiting for SSH access to Raspberry Pis and API credentials

## Notes

All code scaffolding is complete. The next step is:
1. Configure .env with your credentials
2. Test locally with `uv sync && uv run jarvis status`
3. Deploy to Pis when SSH access is available
