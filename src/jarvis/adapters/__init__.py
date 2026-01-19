"""Data source adapters for JARVIS."""

from jarvis.adapters.base import (
    AdapterError,
    AuthenticationError,
    BaseAdapter,
    ConnectionError,
    FetchError,
)
from jarvis.adapters.garmin import GarminAdapter, get_garmin_data
from jarvis.adapters.google_calendar import GoogleCalendarAdapter, get_google_calendar_events
from jarvis.adapters.home_assistant import (
    HomeAssistantAdapter,
    control_device,
    get_my_location,
    speak_message,
)
from jarvis.adapters.obsidian import ObsidianAdapter, get_obsidian_daily, search_obsidian
from jarvis.adapters.outlook import OutlookAdapter, get_outlook_events
from jarvis.adapters.whoop import WhoopAdapter, get_whoop_data

__all__ = [
    # Base
    "BaseAdapter",
    "AdapterError",
    "AuthenticationError",
    "ConnectionError",
    "FetchError",
    # Adapters
    "GarminAdapter",
    "WhoopAdapter",
    "GoogleCalendarAdapter",
    "OutlookAdapter",
    "ObsidianAdapter",
    "HomeAssistantAdapter",
    # Convenience functions
    "get_garmin_data",
    "get_whoop_data",
    "get_google_calendar_events",
    "get_outlook_events",
    "get_obsidian_daily",
    "search_obsidian",
    "control_device",
    "speak_message",
    "get_my_location",
]
