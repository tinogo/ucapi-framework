"""
Common entity interface for UC API integrations.

:copyright: (c) 2025 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from abc import ABC
from typing import Any

from ucapi import IntegrationAPI, media_player


def map_state_to_media_player(device_state: Any) -> media_player.States:
    """
    Map a device-specific state to media_player.States.

    This helper function provides the default state mapping logic used by both
    Entity.map_entity_states() and BaseIntegrationDriver.map_device_state().

    :param device_state: Device-specific state (string, enum, or any object with __str__)
    :return: Media player state
    """
    if device_state is None:
        return media_player.States.UNKNOWN

    # If already a media_player.States enum, return it directly
    if isinstance(device_state, media_player.States):
        return device_state

    # Convert to uppercase string for comparison
    state_str = str(device_state).upper()

    match state_str:
        case "UNAVAILABLE":
            return media_player.States.UNAVAILABLE
        case "UNKNOWN":
            return media_player.States.UNKNOWN
        case "ON" | "MENU" | "IDLE" | "ACTIVE" | "READY":
            return media_player.States.ON
        case "OFF" | "POWER_OFF" | "POWERED_OFF" | "STOPPED":
            return media_player.States.OFF
        case "PLAYING" | "PLAY" | "SEEKING":
            return media_player.States.PLAYING
        case "PAUSED" | "PAUSE":
            return media_player.States.PAUSED
        case "STANDBY" | "SLEEP":
            return media_player.States.STANDBY
        case "BUFFERING" | "LOADING":
            return media_player.States.BUFFERING
        case _:
            return media_player.States.UNKNOWN


# pylint: disable=R0903
class Entity(ABC):
    """
    Common interface for entities with custom behavior.

    This ABC provides optional per-entity customization of state mapping and
    attribute updates. Entities inheriting from this class will automatically
    use their custom methods when the driver processes updates.

    The _api and _entity_id attributes are set automatically by accessing
    the entity's properties inherited from ucapi.Entity (id and parent API).

    Example:
        class MyMediaPlayer(MediaPlayer, Entity):
            def __init__(self, entity_id, name, features, attributes, cmd_handler):
                super().__init__(entity_id, name, features, attributes, cmd_handler=cmd_handler)

            def map_entity_states(self, device_state):
                # Custom state mapping for this specific entity
                if device_state == "STREAM":
                    return media_player.States.PLAYING
                return super().map_entity_states(device_state)
    """

    def __init__(self):
        """Initialize the Entity ABC (called automatically via MRO)."""
        self._api: IntegrationAPI | None = None
        self._entity_id: str | None = None

    @property
    def _entity_api(self) -> IntegrationAPI:
        """Get the IntegrationAPI instance (lazy initialization from ucapi.Entity parent)."""
        if self._api is None:
            # Access the api from the ucapi.Entity parent class
            # The entity will have been added to available_entities or configured_entities
            if hasattr(self, "_integration_api"):
                self._api = self._integration_api  # type: ignore[assignment]
            else:
                raise RuntimeError(
                    "Entity API not available. Ensure entity is properly initialized "
                    "and added to the integration before using framework methods."
                )
        return self._api  # type: ignore[return-value]

    @property
    def _framework_entity_id(self) -> str:
        """Get the entity ID (lazy initialization from ucapi.Entity parent)."""
        if self._entity_id is None:
            # Access the id from the ucapi.Entity parent class
            if hasattr(self, "id"):
                self._entity_id = self.id  # type: ignore[assignment]
            else:
                raise RuntimeError(
                    "Entity ID not available. Ensure entity is properly initialized."
                )
        return self._entity_id  # type: ignore[return-value]

    def update_attributes(self, update: dict[str, Any], *, force: bool = False) -> None:
        """
        Update the entity attributes from the given device update.

        :param update: dictionary containing the updated properties.
        :param force: if True, update attributes even if they haven't changed.
        """
        if force:
            attributes = update
        else:
            attributes = self.filter_changed_attributes(update)

        if attributes:
            self._entity_api.configured_entities.update_attributes(
                self._framework_entity_id, attributes
            )

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes and return only the changed values.

        Compares each attribute in the update dict with the currently stored
        entity state in configured_entities and only returns attributes that
        have actually changed.

        :param update: dictionary containing the updated properties.
        :return: dictionary containing only the changed attributes.
        """
        configured_entity = self._entity_api.configured_entities.get(
            self._framework_entity_id
        )
        if not configured_entity:
            # Entity not found, return all attributes
            return update

        # Get current attributes from the configured entity
        current_attributes = configured_entity.attributes or {}

        # Return only changed values
        return {
            key: value
            for key, value in update.items()
            if current_attributes.get(key) != value
        }

    def map_entity_states(self, device_state: Any) -> Any:
        """
        Convert a device-specific state to a UC API entity state.

        DEFAULT IMPLEMENTATION: Uses map_state_to_media_player() helper to convert
        device_state to uppercase string and map common state values to media_player.States:

        - UNAVAILABLE → UNAVAILABLE
        - UNKNOWN → UNKNOWN
        - ON, MENU, IDLE, ACTIVE, READY → ON
        - OFF, POWER_OFF, POWERED_OFF, STOPPED → OFF
        - PLAYING, PLAY, SEEKING → PLAYING
        - PAUSED, PAUSE → PAUSED
        - STANDBY, SLEEP → STANDBY
        - BUFFERING, LOADING → BUFFERING
        - Everything else → UNKNOWN

        Override this method per entity type to customize state mapping for your device.

        Example override:
            class MyCustomMediaPlayer(MediaPlayer, Entity):
                def map_entity_states(self, device_state):
                    if isinstance(device_state, MyDeviceState):
                        match device_state:
                            case MyDeviceState.POWERED_ON:
                                return media_player.States.ON
                            case MyDeviceState.POWERED_OFF:
                                return media_player.States.OFF
                            case _:
                                return media_player.States.UNKNOWN
                    return super().map_entity_states(device_state)

        :param device_state: Device-specific state (string, enum, or any object with __str__)
        :return: UC API entity state (typically media_player.States)
        """
        return map_state_to_media_player(device_state)
