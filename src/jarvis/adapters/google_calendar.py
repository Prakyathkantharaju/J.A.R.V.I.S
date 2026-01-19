"""Google Calendar adapter for personal events."""

from datetime import date, datetime, timedelta
from typing import Any

from jarvis.config.settings import settings
from jarvis.adapters.base import AuthenticationError, BaseAdapter, FetchError

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


# Scopes required for calendar access
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendarAdapter(BaseAdapter):
    """Adapter for Google Calendar events.

    Fetches:
    - Calendar events for date range
    - Event details (title, time, location, attendees)
    - All-day events vs timed events
    """

    def __init__(self) -> None:
        super().__init__("google_calendar")
        self._service: Any = None
        self._credentials: Any = None

    async def connect(self) -> bool:
        """Connect to Google Calendar API using OAuth."""
        if not GOOGLE_AVAILABLE:
            self.logger.warning(
                "Google API libraries not installed. "
                "Run: uv add google-api-python-client google-auth-oauthlib"
            )
            return False

        try:
            creds = None
            token_file = settings.google.token_file.expanduser()
            credentials_file = settings.google.credentials_file.expanduser()

            # Load existing token
            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not credentials_file.exists():
                        self.logger.error(
                            "Google credentials file not found",
                            path=str(credentials_file),
                        )
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save token for next time
                token_file.parent.mkdir(parents=True, exist_ok=True)
                token_file.write_text(creds.to_json())

            self._credentials = creds
            self._service = build("calendar", "v3", credentials=creds)
            self._connected = True
            self.logger.info("Connected to Google Calendar")
            return True

        except Exception as e:
            self.logger.error("Failed to connect to Google Calendar", error=str(e))
            raise AuthenticationError(self.name, f"OAuth failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Google Calendar."""
        self._service = None
        self._credentials = None
        self._connected = False
        self.logger.info("Disconnected from Google Calendar")

    async def health_check(self) -> bool:
        """Check if Google Calendar connection is healthy."""
        if not self._service:
            return False
        try:
            self._service.calendarList().list(maxResults=1).execute()
            return True
        except Exception:
            return False

    async def fetch(
        self,
        start_date: date,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch Google Calendar events for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)
            **kwargs:
                - calendar_id: str (default "primary")
                - max_results: int (default 50)

        Returns:
            Dictionary with calendar events.
        """
        if not self._service:
            raise FetchError(self.name, "Not connected")

        end_date = end_date or start_date
        calendar_id = kwargs.get("calendar_id", "primary")
        max_results = kwargs.get("max_results", 50)

        try:
            # Convert dates to RFC3339 timestamps
            time_min = datetime.combine(start_date, datetime.min.time()).isoformat() + "Z"
            time_max = datetime.combine(
                end_date + timedelta(days=1), datetime.min.time()
            ).isoformat() + "Z"

            events_result = (
                self._service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            data: dict[str, Any] = {
                "date": start_date.isoformat(),
                "source": "google_calendar",
                "events": [],
            }

            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                # Determine if all-day event
                is_all_day = "date" in event["start"]

                event_data = {
                    "id": event.get("id"),
                    "title": event.get("summary", "No Title"),
                    "start": start,
                    "end": end,
                    "all_day": is_all_day,
                    "location": event.get("location"),
                    "description": event.get("description"),
                    "status": event.get("status"),
                    "attendees": [
                        {
                            "email": a.get("email"),
                            "response": a.get("responseStatus"),
                        }
                        for a in event.get("attendees", [])
                    ],
                    "meeting_link": event.get("hangoutLink"),
                    "calendar": "personal",
                }
                data["events"].append(event_data)

            self.logger.info(
                "Fetched Google Calendar events",
                date=start_date.isoformat(),
                count=len(data["events"]),
            )
            return data

        except Exception as e:
            self.logger.error("Failed to fetch Google Calendar events", error=str(e))
            raise FetchError(self.name, f"Fetch failed: {e}") from e

    async def get_upcoming(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get upcoming events in the next N hours."""
        if not self._service:
            raise FetchError(self.name, "Not connected")

        now = datetime.utcnow()
        end = now + timedelta(hours=hours)

        data = await self.fetch(now.date(), end.date())
        return data.get("events", [])


# Convenience function
async def get_google_calendar_events(target_date: date | None = None) -> dict[str, Any]:
    """Fetch Google Calendar events for a specific date."""
    target_date = target_date or date.today()
    async with GoogleCalendarAdapter() as adapter:
        return await adapter.fetch(target_date)
