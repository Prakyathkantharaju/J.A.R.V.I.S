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

            client_id = settings.whoop.client_id
            client_secret = settings.whoop.client_secret.get_secret_value()

            self._client = WhoopClient.from_token(
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
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
                latest_cycle = cycles[-1]  # Most recent

                # Strain data from cycle score (Pydantic model)
                if latest_cycle.score:
                    score = latest_cycle.score
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

                        # Use sleep performance as recovery proxy since recovery API
                        # requires additional OAuth scope that may not be available
                        if sleep_performance is not None:
                            data["recovery"] = {
                                "score": sleep_performance,  # Sleep performance as proxy
                                "source": "sleep_performance",
                            }
            except Exception:
                pass  # Sleep data not available

            # Try dedicated recovery endpoint (may fail due to OAuth scope)
            try:
                recoveries = self._client.recovery.get_all(start=start_dt, end=end_dt)
                if recoveries:
                    latest_recovery = recoveries[-1]
                    if latest_recovery.score:
                        rec_score = latest_recovery.score
                        # Override with actual recovery if available
                        data["recovery"] = {
                            "score": getattr(rec_score, "recovery_score", None),
                            "hrv_ms": getattr(rec_score, "hrv_rmssd_milli", None),
                            "resting_hr": getattr(rec_score, "resting_heart_rate", None),
                            "source": "recovery_api",
                        }
            except Exception:
                pass  # Recovery API not available, sleep proxy is used

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
