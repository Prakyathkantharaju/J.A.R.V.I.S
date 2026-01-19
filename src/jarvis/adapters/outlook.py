"""Microsoft Outlook adapter for work calendar via Graph API."""

from datetime import date, datetime, timedelta
from typing import Any

from jarvis.config.settings import settings
from jarvis.adapters.base import AuthenticationError, BaseAdapter, FetchError

try:
    import msal

    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False


# Microsoft Graph API scopes
SCOPES = ["Calendars.Read", "User.Read"]
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"


class OutlookAdapter(BaseAdapter):
    """Adapter for Microsoft Outlook/365 calendar via Graph API.

    Fetches:
    - Calendar events for date range
    - Meeting details (Teams links, attendees)
    - Work calendar integration
    """

    def __init__(self) -> None:
        super().__init__("outlook")
        self._app: Any = None
        self._token: dict[str, Any] | None = None

    async def connect(self) -> bool:
        """Connect to Microsoft Graph API using OAuth."""
        if not MSAL_AVAILABLE:
            self.logger.warning("MSAL library not installed. Run: uv add msal")
            return False

        try:
            client_id = settings.microsoft.client_id
            client_secret = settings.microsoft.client_secret.get_secret_value()
            tenant_id = settings.microsoft.tenant_id

            if not client_id or not client_secret:
                self.logger.warning("Microsoft credentials not configured")
                return False

            # Create MSAL application
            authority = f"https://login.microsoftonline.com/{tenant_id}"
            self._app = msal.ConfidentialClientApplication(
                client_id,
                authority=authority,
                client_credential=client_secret,
            )

            # Try to acquire token
            result = self._app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

            if "access_token" in result:
                self._token = result
                self._connected = True
                self.logger.info("Connected to Microsoft Graph API")
                return True
            else:
                error = result.get("error_description", "Unknown error")
                self.logger.error("Failed to acquire token", error=error)
                return False

        except Exception as e:
            self.logger.error("Failed to connect to Outlook", error=str(e))
            raise AuthenticationError(self.name, f"OAuth failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Microsoft Graph API."""
        self._app = None
        self._token = None
        self._connected = False
        self.logger.info("Disconnected from Microsoft Graph API")

    async def health_check(self) -> bool:
        """Check if Outlook connection is healthy."""
        if not self._token:
            return False
        try:
            import httpx

            headers = {"Authorization": f"Bearer {self._token['access_token']}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{GRAPH_API_ENDPOINT}/me", headers=headers)
                return response.status_code == 200
        except Exception:
            return False

    async def fetch(
        self,
        start_date: date,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch Outlook calendar events for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)

        Returns:
            Dictionary with calendar events.
        """
        if not self._token:
            raise FetchError(self.name, "Not connected")

        end_date = end_date or start_date

        try:
            import httpx

            # Format dates for Graph API
            start_dt = datetime.combine(start_date, datetime.min.time()).isoformat() + "Z"
            end_dt = datetime.combine(
                end_date + timedelta(days=1), datetime.min.time()
            ).isoformat() + "Z"

            headers = {"Authorization": f"Bearer {self._token['access_token']}"}
            params = {
                "startDateTime": start_dt,
                "endDateTime": end_dt,
                "$orderby": "start/dateTime",
                "$top": 50,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GRAPH_API_ENDPOINT}/me/calendarView",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                events_data = response.json()

            events = events_data.get("value", [])

            data: dict[str, Any] = {
                "date": start_date.isoformat(),
                "source": "outlook",
                "events": [],
            }

            for event in events:
                # Determine if all-day event
                is_all_day = event.get("isAllDay", False)

                event_data = {
                    "id": event.get("id"),
                    "title": event.get("subject", "No Title"),
                    "start": event.get("start", {}).get("dateTime"),
                    "end": event.get("end", {}).get("dateTime"),
                    "all_day": is_all_day,
                    "location": event.get("location", {}).get("displayName"),
                    "description": event.get("bodyPreview"),
                    "status": event.get("showAs"),
                    "is_online": event.get("isOnlineMeeting", False),
                    "meeting_link": event.get("onlineMeeting", {}).get("joinUrl")
                    if event.get("isOnlineMeeting")
                    else None,
                    "attendees": [
                        {
                            "email": a.get("emailAddress", {}).get("address"),
                            "name": a.get("emailAddress", {}).get("name"),
                            "response": a.get("status", {}).get("response"),
                        }
                        for a in event.get("attendees", [])
                    ],
                    "organizer": event.get("organizer", {})
                    .get("emailAddress", {})
                    .get("address"),
                    "calendar": "work",
                }
                data["events"].append(event_data)

            self.logger.info(
                "Fetched Outlook events",
                date=start_date.isoformat(),
                count=len(data["events"]),
            )
            return data

        except Exception as e:
            self.logger.error("Failed to fetch Outlook events", error=str(e))
            raise FetchError(self.name, f"Fetch failed: {e}") from e


# Convenience function
async def get_outlook_events(target_date: date | None = None) -> dict[str, Any]:
    """Fetch Outlook events for a specific date."""
    target_date = target_date or date.today()
    async with OutlookAdapter() as adapter:
        return await adapter.fetch(target_date)
