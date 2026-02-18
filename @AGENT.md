# JARVIS - Agent Instructions

## Build Commands

```bash
# Install dependencies
uv sync

# Install with all extras (voice, whoop, dev)
uv sync --all-extras

# Run tests
uv run pytest

# Type check
uv run mypy src/

# Lint
uv run ruff check src/

# Format
uv run ruff format src/
```

## Run Commands

```bash
# Run JARVIS CLI
uv run jarvis

# Run specific adapter test
uv run python -m jarvis.adapters.garmin

# Run data sync
uv run python -m jarvis.autonomous.sync

# Start voice listener
uv run python -m jarvis.voice.pipeline
```

## Environment Setup

1. Copy `.env.example` to `.env`
2. Fill in API credentials
3. Run `uv run python scripts/oauth_setup.py` for OAuth services

## Deployment

### Local Development
```bash
uv sync
uv run jarvis
```

### Pi 5 (Brain)
```bash
ssh pi@pi5
cd /opt/jarvis
./scripts/setup_pi5.sh
sudo systemctl start jarvis-voice jarvis-sync
```

### Pi 4 (Data)
```bash
ssh pi@pi4
cd /opt/jarvis
./scripts/setup_pi4.sh
sudo systemctl start jarvis-ha
```

## File Locations

- Config: `~/.config/jarvis/` or `/etc/jarvis/`
- Data: `~/.local/share/jarvis/` or `/var/lib/jarvis/`
- Logs: `~/.local/state/jarvis/` or `/var/log/jarvis/`

## OpenClaw Integration

```bash
# Install OpenClaw
npm install -g openclaw@latest

# Onboard
openclaw onboard --install-daemon

# Install JARVIS skills
openclaw skill install ./src/jarvis/skills/
```

## Troubleshooting

- **Garmin auth fails**: Delete `~/.garminconnect` and re-auth
- **Whoop token expired**: Run oauth_setup.py again
- **Home Assistant unreachable**: Check Pi 4 is online and HA container running
- **Voice not working**: Check `arecord -l` for microphone, `aplay -l` for speakers
