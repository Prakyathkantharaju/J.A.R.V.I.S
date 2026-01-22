"""Obsidian and JARVIS tools for Clawd agent."""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from jarvis.config.settings import settings


def get_vault_path() -> Path:
    """Get the Obsidian vault path."""
    return settings.obsidian.vault_path.expanduser()


def get_tasks(include_completed: bool = False) -> list[dict[str, Any]]:
    """Get tasks from Tasks.md file.

    Args:
        include_completed: Whether to include completed tasks.

    Returns:
        List of task dictionaries with text, completed status, due date, etc.
    """
    vault = get_vault_path()
    tasks_file = vault / "Tasks.md"

    if not tasks_file.exists():
        return []

    content = tasks_file.read_text(encoding="utf-8")
    tasks = []

    # Parse markdown task format: - [ ] or - [x]
    task_pattern = re.compile(
        r"^[\s]*-\s*\[([ xX])\]\s*(.+)$", re.MULTILINE
    )

    for match in task_pattern.finditer(content):
        completed = match.group(1).lower() == "x"

        if not include_completed and completed:
            continue

        task_text = match.group(2).strip()

        # Extract due date if present (📅 YYYY-MM-DD format)
        due_match = re.search(r"📅\s*(\d{4}-\d{2}-\d{2})", task_text)
        due_date = due_match.group(1) if due_match else None

        # Extract priority markers
        priority = "normal"
        if "⏫" in task_text:
            priority = "high"
        elif "🔼" in task_text:
            priority = "medium"
        elif "🔽" in task_text:
            priority = "low"

        tasks.append({
            "text": task_text,
            "completed": completed,
            "due_date": due_date,
            "priority": priority,
        })

    return tasks


def search_notes(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search notes in the Obsidian vault.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of matching notes with path, title, and matching lines.
    """
    vault = get_vault_path()
    results = []
    query_lower = query.lower()

    for md_file in vault.rglob("*.md"):
        # Skip hidden folders
        if any(part.startswith(".") for part in md_file.parts):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            if query_lower in content.lower():
                # Find matching lines
                matches = []
                for i, line in enumerate(content.split("\n")):
                    if query_lower in line.lower():
                        matches.append({
                            "line": i + 1,
                            "text": line.strip()[:200],
                        })

                results.append({
                    "path": str(md_file.relative_to(vault)),
                    "title": md_file.stem,
                    "matches": matches[:3],
                })

                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return results


def get_daily_note(target_date: date | None = None) -> dict[str, Any]:
    """Get the daily note for a specific date.

    Args:
        target_date: Date to fetch (defaults to today).

    Returns:
        Dictionary with note content, sections, and metadata.
    """
    target_date = target_date or date.today()
    vault = get_vault_path()

    # Try common daily note formats
    date_formats = [
        (settings.obsidian.daily_notes_folder, settings.obsidian.daily_note_format),
        ("Daily Notes", "%Y-%m-%d"),
        (f"{target_date.year}/{target_date.strftime('%b')}", "%Y-%m-%d"),
        (f"{target_date.year}/Jan", "%Y-%m-%d"),  # Specific for user's vault
    ]

    for folder, fmt in date_formats:
        date_str = target_date.strftime(fmt)
        note_path = vault / folder / f"{date_str}.md"

        if note_path.exists():
            content = note_path.read_text(encoding="utf-8")
            return {
                "date": target_date.isoformat(),
                "path": str(note_path.relative_to(vault)),
                "content": content,
                "exists": True,
            }

    return {
        "date": target_date.isoformat(),
        "exists": False,
        "content": None,
    }


def get_food_log(target_date: date | None = None) -> list[dict[str, str]]:
    """Get food log entries from daily note.

    Args:
        target_date: Date to fetch food log for.

    Returns:
        List of food entries with meal type and description.
    """
    daily_note = get_daily_note(target_date)

    if not daily_note.get("exists"):
        return []

    content = daily_note.get("content", "")
    food_items = []

    # Find ## Food section
    food_match = re.search(
        r"##\s*Food\s*\n(.*?)(?=\n##|\Z)",
        content,
        re.IGNORECASE | re.DOTALL
    )

    if food_match:
        food_section = food_match.group(1)

        # Parse food entries
        for line in food_section.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Format: - **Meal**: Food items
            meal_match = re.match(r"^-\s*\*\*(.+?)\*\*:\s*(.+)$", line)
            if meal_match:
                food_items.append({
                    "meal": meal_match.group(1),
                    "food": meal_match.group(2),
                })
            elif line.startswith("- "):
                food_items.append({
                    "meal": "unspecified",
                    "food": line[2:],
                })

    return food_items


def get_articles(limit: int = 20) -> list[dict[str, Any]]:
    """Get saved articles from Clippings folder.

    Args:
        limit: Maximum number of articles to return.

    Returns:
        List of article summaries with title, path, and preview.
    """
    vault = get_vault_path()
    clippings_folder = vault / "Clippings"

    if not clippings_folder.exists():
        return []

    articles = []

    for md_file in sorted(
        clippings_folder.rglob("*.md"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )[:limit]:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Extract title from first heading or filename
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else md_file.stem

            # Get preview (first 200 chars of body)
            body = re.sub(r"^#.*$", "", content, flags=re.MULTILINE).strip()
            preview = body[:200] + "..." if len(body) > 200 else body

            articles.append({
                "title": title,
                "path": str(md_file.relative_to(vault)),
                "preview": preview,
                "modified": datetime.fromtimestamp(
                    md_file.stat().st_mtime
                ).isoformat(),
            })
        except Exception:
            continue

    return articles


def read_note(path: str) -> dict[str, Any]:
    """Read a specific note by path.

    Args:
        path: Relative path to the note within the vault.

    Returns:
        Dictionary with note content and metadata.
    """
    vault = get_vault_path()
    note_path = vault / path

    if not note_path.exists():
        return {"error": f"Note not found: {path}"}

    try:
        content = note_path.read_text(encoding="utf-8")
        return {
            "path": path,
            "title": note_path.stem,
            "content": content,
        }
    except Exception as e:
        return {"error": str(e)}


def get_health_summary() -> dict[str, Any]:
    """Get health summary from JARVIS API.

    Returns:
        Health data including sleep, recovery, strain, and activity.
    """
    try:
        response = httpx.get("http://localhost:8000/api/health", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    # Fallback to direct adapter call if API not available
    try:
        import asyncio
        from jarvis.aggregators.health import get_health_summary as _get_health

        return asyncio.run(_get_health())
    except Exception as e:
        return {"error": str(e)}


def get_calendar_events(target_date: date | None = None) -> dict[str, Any]:
    """Get calendar events from JARVIS API.

    Args:
        target_date: Date to fetch events for.

    Returns:
        Calendar data with events and summary.
    """
    try:
        response = httpx.get("http://localhost:8000/api/calendar", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    return {"events": [], "error": "Calendar API not available"}
