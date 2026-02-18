"""JARVIS API server for dashboard and integrations."""

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from jarvis.adapters.garmin import GarminAdapter
from jarvis.adapters.google_calendar import GoogleCalendarAdapter
from jarvis.adapters.home_assistant import HomeAssistantAdapter
from jarvis.adapters.obsidian import ObsidianAdapter
from jarvis.adapters.outlook import OutlookAdapter
from jarvis.adapters.whoop import WhoopAdapter
from jarvis.aggregators.daily import DailyAggregator

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup: Initialize database
    try:
        from jarvis.db import init_db

        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("Database initialization failed", error=str(e))

    yield

    # Shutdown: Close database connections
    try:
        from jarvis.db import close_db

        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning("Database shutdown failed", error=str(e))


app = FastAPI(
    title="JARVIS API",
    description="Personal AI Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def dashboard() -> HTMLResponse:
    """Serve the dashboard HTML."""
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text())
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


@app.get("/api/briefing")
async def get_briefing() -> dict[str, Any]:
    """Get morning briefing data."""
    try:
        async with DailyAggregator() as agg:
            return await agg.get_morning_briefing()
    except Exception as e:
        logger.error("Failed to get briefing", error=str(e))
        return {"error": str(e)}


@app.get("/api/health")
async def get_health(
    target_date: date | None = Query(
        None,
        alias="date",
        description="Date to fetch health data for (YYYY-MM-DD). Defaults to today.",
    ),
) -> dict[str, Any]:
    """Get health data from Whoop and Garmin.

    For historical dates, returns cached data if available.
    """
    from jarvis.aggregators.health import HealthAggregator

    target_date = target_date or date.today()

    try:
        async with HealthAggregator() as agg:
            return await agg.get_summary(target_date)
    except Exception as e:
        logger.error("Failed to get health data", error=str(e))
        return {"error": str(e)}


@app.get("/api/calendar")
async def get_calendar(
    target_date: date | None = Query(
        None,
        alias="date",
        description="Date to fetch calendar events for (YYYY-MM-DD). Defaults to today.",
    ),
) -> dict[str, Any]:
    """Get calendar events for a specific date."""
    from jarvis.aggregators.calendar import CalendarAggregator

    target_date = target_date or date.today()

    try:
        async with CalendarAggregator() as agg:
            return await agg.get_merged_events(target_date)
    except Exception as e:
        logger.error("Failed to get calendar", error=str(e))
        return {"error": str(e)}


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    """Get adapter connection status."""
    adapters = {
        "whoop": WhoopAdapter(),
        "garmin": GarminAdapter(),
        "google_calendar": GoogleCalendarAdapter(),
        "outlook": OutlookAdapter(),
        "obsidian": ObsidianAdapter(),
        "home_assistant": HomeAssistantAdapter(),
    }

    status = {}
    for name, adapter in adapters.items():
        try:
            connected = await adapter.connect()
            status[name] = {
                "connected": connected,
                "status": "online" if connected else "offline",
            }
            await adapter.disconnect()
        except Exception as e:
            status[name] = {
                "connected": False,
                "status": "error",
                "error": str(e),
            }

    return {"adapters": status, "timestamp": date.today().isoformat()}


from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Chat request model for OpenClaw integration."""

    message: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str
    user_id: str | None = None


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Chat with Clawd AI assistant.

    This endpoint is used by OpenClaw for WhatsApp integration.
    """
    from jarvis.clawd import run_clawd

    try:
        response = await run_clawd(
            request.message,
            source="whatsapp",
            user_id=request.user_id,
        )
        return ChatResponse(response=response, user_id=request.user_id)
    except Exception as e:
        logger.error("Chat failed", error=str(e))
        return ChatResponse(
            response=f"Sorry, I encountered an error: {str(e)}",
            user_id=request.user_id,
        )


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the API server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
