# JARVIS - Development Instructions

You are building JARVIS, a personal AI assistant that integrates multiple life data sources and provides intelligent assistance via Clawdbot.

## Project Overview

JARVIS aggregates data from:
- **Whoop**: Sleep, recovery, strain, HRV
- **Garmin**: Activities, steps, heart rate, training status
- **Google Calendar**: Personal events
- **Outlook**: Work calendar (via Microsoft Graph)
- **Obsidian**: Notes, food logs, training plans
- **Home Assistant**: Smart home control, location tracking

## Architecture

```
User (Voice/WhatsApp/Telegram)
         ↓
    Clawdbot (Skills)
         ↓
    Python Adapters
         ↓
    External APIs + SQLite
```

## Key Files

- `src/jarvis/adapters/` - Data source adapters
- `src/jarvis/skills/` - Clawdbot skills (TypeScript)
- `src/jarvis/aggregators/` - Combine data from multiple sources
- `src/jarvis/autonomous/` - Scheduled routines
- `config/settings.py` - Configuration management

## Development Priorities

1. **Adapters First**: Get data flowing from each source
2. **Skills Second**: Expose data via Clawdbot skills
3. **Aggregation Third**: Combine sources for briefings
4. **Voice Last**: Add wake word + TTS

## Code Standards

- Python 3.12+
- Async/await for all I/O
- Pydantic for data validation
- Type hints everywhere
- Structured logging with structlog

## Testing

Run tests with: `uv run pytest`
Type check with: `uv run mypy src/`
Lint with: `uv run ruff check src/`

## Current Task

Check `@fix_plan.md` for the current prioritized task list.

## Success Criteria

JARVIS is complete when:
1. All adapters fetch data successfully
2. Clawdbot skills respond to queries
3. Morning briefing generates and speaks at 6:30 AM
4. "Hey JARVIS" wake word triggers voice interaction
5. Can be deployed to Raspberry Pi with one command

## EXIT_SIGNAL

When all tasks in @fix_plan.md are complete and tested, set:
```
RALPH_STATUS:
  EXIT_SIGNAL: true
  COMPLETION_REASON: "All JARVIS components implemented and tested"
```
