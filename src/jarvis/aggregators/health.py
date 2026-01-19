"""Health aggregator combining Whoop and Garmin data."""

from datetime import date
from typing import Any

import structlog

from jarvis.adapters.garmin import GarminAdapter
from jarvis.adapters.whoop import WhoopAdapter

logger = structlog.get_logger()


class HealthAggregator:
    """Aggregates health data from Whoop and Garmin.

    Combines:
    - Sleep data (prefers Whoop for stages, Garmin for backup)
    - Recovery/readiness scores
    - Activity metrics
    - Heart rate data
    """

    def __init__(self) -> None:
        self.garmin = GarminAdapter()
        self.whoop = WhoopAdapter()

    async def __aenter__(self) -> "HealthAggregator":
        """Connect to all health sources."""
        await self.garmin.connect()
        await self.whoop.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Disconnect from all sources."""
        await self.garmin.disconnect()
        await self.whoop.disconnect()

    async def get_summary(self, target_date: date | None = None) -> dict[str, Any]:
        """Get aggregated health summary for a date.

        Args:
            target_date: Date to fetch (defaults to today)

        Returns:
            Merged health data from all sources.
        """
        target_date = target_date or date.today()

        summary: dict[str, Any] = {
            "date": target_date.isoformat(),
            "sources": [],
        }

        # Fetch from Whoop (primary for recovery/sleep)
        whoop_data = {}
        if self.whoop.is_connected:
            try:
                whoop_data = await self.whoop.fetch(target_date)
                summary["sources"].append("whoop")
            except Exception as e:
                logger.warning("Failed to fetch Whoop data", error=str(e))

        # Fetch from Garmin (primary for activities/steps)
        garmin_data = {}
        if self.garmin.is_connected:
            try:
                garmin_data = await self.garmin.fetch(target_date)
                summary["sources"].append("garmin")
            except Exception as e:
                logger.warning("Failed to fetch Garmin data", error=str(e))

        # Merge sleep data (prefer Whoop)
        summary["sleep"] = self._merge_sleep(whoop_data, garmin_data)

        # Recovery (Whoop) or Body Battery (Garmin)
        summary["recovery"] = self._merge_recovery(whoop_data, garmin_data)

        # Activity metrics (prefer Garmin)
        summary["activity"] = self._merge_activity(whoop_data, garmin_data)

        # Heart rate (combine both)
        summary["heart_rate"] = self._merge_heart_rate(whoop_data, garmin_data)

        # Workouts (combine both)
        summary["workouts"] = self._merge_workouts(whoop_data, garmin_data)

        return summary

    def _merge_sleep(
        self, whoop_data: dict[str, Any], garmin_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge sleep data from both sources."""
        sleep = {}

        # Whoop sleep (more detailed)
        if "sleep" in whoop_data:
            ws = whoop_data["sleep"]
            sleep.update(
                {
                    "quality_score": ws.get("quality_score"),
                    "efficiency": ws.get("efficiency"),
                    "total_hours": ws.get("total_hours"),
                    "stages": ws.get("stages", {}),
                    "source": "whoop",
                }
            )
        # Fallback to Garmin
        elif "sleep" in garmin_data:
            gs = garmin_data["sleep"]
            total_seconds = gs.get("total_sleep_seconds", 0)
            sleep.update(
                {
                    "total_hours": total_seconds / 3600,
                    "stages": {
                        "deep_hours": gs.get("deep_sleep_seconds", 0) / 3600,
                        "light_hours": gs.get("light_sleep_seconds", 0) / 3600,
                        "rem_hours": gs.get("rem_sleep_seconds", 0) / 3600,
                        "awake_hours": gs.get("awake_seconds", 0) / 3600,
                    },
                    "source": "garmin",
                }
            )

        return sleep

    def _merge_recovery(
        self, whoop_data: dict[str, Any], garmin_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge recovery/readiness data."""
        recovery = {}

        # Whoop recovery (preferred)
        if "recovery" in whoop_data:
            wr = whoop_data["recovery"]
            recovery.update(
                {
                    "score": wr.get("score"),
                    "hrv_ms": wr.get("hrv_ms"),
                    "resting_hr": wr.get("resting_hr"),
                    "source": "whoop",
                }
            )
        # Garmin body battery as fallback
        elif "body_battery" in garmin_data:
            bb = garmin_data["body_battery"]
            # Convert body battery (0-100) to recovery-like score
            recovery.update(
                {
                    "body_battery_charged": bb.get("charged"),
                    "body_battery_drained": bb.get("drained"),
                    "source": "garmin",
                }
            )

        # Add HRV from Whoop if available
        if "recovery" in whoop_data and whoop_data["recovery"].get("hrv_ms"):
            recovery["hrv_ms"] = whoop_data["recovery"]["hrv_ms"]

        return recovery

    def _merge_activity(
        self, whoop_data: dict[str, Any], garmin_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge activity metrics (prefer Garmin)."""
        activity = {}

        # Garmin daily stats (more comprehensive)
        if "daily_stats" in garmin_data:
            gs = garmin_data["daily_stats"]
            activity.update(
                {
                    "steps": gs.get("steps"),
                    "distance_km": gs.get("distance_km"),
                    "calories": gs.get("calories"),
                    "active_minutes": gs.get("active_minutes"),
                    "floors_climbed": gs.get("floors_climbed"),
                    "source": "garmin",
                }
            )

        # Whoop strain
        if "strain" in whoop_data:
            ws = whoop_data["strain"]
            activity["strain_score"] = ws.get("score")
            activity["strain_calories"] = ws.get("calories")

        return activity

    def _merge_heart_rate(
        self, whoop_data: dict[str, Any], garmin_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge heart rate data."""
        hr = {}

        # Garmin HR data
        if "heart_rate" in garmin_data:
            ghr = garmin_data["heart_rate"]
            hr.update(
                {
                    "resting": ghr.get("resting_hr"),
                    "max": ghr.get("max_hr"),
                    "min": ghr.get("min_hr"),
                }
            )

        # Override resting HR with Whoop if available (more accurate)
        if "recovery" in whoop_data and whoop_data["recovery"].get("resting_hr"):
            hr["resting"] = whoop_data["recovery"]["resting_hr"]

        return hr

    def _merge_workouts(
        self, whoop_data: dict[str, Any], garmin_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Merge workouts from both sources."""
        workouts = []

        # Garmin activities
        if "activities" in garmin_data:
            for a in garmin_data["activities"]:
                workouts.append({**a, "source": "garmin"})

        # Whoop workouts
        if "workouts" in whoop_data:
            for w in whoop_data["workouts"]:
                workouts.append({**w, "source": "whoop"})

        return workouts


# Convenience function
async def get_health_summary(target_date: date | None = None) -> dict[str, Any]:
    """Get aggregated health summary."""
    async with HealthAggregator() as agg:
        return await agg.get_summary(target_date)
