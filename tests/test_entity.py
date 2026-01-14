"""Tests for Entity ABC."""

from unittest.mock import MagicMock

import pytest
from ucapi import media_player, sensor

from ucapi_framework.entity import Entity


class TestMediaPlayer(media_player.MediaPlayer, Entity):
    """Test media player with Entity ABC."""

    def __init__(self, entity_id, name):
        media_player.MediaPlayer.__init__(
            self,
            entity_id,
            name,
            features=[media_player.Features.ON_OFF],
            attributes={media_player.Attributes.STATE: media_player.States.UNKNOWN},
        )
        Entity.__init__(self)


class CustomStateMediaPlayer(media_player.MediaPlayer, Entity):
    """Media player with custom state mapping."""

    def __init__(self, entity_id, name):
        media_player.MediaPlayer.__init__(
            self,
            entity_id,
            name,
            features=[media_player.Features.ON_OFF],
            attributes={media_player.Attributes.STATE: media_player.States.UNKNOWN},
        )
        Entity.__init__(self)

    def map_entity_states(self, device_state):
        """Custom state mapping."""
        if device_state == "STREAM":
            return media_player.States.PLAYING
        elif device_state == "POWERING_ON":
            return media_player.States.ON
        return super().map_entity_states(device_state)


class TestSensor(sensor.Sensor, Entity):
    """Test sensor with Entity ABC."""

    def __init__(self, entity_id, name):
        sensor.Sensor.__init__(
            self,
            entity_id,
            name,
            features=[],
            attributes={
                sensor.Attributes.STATE: sensor.States.UNKNOWN,
                sensor.Attributes.VALUE: 0,
            },
        )
        Entity.__init__(self)


class TestEntityABC:
    """Test Entity ABC functionality."""

    def test_entity_lazy_initialization(self):
        """Test that Entity properties are initialized lazily."""
        entity = TestMediaPlayer("media_player.test", "Test Player")

        # Before accessing properties, internal state should be None
        assert entity._api is None
        assert entity._entity_id is None

        # Mock the ucapi.Entity parent attributes
        entity._integration_api = MagicMock()
        entity.id = "media_player.test"

        # Accessing properties should initialize them
        assert entity._framework_entity_id == "media_player.test"
        assert entity._entity_api is not None

    def test_entity_api_error_before_initialization(self):
        """Test that accessing _entity_api before initialization raises error."""
        entity = TestMediaPlayer("media_player.test", "Test Player")
        entity._api = None

        with pytest.raises(RuntimeError, match="Entity API not available"):
            _ = entity._entity_api

    def test_map_entity_states_default(self):
        """Test default state mapping behavior."""
        entity = TestMediaPlayer("media_player.test", "Test Player")

        # Test common state mappings
        assert (
            entity.map_entity_states("UNAVAILABLE") == media_player.States.UNAVAILABLE
        )
        assert entity.map_entity_states("UNKNOWN") == media_player.States.UNKNOWN
        assert entity.map_entity_states("ON") == media_player.States.ON
        assert entity.map_entity_states("MENU") == media_player.States.ON
        assert entity.map_entity_states("IDLE") == media_player.States.ON
        assert entity.map_entity_states("OFF") == media_player.States.OFF
        assert entity.map_entity_states("POWER_OFF") == media_player.States.OFF
        assert entity.map_entity_states("PLAYING") == media_player.States.PLAYING
        assert entity.map_entity_states("PLAY") == media_player.States.PLAYING
        assert entity.map_entity_states("PAUSED") == media_player.States.PAUSED
        assert entity.map_entity_states("STANDBY") == media_player.States.STANDBY
        assert entity.map_entity_states("BUFFERING") == media_player.States.BUFFERING

        # Test case insensitivity
        assert entity.map_entity_states("playing") == media_player.States.PLAYING
        assert entity.map_entity_states("off") == media_player.States.OFF

        # Test unknown state
        assert entity.map_entity_states("RANDOM_STATE") == media_player.States.UNKNOWN

        # Test None handling
        assert entity.map_entity_states(None) == media_player.States.UNKNOWN

    def test_map_entity_states_custom_override(self):
        """Test custom state mapping override."""
        entity = CustomStateMediaPlayer("media_player.custom", "Custom Player")

        # Test custom mappings
        assert entity.map_entity_states("STREAM") == media_player.States.PLAYING
        assert entity.map_entity_states("POWERING_ON") == media_player.States.ON

        # Test that default mappings still work
        assert entity.map_entity_states("OFF") == media_player.States.OFF
        assert entity.map_entity_states("PAUSED") == media_player.States.PAUSED

    def test_filter_changed_attributes(self):
        """Test attribute filtering."""
        entity = TestMediaPlayer("media_player.test", "Test Player")

        # Mock the API and configured entity
        mock_api = MagicMock()
        mock_configured_entity = MagicMock()
        mock_configured_entity.attributes = {
            media_player.Attributes.STATE: media_player.States.OFF,
            media_player.Attributes.VOLUME: 50,
        }
        mock_api.configured_entities.get.return_value = mock_configured_entity

        entity._integration_api = mock_api
        entity.id = "media_player.test"

        # Test filtering - only changed values should be returned
        update = {
            media_player.Attributes.STATE: media_player.States.PLAYING,  # Changed
            media_player.Attributes.VOLUME: 50,  # Unchanged
            media_player.Attributes.MUTED: False,  # New attribute
        }

        filtered = entity.filter_changed_attributes(update)
        assert filtered == {
            media_player.Attributes.STATE: media_player.States.PLAYING,
            media_player.Attributes.MUTED: False,
        }

    def test_filter_changed_attributes_entity_not_configured(self):
        """Test that filter returns all attributes if entity not configured."""
        entity = TestMediaPlayer("media_player.test", "Test Player")

        # Mock the API to return None for configured entity
        mock_api = MagicMock()
        mock_api.configured_entities.get.return_value = None

        entity._integration_api = mock_api
        entity.id = "media_player.test"

        update = {
            media_player.Attributes.STATE: media_player.States.PLAYING,
            media_player.Attributes.VOLUME: 75,
        }

        filtered = entity.filter_changed_attributes(update)
        # Should return all attributes if entity not found
        assert filtered == update

    def test_update_attributes_with_filtering(self):
        """Test update_attributes with automatic filtering."""
        entity = TestMediaPlayer("media_player.test", "Test Player")

        # Mock the API
        mock_api = MagicMock()
        mock_configured_entity = MagicMock()
        mock_configured_entity.attributes = {
            media_player.Attributes.STATE: media_player.States.OFF,
        }
        mock_api.configured_entities.get.return_value = mock_configured_entity

        entity._integration_api = mock_api
        entity.id = "media_player.test"

        # Update with mixed changed/unchanged attributes
        update = {
            media_player.Attributes.STATE: media_player.States.PLAYING,  # Changed
            media_player.Attributes.VOLUME: 50,  # New
        }

        entity.update_attributes(update)

        # Should only update changed attributes
        mock_api.configured_entities.update_attributes.assert_called_once_with(
            "media_player.test", update
        )

    def test_update_attributes_force(self):
        """Test update_attributes with force=True bypasses filtering."""
        entity = TestMediaPlayer("media_player.test", "Test Player")

        # Mock the API
        mock_api = MagicMock()
        entity._integration_api = mock_api
        entity.id = "media_player.test"

        # Update with force=True should skip filtering
        update = {
            media_player.Attributes.STATE: media_player.States.PLAYING,
            media_player.Attributes.VOLUME: 50,
        }

        entity.update_attributes(update, force=True)

        # Should update all attributes without calling filter
        mock_api.configured_entities.update_attributes.assert_called_once_with(
            "media_player.test", update
        )

    def test_multiple_entity_types(self):
        """Test that Entity ABC works with different entity types."""
        # Test with sensor
        sensor_entity = TestSensor("sensor.test", "Test Sensor")
        assert sensor_entity.map_entity_states("ON") == media_player.States.ON

        # Test with media player
        mp_entity = TestMediaPlayer("media_player.test", "Test Player")
        assert mp_entity.map_entity_states("PLAYING") == media_player.States.PLAYING

        # Both should have the same Entity ABC methods
        assert hasattr(sensor_entity, "filter_changed_attributes")
        assert hasattr(mp_entity, "filter_changed_attributes")
        assert hasattr(sensor_entity, "update_attributes")
        assert hasattr(mp_entity, "update_attributes")
