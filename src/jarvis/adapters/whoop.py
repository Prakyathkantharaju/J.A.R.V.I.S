"""Whoop adapter for recovery and strain data."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from jarvis.config.settings import settings
from jarvis.adapters.base import AuthenticationError, BaseAdapter, FetchError

# Whoop API is accessed via whoopy library when available
try:
    from whoopy import WhoopClient

    WHOOP_AVAILABLE = True
except ImportError:
    WHOOP_AVAILABLE = False
    WhoopClient = None  # type: ignore

# Token storage path
WHOOP_TOKEN_FILE = Path.home() / ".config" / "jarvis" / "whoop_tokens.json"

# Whoop API v2 base URL (v1 recovery endpoint is broken)
WHOOP_API_V2 = "https://api.prod.whoop.com/developer/v2"


def _load_saved_tokens() -> dict[str, str] | None:
    """Load tokens from saved file."""
    try:
        if WHOOP_TOKEN_FILE.exists():
            data = json.loads(WHOOP_TOKEN_FILE.read_text())
            if data.get("access_token") and data.get("refresh_token"):
                return data
    except Exception:
        pass
    return None


def _fetch_recovery_v2(access_token: str, cycle_id: int | None = None) -> dict[str, Any] | None:
    """Fetch recovery data from Whoop API v2 (v1 endpoint is broken).

    The v2 /recovery endpoint returns all recovery records with actual recovery scores.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = httpx.get(f"{WHOOP_API_V2}/recovery", headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            records = data.get("records", [])

            if cycle_id:
                # Find recovery for specific cycle
                for rec in records:
                    if rec.get("cycle_id") == cycle_id:
                        return rec.get("score")
            elif records:
                # Return most recent recovery (first in list)
                return records[0].get("score")
    except Exception:
        pass
    return None


class WhoopAdapter(BaseAdapter):
    """Adapter for Whoop fitness/recovery data.

    Fetches:
    - Recovery score
    - Sleep data (stages, efficiency)
    - Strain score
    - HRV (Heart Rate Variability)
    - Workouts

    Tokens are persisted to ~/.config/jarvis/whoop_tokens.json after successful connection.
    """

    def __init__(self) -> None:
        super().__init__("whoop")
        self._client: Any = None
        self._access_token: str | None = None

    async def connect(self) -> bool:
        """Connect to Whoop API using OAuth tokens."""
        if not WHOOP_AVAILABLE:
            self.logger.warning("whoopy library not installed. Run: uv sync --extra whoop")
            return False

        try:
            # Ensure config directory exists
            WHOOP_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

            client_id = settings.whoop.client_id
            client_secret = settings.whoop.client_secret.get_secret_value()

            # Try loading from saved token file first (fresher tokens from auto-refresh)
            saved = _load_saved_tokens()
            if saved:
                access_token = saved["access_token"]
                refresh_token = saved["refresh_token"]
                self.logger.info("Using saved Whoop tokens")
            else:
                # Fall back to .env tokens
                access_token = settings.whoop.access_token.get_secret_value()
                refresh_token = settings.whoop.refresh_token.get_secret_value()

            if not access_token:
                self.logger.warning("Whoop tokens not configured. Run oauth_setup.py")
                return False

            self._client = WhoopClient.from_token(
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
            )
            self._access_token = access_token

            # Save tokens for future use (whoopy format includes refreshed tokens)
            self._client.save_token(str(WHOOP_TOKEN_FILE))

            self._connected = True
            self.logger.info("Connected to Whoop API")
            return True

        except Exception as e:
            self.logger.error("Failed to connect to Whoop", error=str(e))
            raise AuthenticationError(self.name, f"Authentication failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Whoop API."""
        self._client = None
        self._connected = False
        self.logger.info("Disconnected from Whoop API")

    async def health_check(self) -> bool:
        """Check if Whoop connection is healthy."""
        if not self._client:
            return False
        try:
            # Try to get user profile
            self._client.user.get_profile()
            return True
        except Exception:
            return False

    async def fetch(
        self,
        start_date: date,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch Whoop data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)

        Returns:
            Dictionary with Whoop data including recovery, sleep, strain.
        """
        if not self._client:
            raise FetchError(self.name, "Not connected")

        end_date = end_date or start_date

        try:
            data: dict[str, Any] = {
                "date": start_date.isoformat(),
                "source": "whoop",
            }

            # Get cycles (contains strain data)
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            cycles = self._client.cycles.get_all(start=start_dt, end=end_dt)

            if cycles:
                # cycles[0] is today's current cycle (most recent by start time)
                # cycles[-1] is the oldest in the range
                today_cycle = cycles[0]

                # Strain data from cycle score (Pydantic model)
                if today_cycle.score:
                    score = today_cycle.score
                    data["strain"] = {
                        "score": getattr(score, "strain", None),
                        "max_hr": getattr(score, "max_heart_rate", None),
                        "avg_hr": getattr(score, "average_heart_rate", None),
                        "calories": getattr(score, "calories", None),
                    }

            # Get sleep data (also used for recovery proxy)
            try:
                sleeps = self._client.sleep.get_all(start=start_dt, end=end_dt)
                # Filter out naps, get most recent main sleep
                main_sleeps = [s for s in sleeps if not getattr(s, "nap", False)]
                if main_sleeps:
                    latest_sleep = main_sleeps[-1]
                    if latest_sleep.score:
                        sleep_score = latest_sleep.score
                        stage_summary = getattr(sleep_score, "stage_summary", None)

                        # Calculate sleep duration and stages
                        total_sleep_ms = 0
                        stages = {}
                        if stage_summary:
                            total_sleep_ms = getattr(stage_summary, "total_sleep_time_milli", 0) or 0
                            stages = {
                                "deep_hours": (getattr(stage_summary, "total_slow_wave_sleep_time_milli", 0) or 0) / 3600000,
                                "light_hours": (getattr(stage_summary, "total_light_sleep_time_milli", 0) or 0) / 3600000,
                                "rem_hours": (getattr(stage_summary, "total_rem_sleep_time_milli", 0) or 0) / 3600000,
                                "awake_hours": (getattr(stage_summary, "total_awake_time_milli", 0) or 0) / 3600000,
                            }

                        sleep_performance = getattr(sleep_score, "sleep_performance_percentage", None)
                        sleep_efficiency = getattr(sleep_score, "sleep_efficiency_percentage", None)

                        data["sleep"] = {
                            "total_hours": total_sleep_ms / 3600000 if total_sleep_ms else 0,
                            "quality_score": sleep_performance,
                            "efficiency": sleep_efficiency,
                            "stages": stages,
                        }

            except Exception:
                pass  # Sleep data not available

            # Get recovery from v2 API (v1 endpoint is broken)
            # Get the cycle_id to find matching recovery
            cycle_id = cycles[0].id if cycles else None
            if self._access_token:
                recovery_score = _fetch_recovery_v2(self._access_token, cycle_id)
                if recovery_score:
                    data["recovery"] = {
                        "score": recovery_score.get("recovery_score"),
                        "hrv_ms": recovery_score.get("hrv_rmssd_milli"),
                        "resting_hr": recovery_score.get("resting_heart_rate"),
                        "spo2": recovery_score.get("spo2_percentage"),
                        "skin_temp": recovery_score.get("skin_temp_celsius"),
                        "source": "recovery_v2_api",
                    }

            self.logger.info("Fetched Whoop data", date=start_date.isoformat())
            return data

        except Exception as e:
            self.logger.error("Failed to fetch Whoop data", error=str(e))
            raise FetchError(self.name, f"Fetch failed: {e}") from e

    async def get_recovery_trend(self, days: int = 7) -> list[dict[str, Any]]:
        """Get recovery trend for the past N days."""
        if not self._client:
            raise FetchError(self.name, "Not connected")

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        data = await self.fetch(start_date, end_date)
        # Extract just recovery scores
        return data.get("recovery", {})


# Convenience function
async def get_whoop_data(target_date: date | None = None) -> dict[str, Any]:
    """Fetch Whoop data for a specific date."""
    target_date = target_date or date.today()
    async with WhoopAdapter() as adapter:
        return await adapter.fetch(target_date)
