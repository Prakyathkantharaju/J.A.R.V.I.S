"""Clawd agent using Pydantic AI with OpenRouter."""

import os
from datetime import date
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from jarvis.clawd import tools
from jarvis.config.settings import settings


class ClawdDependencies(BaseModel):
    """Dependencies passed to the agent."""

    user_name: str = "Prakyath"
    current_date: str = date.today().isoformat()


# System prompt for Clawd
SYSTEM_PROMPT = """You are Clawd, a personal AI assistant for {user_name}. Today is {current_date}.

You have access to:
- Obsidian vault with notes, tasks, and saved articles
- Health data from Whoop and Garmin (sleep, recovery, strain, activity)
- Calendar events

Your personality:
- Helpful and concise
- Proactive in suggesting relevant information
- Aware of user's health and schedule context

When responding:
- Be brief unless asked for details
- Reference specific data when relevant
- Suggest actions based on context (e.g., rest if recovery is low)
"""

# Global agent instance (lazily initialized)
_agent: Agent[ClawdDependencies, str] | None = None


def _create_agent() -> Agent[ClawdDependencies, str]:
    """Create and configure the Clawd agent with tools."""
    model = settings.openrouter.model
    # OpenRouter models need openai: prefix for pydantic-ai
    model_name = f"openai:{model}"

    agent = Agent(
        model_name,
        deps_type=ClawdDependencies,
        system_prompt=SYSTEM_PROMPT,
    )

    # Register tools
    @agent.tool
    def get_tasks(ctx: RunContext[ClawdDependencies], include_completed: bool = False) -> list[dict[str, Any]]:
        """Get tasks from Obsidian Tasks.md file.

        Args:
            include_completed: Whether to include completed tasks (default: False)

        Returns:
            List of tasks with text, status, due date, and priority.
        """
        return tools.get_tasks(include_completed=include_completed)

    @agent.tool
    def search_notes(ctx: RunContext[ClawdDependencies], query: str) -> list[dict[str, Any]]:
        """Search notes in the Obsidian vault.

        Args:
            query: Search term to find in notes.

        Returns:
            List of matching notes with paths and matching lines.
        """
        return tools.search_notes(query)

    @agent.tool
    def get_daily_note(ctx: RunContext[ClawdDependencies], date_str: str | None = None) -> dict[str, Any]:
        """Get the daily note for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format (default: today)

        Returns:
            Daily note content and metadata.
        """
        target_date = date.fromisoformat(date_str) if date_str else None
        return tools.get_daily_note(target_date)

    @agent.tool
    def get_food_log(ctx: RunContext[ClawdDependencies], date_str: str | None = None) -> list[dict[str, str]]:
        """Get food log entries from daily note.

        Args:
            date_str: Date in YYYY-MM-DD format (default: today)

        Returns:
            List of food entries with meal type and description.
        """
        target_date = date.fromisoformat(date_str) if date_str else None
        return tools.get_food_log(target_date)

    @agent.tool
    def get_articles(ctx: RunContext[ClawdDependencies], limit: int = 10) -> list[dict[str, Any]]:
        """Get saved articles from Clippings folder.

        Args:
            limit: Maximum number of articles to return.

        Returns:
            List of article summaries with title and preview.
        """
        return tools.get_articles(limit=limit)

    @agent.tool
    def read_note(ctx: RunContext[ClawdDependencies], path: str) -> dict[str, Any]:
        """Read a specific note by its path.

        Args:
            path: Relative path to the note within the vault.

        Returns:
            Note content and metadata.
        """
        return tools.read_note(path)

    @agent.tool
    def get_health_summary(ctx: RunContext[ClawdDependencies]) -> dict[str, Any]:
        """Get health summary from Whoop and Garmin.

        Returns:
            Health data including sleep, recovery, strain, steps, and heart rate.
        """
        return tools.get_health_summary()

    @agent.tool
    def get_calendar_events(ctx: RunContext[ClawdDependencies]) -> dict[str, Any]:
        """Get today's calendar events.

        Returns:
            Calendar data with events and summary.
        """
        return tools.get_calendar_events()

    return agent


def get_agent() -> Agent[ClawdDependencies, str]:
    """Get or create the Clawd agent (lazy initialization)."""
    global _agent
    if _agent is None:
        _agent = _create_agent()
    return _agent


async def run_clawd(
    message: str,
    user_name: str = "Prakyath",
    openrouter_api_key: str | None = None,
) -> str:
    """Run Clawd with a user message.

    Args:
        message: User's message/question.
        user_name: Name of the user.
        openrouter_api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var).

    Returns:
        Clawd's response.
    """
    # Set up OpenRouter - prefer settings, then param, then env var
    api_key = (
        settings.openrouter.api_key.get_secret_value()
        or openrouter_api_key
        or os.environ.get("OPENROUTER_API_KEY")
    )
    if not api_key:
        return "Error: OPENROUTER_API_KEY not set. Add to .env or set environment variable."

    # Configure OpenAI client for OpenRouter
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

    # Get the agent (created after env vars are set)
    agent = get_agent()

    deps = ClawdDependencies(
        user_name=user_name,
        current_date=date.today().isoformat(),
    )

    result = await agent.run(message, deps=deps)
    return result.output


def run_clawd_sync(
    message: str,
    user_name: str = "Prakyath",
    openrouter_api_key: str | None = None,
) -> str:
    """Synchronous wrapper for run_clawd."""
    import asyncio

    return asyncio.run(run_clawd(message, user_name, openrouter_api_key))
