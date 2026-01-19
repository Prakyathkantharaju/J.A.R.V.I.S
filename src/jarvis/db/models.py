"""Database models for JARVIS using SQLModel."""

from datetime import date, datetime
from typing import Any

from sqlmodel import Field, SQLModel


class HealthMetric(SQLModel, table=True):
    """Stores daily health metrics from Whoop/Garmin."""

    id: int | None = Field(default=None, primary_key=True)
    date: date = Field(index=True)
    source: str  # "whoop", "garmin"

    # Sleep
    sleep_hours: float | None = None
    sleep_quality: float | None = None
    deep_sleep_hours: float | None = None
    rem_sleep_hours: float | None = None

    # Recovery
    recovery_score: float | None = None
    hrv_ms: float | None = None
    resting_hr: int | None = None

    # Activity
    steps: int | None = None
    calories: int | None = None
    active_minutes: int | None = None
    strain_score: float | None = None

    # Metadata
    raw_data: dict[str, Any] | None = Field(default=None, sa_column_kwargs={"type_": "JSON"})
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class CalendarEvent(SQLModel, table=True):
    """Cached calendar events."""

    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    source: str  # "google", "outlook"
    calendar_type: str  # "personal", "work"

    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    location: str | None = None
    description: str | None = None
    meeting_link: str | None = None

    synced_at: datetime = Field(default_factory=datetime.utcnow)


class FoodLog(SQLModel, table=True):
    """Food intake logs from Obsidian."""

    id: int | None = Field(default=None, primary_key=True)
    date: date = Field(index=True)
    meal: str  # "breakfast", "lunch", "dinner", "snack"
    food: str
    notes: str | None = None

    logged_at: datetime = Field(default_factory=datetime.utcnow)


class DailyNote(SQLModel, table=True):
    """Summary of daily notes from Obsidian."""

    id: int | None = Field(default=None, primary_key=True)
    date: date = Field(index=True, unique=True)

    has_food_log: bool = False
    has_training: bool = False
    has_reflection: bool = False

    content_preview: str | None = None
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class SyncState(SQLModel, table=True):
    """Tracks sync state for each adapter."""

    id: int | None = Field(default=None, primary_key=True)
    adapter: str = Field(index=True, unique=True)
    last_sync: datetime | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    sync_count: int = 0
