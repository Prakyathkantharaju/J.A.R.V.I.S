"""Calendar aggregator combining Google and Outlook calendars."""

from datetime import date, datetime
from typing import Any

import structlog

from jarvis.adapters.google_calendar import GoogleCalendarAdapter
from jarvis.adapters.outlook import OutlookAdapter

logger = structlog.get_logger()


class CalendarAggregator:
    """Aggregates calendar events from Google (personal) and Outlook (work).

    Features:
    - Merged timeline view
    - Conflict detection
    - Meeting categorization
    """

    def __init__(self) -> None:
        self.google = GoogleCalendarAdapter()
        self.outlook = OutlookAdapter()

    async def __aenter__(self) -> "CalendarAggregator":
        """Connect to all calendar sources."""
        await self.google.connect()
        await self.outlook.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Disconnect from all sources."""
        await self.google.disconnect()
        await self.outlook.disconnect()

    async def get_merged_events(
        self,
        target_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get merged calendar events from all sources.

        Args:
            target_date: Start date (defaults to today)
            end_date: End date (defaults to target_date)

        Returns:
            Merged and sorted events from all calendars.
        """
        target_date = target_date or date.today()
        end_date = end_date or target_date

        all_events: list[dict[str, Any]] = []
        sources: list[str] = []

        # Fetch from Google Calendar (personal)
        if self.google.is_connected:
            try:
                google_data = await self.google.fetch(target_date, end_date)
                for event in google_data.get("events", []):
                    event["calendar_type"] = "personal"
                    all_events.append(event)
                sources.append("google")
            except Exception as e:
                logger.warning("Failed to fetch Google Calendar", error=str(e))

        # Fetch from Outlook (work)
        if self.outlook.is_connected:
            try:
                outlook_data = await self.outlook.fetch(target_date, end_date)
                for event in outlook_data.get("events", []):
                    event["calendar_type"] = "work"
                    all_events.append(event)
                sources.append("outlook")
            except Exception as e:
                logger.warning("Failed to fetch Outlook", error=str(e))

        # Sort events by start time
        all_events.sort(key=lambda e: e.get("start", ""))

        # Detect conflicts
        conflicts = self._detect_conflicts(all_events)

        return {
            "date": target_date.isoformat(),
            "sources": sources,
            "events": all_events,
            "conflicts": conflicts,
            "summary": self._generate_summary(all_events),
        }

    def _detect_conflicts(
        self, events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect overlapping events."""
        conflicts = []
        timed_events = [e for e in events if not e.get("all_day")]

        for i, event1 in enumerate(timed_events):
            for event2 in timed_events[i + 1:]:
                if self._events_overlap(event1, event2):
                    conflicts.append(
                        {
                            "event1": event1.get("title"),
                            "event2": event2.get("title"),
                            "time": event1.get("start"),
                        }
                    )

        return conflicts

    def _events_overlap(
        self, event1: dict[str, Any], event2: dict[str, Any]
    ) -> bool:
        """Check if two events overlap."""
        try:
            start1 = self._parse_datetime(event1.get("start", ""))
            end1 = self._parse_datetime(event1.get("end", ""))
            start2 = self._parse_datetime(event2.get("start", ""))
            end2 = self._parse_datetime(event2.get("end", ""))

            if not all([start1, end1, start2, end2]):
                return False

            return start1 < end2 and start2 < end1
        except Exception:
            return False

    def _parse_datetime(self, dt_str: str) -> datetime | None:
        """Parse datetime string (handles various formats)."""
        if not dt_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str.replace("Z", "+00:00"), fmt)
            except ValueError:
                continue

        return None

    def _generate_summary(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate summary statistics for events."""
        total = len(events)
        work = sum(1 for e in events if e.get("calendar_type") == "work")
        personal = sum(1 for e in events if e.get("calendar_type") == "personal")
        all_day = sum(1 for e in events if e.get("all_day"))
        meetings = sum(1 for e in events if e.get("is_online") or e.get("meeting_link"))

        return {
            "total_events": total,
            "work_events": work,
            "personal_events": personal,
            "all_day_events": all_day,
            "online_meetings": meetings,
        }

    async def get_next_event(self) -> dict[str, Any] | None:
        """Get the next upcoming event."""
        data = await self.get_merged_events()
        events = data.get("events", [])

        now = datetime.now()
        for event in events:
            if event.get("all_day"):
                continue
            start = self._parse_datetime(event.get("start", ""))
            if start and start > now:
                return event

        return None

    async def get_free_slots(
        self,
        target_date: date | None = None,
        work_hours: tuple[int, int] = (9, 17),
    ) -> list[dict[str, str]]:
        """Find free time slots in the day.

        Args:
            target_date: Date to check
            work_hours: Tuple of (start_hour, end_hour)

        Returns:
            List of free time slots.
        """
        target_date = target_date or date.today()
        data = await self.get_merged_events(target_date)
        events = [e for e in data.get("events", []) if not e.get("all_day")]

        # Build occupied time ranges
        occupied = []
        for event in events:
            start = self._parse_datetime(event.get("start", ""))
            end = self._parse_datetime(event.get("end", ""))
            if start and end:
                occupied.append((start, end))

        occupied.sort(key=lambda x: x[0])

        # Find free slots within work hours
        free_slots = []
        day_start = datetime.combine(target_date, datetime.min.time()).replace(
            hour=work_hours[0]
        )
        day_end = datetime.combine(target_date, datetime.min.time()).replace(
            hour=work_hours[1]
        )

        current = day_start
        for start, end in occupied:
            if start > current:
                free_slots.append(
                    {
                        "start": current.isoformat(),
                        "end": min(start, day_end).isoformat(),
                    }
                )
            current = max(current, end)

        if current < day_end:
            free_slots.append(
                {
                    "start": current.isoformat(),
                    "end": day_end.isoformat(),
                }
            )

        return free_slots


# Convenience function
async def get_merged_calendar(target_date: date | None = None) -> dict[str, Any]:
    """Get merged calendar events."""
    async with CalendarAggregator() as agg:
        return await agg.get_merged_events(target_date)
