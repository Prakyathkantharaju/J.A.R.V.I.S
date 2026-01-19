"""Obsidian vault adapter for notes, food logs, and training plans."""

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from jarvis.config.settings import settings
from jarvis.adapters.base import BaseAdapter, FetchError


class ObsidianAdapter(BaseAdapter):
    """Adapter for Obsidian vault (local markdown files).

    Fetches:
    - Daily notes
    - Food logs from ## Food sections
    - Training plans
    - Note search
    """

    def __init__(self) -> None:
        super().__init__("obsidian")
        self._vault_path: Path | None = None

    async def connect(self) -> bool:
        """Connect to Obsidian vault (verify path exists)."""
        try:
            vault_path = settings.obsidian.vault_path.expanduser()

            if not vault_path.exists():
                self.logger.warning("Obsidian vault not found", path=str(vault_path))
                return False

            if not vault_path.is_dir():
                self.logger.warning("Obsidian vault path is not a directory")
                return False

            self._vault_path = vault_path
            self._connected = True
            self.logger.info("Connected to Obsidian vault", path=str(vault_path))
            return True

        except Exception as e:
            self.logger.error("Failed to connect to Obsidian vault", error=str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from Obsidian vault."""
        self._vault_path = None
        self._connected = False
        self.logger.info("Disconnected from Obsidian vault")

    async def health_check(self) -> bool:
        """Check if Obsidian vault is accessible."""
        if not self._vault_path:
            return False
        return self._vault_path.exists() and self._vault_path.is_dir()

    def _get_daily_note_path(self, target_date: date) -> Path:
        """Get path to daily note for a given date."""
        if not self._vault_path:
            raise FetchError(self.name, "Not connected")

        date_str = target_date.strftime(settings.obsidian.daily_note_format)
        daily_folder = self._vault_path / settings.obsidian.daily_notes_folder
        return daily_folder / f"{date_str}.md"

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from markdown content."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    return frontmatter or {}, parts[2].strip()
                except yaml.YAMLError:
                    pass
        return {}, content

    def _extract_section(self, content: str, section_name: str) -> str | None:
        """Extract content under a specific heading."""
        # Match ## Section Name or # Section Name
        pattern = rf"^#+\s*{re.escape(section_name)}\s*$"
        lines = content.split("\n")
        in_section = False
        section_content = []

        for line in lines:
            if re.match(pattern, line, re.IGNORECASE):
                in_section = True
                continue
            elif in_section:
                # Stop at next heading
                if re.match(r"^#+\s+", line):
                    break
                section_content.append(line)

        if section_content:
            return "\n".join(section_content).strip()
        return None

    def _parse_food_section(self, food_content: str) -> list[dict[str, str]]:
        """Parse food items from the ## Food section."""
        items = []
        for line in food_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse "- **Meal**: Food items" format
            match = re.match(r"^-\s*\*\*(.+?)\*\*:\s*(.+)$", line)
            if match:
                items.append({"meal": match.group(1), "food": match.group(2)})
            # Also support simple "- Food item" format
            elif line.startswith("- "):
                items.append({"meal": "unspecified", "food": line[2:]})

        return items

    async def fetch(
        self,
        start_date: date,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch Obsidian data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)
            **kwargs:
                - include_food: bool (default True)
                - include_training: bool (default True)

        Returns:
            Dictionary with daily note content, food logs, training.
        """
        if not self._vault_path:
            raise FetchError(self.name, "Not connected")

        end_date = end_date or start_date
        include_food = kwargs.get("include_food", True)
        include_training = kwargs.get("include_training", True)

        try:
            note_path = self._get_daily_note_path(start_date)

            data: dict[str, Any] = {
                "date": start_date.isoformat(),
                "source": "obsidian",
                "note_exists": note_path.exists(),
            }

            if note_path.exists():
                content = note_path.read_text(encoding="utf-8")
                frontmatter, body = self._parse_frontmatter(content)

                data["frontmatter"] = frontmatter
                data["content_preview"] = body[:500] if body else ""

                # Extract food section
                if include_food:
                    food_section = self._extract_section(body, "Food")
                    if food_section:
                        data["food"] = self._parse_food_section(food_section)
                        data["food_raw"] = food_section

                # Extract training section
                if include_training:
                    training_section = self._extract_section(body, "Training")
                    if training_section:
                        data["training"] = training_section

            self.logger.info(
                "Fetched Obsidian data",
                date=start_date.isoformat(),
                exists=data["note_exists"],
            )
            return data

        except Exception as e:
            self.logger.error("Failed to fetch Obsidian data", error=str(e))
            raise FetchError(self.name, f"Fetch failed: {e}") from e

    async def search_notes(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search notes in the vault for a query string."""
        if not self._vault_path:
            raise FetchError(self.name, "Not connected")

        results = []
        query_lower = query.lower()

        for md_file in self._vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    # Find matching lines for context
                    matches = []
                    for i, line in enumerate(content.split("\n")):
                        if query_lower in line.lower():
                            matches.append({"line": i + 1, "text": line.strip()[:200]})

                    results.append(
                        {
                            "path": str(md_file.relative_to(self._vault_path)),
                            "title": md_file.stem,
                            "matches": matches[:3],  # First 3 matches
                        }
                    )

                    if len(results) >= max_results:
                        break
            except Exception:
                continue

        return results

    async def get_training_plan(self, plan_name: str = "Marathon Training Plan") -> dict[str, Any]:
        """Get training plan from a dedicated note."""
        if not self._vault_path:
            raise FetchError(self.name, "Not connected")

        # Search for training plan file
        for md_file in self._vault_path.rglob("*.md"):
            if plan_name.lower() in md_file.stem.lower():
                content = md_file.read_text(encoding="utf-8")
                _, body = self._parse_frontmatter(content)

                return {
                    "name": md_file.stem,
                    "path": str(md_file.relative_to(self._vault_path)),
                    "content": body,
                }

        return {"error": f"Training plan '{plan_name}' not found"}

    async def append_to_daily_note(self, target_date: date, section: str, content: str) -> bool:
        """Append content to a section in the daily note."""
        if not self._vault_path:
            raise FetchError(self.name, "Not connected")

        note_path = self._get_daily_note_path(target_date)

        try:
            if note_path.exists():
                existing = note_path.read_text(encoding="utf-8")
            else:
                # Create new daily note
                note_path.parent.mkdir(parents=True, exist_ok=True)
                date_str = target_date.strftime("%Y-%m-%d")
                existing = f"# {date_str}\n\n"

            # Check if section exists
            section_pattern = rf"^#+\s*{re.escape(section)}\s*$"
            if re.search(section_pattern, existing, re.MULTILINE):
                # Append to existing section
                lines = existing.split("\n")
                new_lines = []
                in_section = False
                added = False

                for line in lines:
                    new_lines.append(line)
                    if re.match(section_pattern, line, re.IGNORECASE):
                        in_section = True
                    elif in_section and not added:
                        if re.match(r"^#+\s+", line):
                            # Next section, insert before it
                            new_lines.insert(-1, content)
                            added = True
                            in_section = False

                if not added:
                    new_lines.append(content)

                note_path.write_text("\n".join(new_lines), encoding="utf-8")
            else:
                # Add new section
                existing += f"\n## {section}\n{content}\n"
                note_path.write_text(existing, encoding="utf-8")

            self.logger.info("Updated daily note", date=target_date.isoformat(), section=section)
            return True

        except Exception as e:
            self.logger.error("Failed to update daily note", error=str(e))
            return False


# Convenience functions
async def get_obsidian_daily(target_date: date | None = None) -> dict[str, Any]:
    """Fetch Obsidian daily note for a specific date."""
    target_date = target_date or date.today()
    async with ObsidianAdapter() as adapter:
        return await adapter.fetch(target_date)


async def search_obsidian(query: str) -> list[dict[str, Any]]:
    """Search Obsidian vault."""
    async with ObsidianAdapter() as adapter:
        return await adapter.search_notes(query)
