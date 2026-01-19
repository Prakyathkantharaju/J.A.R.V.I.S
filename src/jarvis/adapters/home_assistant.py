"""Home Assistant adapter for smart home control and location."""

from datetime import date
from typing import Any

from jarvis.config.settings import settings
from jarvis.adapters.base import AuthenticationError, BaseAdapter, FetchError

try:
    from homeassistant_api import Client

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False


class HomeAssistantAdapter(BaseAdapter):
    """Adapter for Home Assistant smart home platform.

    Features:
    - Device control (lights, switches, etc.)
    - Sensor readings
    - Location tracking (via HA Companion App)
    - TTS to speakers
    - Automation triggers
    """

    def __init__(self) -> None:
        super().__init__("home_assistant")
        self._client: Any = None

    async def connect(self) -> bool:
        """Connect to Home Assistant API."""
        if not HA_AVAILABLE:
            self.logger.warning(
                "homeassistant-api not installed. Run: uv add homeassistant-api"
            )
            return False

        try:
            url = settings.home_assistant.url
            token = settings.home_assistant.token.get_secret_value()

            if not url or not token:
                self.logger.warning("Home Assistant credentials not configured")
                return False

            # Ensure URL ends with /api for the homeassistant-api library
            api_url = url.rstrip("/") + "/api"
            self._client = Client(api_url, token)
            # Verify connection
            self._client.get_config()
            self._connected = True
            self.logger.info("Connected to Home Assistant", url=url)
            return True

        except Exception as e:
            self.logger.error("Failed to connect to Home Assistant", error=str(e))
            raise AuthenticationError(self.name, f"Connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Home Assistant."""
        self._client = None
        self._connected = False
        self.logger.info("Disconnected from Home Assistant")

    async def health_check(self) -> bool:
        """Check if Home Assistant connection is healthy."""
        if not self._client:
            return False
        try:
            self._client.get_config()
            return True
        except Exception:
            return False

    async def fetch(
        self,
        start_date: date,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch Home Assistant state data.

        Args:
            start_date: Not used (HA is real-time)
            end_date: Not used
            **kwargs:
                - entity_ids: list[str] - specific entities to fetch

        Returns:
            Dictionary with current states.
        """
        if not self._client:
            raise FetchError(self.name, "Not connected")

        try:
            entity_ids = kwargs.get("entity_ids", [])

            if entity_ids:
                states = {
                    eid: self._get_entity_state(eid) for eid in entity_ids
                }
            else:
                # Get all states
                all_states = self._client.get_states()
                states = {
                    state.entity_id: {
                        "state": state.state,
                        "attributes": state.attributes,
                        "last_changed": str(state.last_changed),
                    }
                    for state in all_states
                }

            return {
                "date": date.today().isoformat(),
                "source": "home_assistant",
                "states": states,
            }

        except Exception as e:
            self.logger.error("Failed to fetch Home Assistant states", error=str(e))
            raise FetchError(self.name, f"Fetch failed: {e}") from e

    def _get_entity_state(self, entity_id: str) -> dict[str, Any]:
        """Get state of a specific entity."""
        try:
            state = self._client.get_state(entity_id=entity_id)
            return {
                "state": state.state,
                "attributes": state.attributes,
                "last_changed": str(state.last_changed),
            }
        except Exception as e:
            return {"error": str(e)}

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        **service_data: Any,
    ) -> bool:
        """Call a Home Assistant service.

        Args:
            domain: Service domain (e.g., "light", "switch", "tts")
            service: Service name (e.g., "turn_on", "turn_off", "speak")
            entity_id: Target entity (optional)
            **service_data: Additional service data

        Returns:
            True if service call succeeded.
        """
        if not self._client:
            raise FetchError(self.name, "Not connected")

        try:
            data = dict(service_data)
            if entity_id:
                data["entity_id"] = entity_id

            self._client.trigger_service(domain, service, **data)
            self.logger.info(
                "Called Home Assistant service",
                domain=domain,
                service=service,
                entity_id=entity_id,
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to call service",
                domain=domain,
                service=service,
                error=str(e),
            )
            return False

    # Convenience methods for common operations

    async def turn_on(self, entity_id: str, **kwargs: Any) -> bool:
        """Turn on an entity (light, switch, etc.)."""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "turn_on", entity_id, **kwargs)

    async def turn_off(self, entity_id: str) -> bool:
        """Turn off an entity."""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "turn_off", entity_id)

    async def toggle(self, entity_id: str) -> bool:
        """Toggle an entity."""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "toggle", entity_id)

    async def speak(self, message: str, entity_id: str = "media_player.living_room") -> bool:
        """Speak a message via TTS.

        Args:
            message: Text to speak
            entity_id: Media player entity to use for TTS
        """
        return await self.call_service(
            "tts",
            "speak",
            entity_id=entity_id,
            message=message,
        )

    async def get_location(self, person_entity: str = "person.prakyath") -> dict[str, Any]:
        """Get location of a person entity."""
        if not self._client:
            raise FetchError(self.name, "Not connected")

        try:
            state = self._client.get_state(entity_id=person_entity)
            return {
                "state": state.state,  # "home", "not_home", or zone name
                "latitude": state.attributes.get("latitude"),
                "longitude": state.attributes.get("longitude"),
                "gps_accuracy": state.attributes.get("gps_accuracy"),
                "source": state.attributes.get("source"),
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_devices_by_area(self, area: str) -> list[dict[str, Any]]:
        """Get all devices in a specific area."""
        if not self._client:
            raise FetchError(self.name, "Not connected")

        # Filter states by area (requires area attribute)
        all_states = self._client.get_states()
        devices = []

        for state in all_states:
            if state.attributes.get("area_id") == area or area.lower() in str(
                state.attributes
            ).lower():
                devices.append(
                    {
                        "entity_id": state.entity_id,
                        "state": state.state,
                        "friendly_name": state.attributes.get("friendly_name"),
                    }
                )

        return devices

    async def set_climate(
        self,
        entity_id: str,
        temperature: float,
        hvac_mode: str | None = None,
    ) -> bool:
        """Set climate/thermostat settings."""
        data: dict[str, Any] = {"temperature": temperature}
        if hvac_mode:
            data["hvac_mode"] = hvac_mode
        return await self.call_service("climate", "set_temperature", entity_id, **data)


# Convenience functions
async def control_device(entity_id: str, action: str, **kwargs: Any) -> bool:
    """Control a Home Assistant device."""
    async with HomeAssistantAdapter() as adapter:
        if action == "on":
            return await adapter.turn_on(entity_id, **kwargs)
        elif action == "off":
            return await adapter.turn_off(entity_id)
        elif action == "toggle":
            return await adapter.toggle(entity_id)
        else:
            return False


async def speak_message(message: str, speaker: str = "media_player.living_room") -> bool:
    """Speak a message via Home Assistant TTS."""
    async with HomeAssistantAdapter() as adapter:
        return await adapter.speak(message, speaker)


async def get_my_location() -> dict[str, Any]:
    """Get current location from Home Assistant."""
    async with HomeAssistantAdapter() as adapter:
        return await adapter.get_location()
