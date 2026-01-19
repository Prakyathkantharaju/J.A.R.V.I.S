"""Whoop adapter for recovery and strain data."""

from datetime import date, datetime, timedelta
from typing import Any

from jarvis.config.settings import settings
from jarvis.adapters.base import AuthenticationError, BaseAdapter, FetchError

# Whoop API is accessed via whoopy library when available
try:
    from whoopy import WhoopClient

    WHOOP_AVAILABLE = True
except ImportError:
    WHOOP_AVAILABLE = False
    WhoopClient = None  # type: ignore


class WhoopAdapter(BaseAdapter):
    """Adapter for Whoop fitness/recovery data.

    Fetches:
    - Recovery score
    - Sleep data (stages, efficiency)
    - Strain score
    - HRV (Heart Rate Variability)
    - Workouts
    """

    def __init__(self) -> None:
        super().__init__("whoop")
        self._client: Any = None

    async def connect(self) -> bool:
        """Connect to Whoop API using OAuth tokens."""
        if not WHOOP_AVAILABLE:
            self.logger.warning("whoopy library not installed. Run: uv sync --extra whoop")
            return False

        try:
            access_token = settings.whoop.access_token.get_secret_value()
            refresh_token = settings.whoop.refresh_token.get_secret_value()

            if not access_token:
                self.logger.warning("Whoop tokens not configured. Run oauth_setup.py")
                return False

            self._client = WhoopClient(
                access_token=access_token,
                refresh_token=refresh_token,
            )
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
            self._client.user.profile()
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

            # Get cycles (contains recovery, sleep, strain)
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            cycles = self._client.cycle.collection(start=start_dt, end=end_dt)

            if cycles:
                latest_cycle = cycles[-1]  # Most recent

                # Recovery data
                recovery = latest_cycle.get("score", {}).get("recovery")
                if recovery:
                    data["recovery"] = {
                        "score": recovery.get("recovery_score"),
                        "hrv_ms": recovery.get("hrv_rmssd_milli"),
                        "resting_hr": recovery.get("resting_heart_rate"),
                        "spo2": recovery.get("spo2_percentage"),
                        "skin_temp_celsius": recovery.get("skin_temp_celsius"),
                    }

                # Sleep data
                sleep = latest_cycle.get("score", {}).get("sleep")
                if sleep:
                    data["sleep"] = {
                        "quality_score": sleep.get("sleep_performance_percentage"),
                        "efficiency": sleep.get("sleep_efficiency_percentage"),
                        "total_hours": sleep.get("total_in_bed_time_milli", 0) / 3600000,
                        "disturbances": sleep.get("disturbances"),
                        "latency_minutes": sleep.get("latency_milli", 0) / 60000,
                        "stages": {
                            "awake_hours": sleep.get("awake_time_milli", 0) / 3600000,
                            "light_hours": sleep.get("light_sleep_time_milli", 0) / 3600000,
                            "deep_hours": sleep.get("slow_wave_sleep_time_milli", 0) / 3600000,
                            "rem_hours": sleep.get("rem_sleep_time_milli", 0) / 3600000,
                        },
                    }

                # Strain data
                strain = latest_cycle.get("score", {}).get("strain")
                if strain:
                    data["strain"] = {
                        "score": strain.get("strain"),
                        "max_hr": strain.get("max_heart_rate"),
                        "avg_hr": strain.get("average_heart_rate"),
                        "calories": strain.get("kilojoule", 0) * 0.239,  # kJ to kcal
                    }

            # Get workouts for the date range
            workouts = self._client.workout.collection(start=start_dt, end=end_dt)
            if workouts:
                data["workouts"] = [
                    {
                        "sport": w.get("sport_id"),
                        "strain": w.get("score", {}).get("strain"),
                        "avg_hr": w.get("score", {}).get("average_heart_rate"),
                        "max_hr": w.get("score", {}).get("max_heart_rate"),
                        "calories": w.get("score", {}).get("kilojoule", 0) * 0.239,
                        "duration_minutes": w.get("score", {}).get("time_milli", 0) / 60000,
                    }
                    for w in workouts
                ]

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
