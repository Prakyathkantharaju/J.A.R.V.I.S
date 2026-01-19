"""Garmin Connect adapter for fitness data."""

from datetime import date
from typing import Any

from garminconnect import Garmin

from jarvis.config.settings import settings
from jarvis.adapters.base import AuthenticationError, BaseAdapter, FetchError


class GarminAdapter(BaseAdapter):
    """Adapter for Garmin Connect fitness data.

    Fetches:
    - Daily stats (steps, calories, distance)
    - Heart rate data
    - Sleep data
    - Activities
    - Training status
    - Body battery
    """

    def __init__(self) -> None:
        super().__init__("garmin")
        self._client: Garmin | None = None

    async def connect(self) -> bool:
        """Connect to Garmin Connect using credentials."""
        try:
            email = settings.garmin.email
            password = settings.garmin.password.get_secret_value()

            if not email or not password:
                self.logger.warning("Garmin credentials not configured")
                return False

            self._client = Garmin(email, password)
            self._client.login()
            self._connected = True
            self.logger.info("Connected to Garmin Connect")
            return True

        except Exception as e:
            self.logger.error("Failed to connect to Garmin", error=str(e))
            raise AuthenticationError(self.name, f"Login failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Garmin Connect."""
        self._client = None
        self._connected = False
        self.logger.info("Disconnected from Garmin Connect")

    async def health_check(self) -> bool:
        """Check if Garmin connection is healthy."""
        if not self._client:
            return False
        try:
            # Try to fetch user profile as health check
            self._client.get_full_name()
            return True
        except Exception:
            return False

    async def fetch(
        self,
        start_date: date,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch Garmin data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)
            **kwargs: Additional options:
                - include_activities: bool (default True)
                - include_sleep: bool (default True)
                - include_hr: bool (default True)

        Returns:
            Dictionary with Garmin data.
        """
        if not self._client:
            raise FetchError(self.name, "Not connected")

        end_date = end_date or start_date
        include_activities = kwargs.get("include_activities", True)
        include_sleep = kwargs.get("include_sleep", True)
        include_hr = kwargs.get("include_hr", True)

        try:
            data: dict[str, Any] = {
                "date": start_date.isoformat(),
                "source": "garmin",
            }

            # Daily stats
            stats = self._client.get_stats(start_date.isoformat())
            data["daily_stats"] = {
                "steps": stats.get("totalSteps", 0),
                "distance_km": stats.get("totalDistanceMeters", 0) / 1000,
                "calories": stats.get("totalKilocalories", 0),
                "active_minutes": stats.get("moderateIntensityMinutes", 0)
                + stats.get("vigorousIntensityMinutes", 0),
                "floors_climbed": stats.get("floorsAscended", 0),
            }

            # Heart rate
            if include_hr:
                hr_data = self._client.get_heart_rates(start_date.isoformat())
                data["heart_rate"] = {
                    "resting_hr": hr_data.get("restingHeartRate"),
                    "max_hr": hr_data.get("maxHeartRate"),
                    "min_hr": hr_data.get("minHeartRate"),
                }

            # Sleep
            if include_sleep:
                sleep_data = self._client.get_sleep_data(start_date.isoformat())
                if sleep_data:
                    data["sleep"] = {
                        "total_sleep_seconds": sleep_data.get("sleepTimeSeconds", 0),
                        "deep_sleep_seconds": sleep_data.get("deepSleepSeconds", 0),
                        "light_sleep_seconds": sleep_data.get("lightSleepSeconds", 0),
                        "rem_sleep_seconds": sleep_data.get("remSleepSeconds", 0),
                        "awake_seconds": sleep_data.get("awakeSleepSeconds", 0),
                    }

            # Body battery
            try:
                bb_data = self._client.get_body_battery(start_date.isoformat())
                if bb_data:
                    data["body_battery"] = {
                        "charged": bb_data[0].get("charged", 0) if bb_data else 0,
                        "drained": bb_data[0].get("drained", 0) if bb_data else 0,
                    }
            except Exception:
                pass  # Body battery not available on all devices

            # Activities
            if include_activities:
                activities = self._client.get_activities_by_date(
                    start_date.isoformat(), end_date.isoformat()
                )
                data["activities"] = [
                    {
                        "name": a.get("activityName"),
                        "type": a.get("activityType", {}).get("typeKey"),
                        "duration_minutes": a.get("duration", 0) / 60,
                        "distance_km": (a.get("distance", 0) or 0) / 1000,
                        "calories": a.get("calories", 0),
                        "avg_hr": a.get("averageHR"),
                        "max_hr": a.get("maxHR"),
                    }
                    for a in (activities or [])
                ]

            self.logger.info("Fetched Garmin data", date=start_date.isoformat())
            return data

        except Exception as e:
            self.logger.error("Failed to fetch Garmin data", error=str(e))
            raise FetchError(self.name, f"Fetch failed: {e}") from e

    async def get_training_status(self) -> dict[str, Any]:
        """Get current training status and readiness."""
        if not self._client:
            raise FetchError(self.name, "Not connected")

        try:
            status = self._client.get_training_status(date.today().isoformat())
            return {
                "training_status": status.get("trainingStatusPhrase"),
                "vo2_max": status.get("vo2Max"),
                "load": status.get("weeklyTrainingLoad"),
            }
        except Exception as e:
            self.logger.warning("Could not fetch training status", error=str(e))
            return {}


# Convenience function for quick access
async def get_garmin_data(target_date: date | None = None) -> dict[str, Any]:
    """Fetch Garmin data for a specific date."""
    target_date = target_date or date.today()
    async with GarminAdapter() as adapter:
        return await adapter.fetch(target_date)
