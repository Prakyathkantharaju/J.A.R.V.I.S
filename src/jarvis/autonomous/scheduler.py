"""Scheduler for autonomous JARVIS routines."""

import asyncio

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from jarvis.config.settings import settings

logger = structlog.get_logger()


class JARVISScheduler:
    """Manages scheduled tasks for JARVIS."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self) -> None:
        """Configure all scheduled jobs."""

        # Morning briefing at 6:30 AM
        self.scheduler.add_job(
            self._morning_briefing,
            CronTrigger(hour=6, minute=30),
            id="morning_briefing",
            name="Morning Briefing",
            replace_existing=True,
        )

        # Health check every 2 hours
        self.scheduler.add_job(
            self._health_check,
            IntervalTrigger(hours=2),
            id="health_check",
            name="Health Check",
            replace_existing=True,
        )

        # Evening reflection at 9:00 PM
        self.scheduler.add_job(
            self._evening_reflection,
            CronTrigger(hour=21, minute=0),
            id="evening_reflection",
            name="Evening Reflection",
            replace_existing=True,
        )

        # Data sync every 15 minutes
        self.scheduler.add_job(
            self._data_sync,
            IntervalTrigger(minutes=15),
            id="data_sync",
            name="Data Sync",
            replace_existing=True,
        )

        logger.info("Scheduled jobs configured")

    async def _morning_briefing(self) -> None:
        """Generate and deliver morning briefing."""
        logger.info("Running morning briefing")
        try:
            from jarvis.aggregators.daily import get_daily_briefing

            briefing = await get_daily_briefing()
            summary = briefing.get("summary", "Good morning!")

            # Speak the briefing
            from jarvis.adapters.home_assistant import speak_message

            await speak_message(summary)

            logger.info("Morning briefing delivered", summary=summary[:100])

        except Exception as e:
            logger.error("Morning briefing failed", error=str(e))

    async def _health_check(self) -> None:
        """Check health metrics for anomalies."""
        logger.info("Running health check")
        try:
            from jarvis.aggregators.health import get_health_summary

            health = await get_health_summary()

            # Check for anomalies
            recovery = health.get("recovery", {})
            hrv = recovery.get("hrv_ms")

            # Example: Alert if HRV drops significantly
            # In production, compare against personal baseline
            if hrv and hrv < 30:
                from jarvis.adapters.home_assistant import speak_message

                message = f"Health alert: Your HRV is at {hrv} milliseconds, which is lower than usual. Consider taking it easy today."
                await speak_message(message)
                logger.warning("Low HRV detected", hrv=hrv)

            logger.info("Health check complete", recovery=recovery.get("score"))

        except Exception as e:
            logger.error("Health check failed", error=str(e))

    async def _evening_reflection(self) -> None:
        """Generate and optionally deliver evening summary."""
        logger.info("Running evening reflection")
        try:
            from jarvis.aggregators.daily import get_evening_summary

            reflection = await get_evening_summary()
            summary = reflection.get("summary", "")

            # Optional: Speak the summary (configurable)
            # For now, just log it
            logger.info("Evening reflection generated", summary=summary[:100])

            # Could also write to Obsidian daily note
            from jarvis.adapters.obsidian import ObsidianAdapter
            from datetime import date

            async with ObsidianAdapter() as obsidian:
                await obsidian.append_to_daily_note(
                    date.today(),
                    "Evening Reflection",
                    f"\n{summary}\n",
                )

        except Exception as e:
            logger.error("Evening reflection failed", error=str(e))

    async def _data_sync(self) -> None:
        """Sync data from all sources."""
        logger.info("Running data sync")
        try:
            from jarvis.adapters import (
                GarminAdapter,
                GoogleCalendarAdapter,
                WhoopAdapter,
            )

            # Sync each adapter
            for adapter_class in [GarminAdapter, WhoopAdapter, GoogleCalendarAdapter]:
                try:
                    adapter = adapter_class()
                    if await adapter.connect():
                        await adapter.fetch_today()
                        await adapter.disconnect()
                        logger.debug(f"Synced {adapter.name}")
                except Exception as e:
                    logger.warning(f"Failed to sync {adapter_class.__name__}", error=str(e))

            logger.info("Data sync complete")

        except Exception as e:
            logger.error("Data sync failed", error=str(e))

    def start(self) -> None:
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("JARVIS scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("JARVIS scheduler stopped")


def start_scheduler() -> None:
    """Entry point for scheduler service."""
    import signal
    import sys

    scheduler = JARVISScheduler()
    scheduler.start()

    # Handle shutdown signals
    def shutdown(sig: int, frame: object) -> None:
        logger.info("Shutting down scheduler...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Run event loop
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()


if __name__ == "__main__":
    start_scheduler()
