"""Daily aggregator for morning briefings and summaries."""

from datetime import date
from typing import Any

import structlog

from jarvis.adapters.home_assistant import HomeAssistantAdapter
from jarvis.adapters.obsidian import ObsidianAdapter
from jarvis.aggregators.calendar import CalendarAggregator
from jarvis.aggregators.health import HealthAggregator

logger = structlog.get_logger()


class DailyAggregator:
    """Aggregates all data sources for daily briefings.

    Combines:
    - Health data (sleep, recovery, activity)
    - Calendar events (personal + work)
    - Training plan for today
    - Weather (via Home Assistant if available)
    """

    def __init__(self) -> None:
        self.health = HealthAggregator()
        self.calendar = CalendarAggregator()
        self.obsidian = ObsidianAdapter()
        self.home_assistant = HomeAssistantAdapter()

    async def __aenter__(self) -> "DailyAggregator":
        """Connect to all sources."""
        # Health aggregator handles its own connections
        await self.health.__aenter__()
        await self.calendar.__aenter__()
        await self.obsidian.connect()
        await self.home_assistant.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Disconnect from all sources."""
        await self.health.__aexit__(exc_type, exc_val, exc_tb)
        await self.calendar.__aexit__(exc_type, exc_val, exc_tb)
        await self.obsidian.disconnect()
        await self.home_assistant.disconnect()

    async def get_morning_briefing(self) -> dict[str, Any]:
        """Generate morning briefing with all relevant data.

        Returns:
            Complete morning briefing data.
        """
        today = date.today()

        briefing: dict[str, Any] = {
            "date": today.isoformat(),
            "type": "morning_briefing",
            "sections": {},
        }

        # Health summary
        try:
            health_data = await self.health.get_summary(today)
            briefing["sections"]["health"] = {
                "sleep": health_data.get("sleep", {}),
                "recovery": health_data.get("recovery", {}),
                "yesterday_activity": health_data.get("activity", {}),
            }
        except Exception as e:
            logger.warning("Failed to get health data", error=str(e))
            briefing["sections"]["health"] = {"error": str(e)}

        # Calendar for today
        try:
            calendar_data = await self.calendar.get_merged_events(today)
            briefing["sections"]["calendar"] = {
                "events": calendar_data.get("events", []),
                "summary": calendar_data.get("summary", {}),
                "conflicts": calendar_data.get("conflicts", []),
            }
        except Exception as e:
            logger.warning("Failed to get calendar", error=str(e))
            briefing["sections"]["calendar"] = {"error": str(e)}

        # Training plan for today
        try:
            obsidian_data = await self.obsidian.fetch(today)
            training = obsidian_data.get("training")
            if training:
                briefing["sections"]["training"] = {"plan": training}
            else:
                # Try to find training plan file
                plan = await self.obsidian.get_training_plan()
                if "content" in plan:
                    briefing["sections"]["training"] = {
                        "plan_name": plan.get("name"),
                        "note": "Check your training plan for today's workout",
                    }
        except Exception as e:
            logger.warning("Failed to get training plan", error=str(e))

        # Weather (if Home Assistant has weather entity)
        if self.home_assistant.is_connected:
            try:
                weather = await self._get_weather()
                if weather:
                    briefing["sections"]["weather"] = weather
            except Exception as e:
                logger.warning("Failed to get weather", error=str(e))

        # Generate natural language summary
        briefing["summary"] = self._generate_summary_text(briefing)

        return briefing

    async def get_evening_reflection(self) -> dict[str, Any]:
        """Generate evening reflection/summary.

        Returns:
            End-of-day summary data.
        """
        today = date.today()

        reflection: dict[str, Any] = {
            "date": today.isoformat(),
            "type": "evening_reflection",
            "sections": {},
        }

        # Today's activity summary
        try:
            health_data = await self.health.get_summary(today)
            reflection["sections"]["activity"] = {
                "stats": health_data.get("activity", {}),
                "workouts": health_data.get("workouts", []),
            }
        except Exception as e:
            logger.warning("Failed to get activity data", error=str(e))

        # Completed events
        try:
            calendar_data = await self.calendar.get_merged_events(today)
            reflection["sections"]["completed"] = {
                "events_count": len(calendar_data.get("events", [])),
                "meetings": calendar_data.get("summary", {}).get("online_meetings", 0),
            }
        except Exception as e:
            logger.warning("Failed to get calendar", error=str(e))

        # Food log from today
        try:
            obsidian_data = await self.obsidian.fetch(today)
            food = obsidian_data.get("food", [])
            if food:
                reflection["sections"]["nutrition"] = {"meals": food}
        except Exception as e:
            logger.warning("Failed to get food log", error=str(e))

        # Tomorrow preview
        try:
            from datetime import timedelta

            tomorrow = today + timedelta(days=1)
            tomorrow_cal = await self.calendar.get_merged_events(tomorrow)
            reflection["sections"]["tomorrow"] = {
                "events_count": len(tomorrow_cal.get("events", [])),
                "first_event": (
                    tomorrow_cal.get("events", [{}])[0] if tomorrow_cal.get("events") else None
                ),
            }
        except Exception as e:
            logger.warning("Failed to get tomorrow's calendar", error=str(e))

        reflection["summary"] = self._generate_reflection_text(reflection)

        return reflection

    async def _get_weather(self) -> dict[str, Any] | None:
        """Get weather from Home Assistant weather entity."""
        if not self.home_assistant.is_connected:
            return None

        try:
            # Common weather entity IDs
            weather_entities = [
                "weather.home",
                "weather.forecast_home",
                "weather.openweathermap",
            ]

            for entity_id in weather_entities:
                try:
                    state = await self.home_assistant.fetch(
                        date.today(), entity_ids=[entity_id]
                    )
                    weather_state = state.get("states", {}).get(entity_id, {})
                    if weather_state and "error" not in weather_state:
                        attrs = weather_state.get("attributes", {})
                        return {
                            "condition": weather_state.get("state"),
                            "temperature": attrs.get("temperature"),
                            "humidity": attrs.get("humidity"),
                            "wind_speed": attrs.get("wind_speed"),
                        }
                except Exception:
                    continue

            return None
        except Exception:
            return None

    def _generate_summary_text(self, briefing: dict[str, Any]) -> str:
        """Generate natural language morning summary."""
        parts = []
        sections = briefing.get("sections", {})

        # Greeting
        parts.append("Good morning!")

        # Sleep
        health = sections.get("health", {})
        sleep = health.get("sleep", {})
        if sleep.get("total_hours"):
            hours = sleep["total_hours"]
            quality = sleep.get("quality_score", "")
            parts.append(
                f"You slept {hours:.1f} hours"
                + (f" with {quality}% quality" if quality else "")
                + "."
            )

        # Recovery
        recovery = health.get("recovery", {})
        if recovery.get("score"):
            score = recovery["score"]
            status = "excellent" if score >= 80 else "good" if score >= 60 else "low"
            parts.append(f"Recovery is {status} at {score}%.")

        # Calendar
        calendar = sections.get("calendar", {})
        summary = calendar.get("summary", {})
        if summary.get("total_events"):
            total = summary["total_events"]
            meetings = summary.get("online_meetings", 0)
            parts.append(
                f"You have {total} events today"
                + (f" including {meetings} meetings" if meetings else "")
                + "."
            )

        # Training
        training = sections.get("training", {})
        if training.get("plan"):
            parts.append(f"Training today: {training['plan'][:100]}...")

        # Weather
        weather = sections.get("weather", {})
        if weather.get("condition"):
            temp = weather.get("temperature", "")
            parts.append(
                f"Weather is {weather['condition']}"
                + (f", {temp}°" if temp else "")
                + "."
            )

        return " ".join(parts)

    def _generate_reflection_text(self, reflection: dict[str, Any]) -> str:
        """Generate natural language evening summary."""
        parts = []
        sections = reflection.get("sections", {})

        parts.append("Good evening!")

        # Activity
        activity = sections.get("activity", {})
        stats = activity.get("stats", {})
        if stats.get("steps"):
            parts.append(f"Today you walked {stats['steps']:,} steps.")

        workouts = activity.get("workouts", [])
        if workouts:
            parts.append(f"You completed {len(workouts)} workout(s).")

        # Completed
        completed = sections.get("completed", {})
        if completed.get("events_count"):
            parts.append(f"You had {completed['events_count']} calendar events.")

        # Tomorrow
        tomorrow = sections.get("tomorrow", {})
        if tomorrow.get("events_count"):
            parts.append(f"Tomorrow you have {tomorrow['events_count']} events.")
            first = tomorrow.get("first_event")
            if first:
                parts.append(f"First event: {first.get('title', 'Unknown')}.")

        parts.append("Get some rest!")

        return " ".join(parts)


# Convenience function
async def get_daily_briefing() -> dict[str, Any]:
    """Get morning briefing."""
    async with DailyAggregator() as agg:
        return await agg.get_morning_briefing()


async def get_evening_summary() -> dict[str, Any]:
    """Get evening reflection."""
    async with DailyAggregator() as agg:
        return await agg.get_evening_reflection()
