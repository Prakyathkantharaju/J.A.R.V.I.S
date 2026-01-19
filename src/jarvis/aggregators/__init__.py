"""Data aggregators for combining multiple sources."""

from jarvis.aggregators.daily import DailyAggregator, get_daily_briefing
from jarvis.aggregators.health import HealthAggregator, get_health_summary
from jarvis.aggregators.calendar import CalendarAggregator, get_merged_calendar

__all__ = [
    "DailyAggregator",
    "HealthAggregator",
    "CalendarAggregator",
    "get_daily_briefing",
    "get_health_summary",
    "get_merged_calendar",
]
