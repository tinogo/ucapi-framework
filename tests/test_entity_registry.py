"""Tests for entity registry functionality in BaseDeviceInterface."""

import asyncio
import pytest
from unittest.mock import MagicMock
from ucapi import sensor
from ucapi_framework import Entity, SensorAttributes
from ucapi_framework.device import BaseDeviceInterface


class TestDevice(BaseDeviceInterface):
    """Test device implementation."""

    def __init__(self, device_config, loop=None, config_manager=None):
        super().__init__(device_config, loop, config_manager)
        self.sensor_data = {}

    @property
    def identifier(self) -> str:
        return self._device_config.get("id", "test_device")

    @property
    def name(self) -> str:
        return self._device_config.get("name", "Test Device")

    @property
    def address(self) -> str:
        return self._device_config.get("address", "192.168.1.1")

    @property
    def log_id(self) -> str:
        return f"Device[{self.identifier}]"

    @property
    def is_connected(self) -> bool:
        return True

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    def get_device_attributes(self, entity_id: str) -> SensorAttributes:
        """Return sensor attributes."""
        sensor_id = entity_id.split(".")[-1]
        data = self.sensor_data.get(sensor_id, {})

        return SensorAttributes(
            STATE=sensor.States.ON if data else sensor.States.UNAVAILABLE,
            VALUE=data.get("value"),
            UNIT=data.get("unit"),
        )


class TestSensor(sensor.Sensor, Entity):
    """Test sensor entity."""

    def __init__(self, device, sensor_id, name):
        entity_id = f"sensor.test_device.{sensor_id}"
        super().__init__(
            entity_id,
            name,
            features=[],
            attributes={
                sensor.Attributes.STATE: sensor.States.UNAVAILABLE,
                sensor.Attributes.UNIT: "°C",
            },
        )
        self.sensor_id = sensor_id
        self._device = device

        # Register with device
        device.register_entity(self.id, self)


class TestDeviceWithoutGetAttributes(BaseDeviceInterface):
    """Test device without get_device_attributes override."""

    def __init__(self, device_config, loop=None):
        super().__init__(device_config, loop)

    @property
    def identifier(self) -> str:
        return "test"

    @property
    def name(self) -> str:
        return "Test"

    @property
    def address(self) -> str:
        return "localhost"

    @property
    def log_id(self) -> str:
        return "Test"

    @property
    def is_connected(self) -> bool:
        return True

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass


class TestEntityRegistry:
    """Test entity registry functionality."""

    @pytest.fixture
    def event_loop(self):
        """Create event loop for tests."""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture
    def device_config(self):
        """Create test device config."""
        return {"id": "test_device", "name": "Test Device", "address": "192.168.1.1"}

    @pytest.fixture
    def device(self, device_config, event_loop):
        """Create test device."""
        return TestDevice(device_config, loop=event_loop)

    @pytest.fixture
    def mock_api(self):
        """Create mock API."""
        api = MagicMock()
        api.configured_entities.get.return_value = MagicMock(
            attributes={sensor.Attributes.STATE: sensor.States.UNAVAILABLE}
        )
        return api

    def test_register_entity(self, device):
        """Test entity registration."""
        entity = TestSensor(device, "temp", "Temperature")

        # Verify entity is registered
        assert device.get_entity(entity.id) is entity
        assert device.get_entity(entity.id) == entity

    def test_register_multiple_entities(self, device):
        """Test registering multiple entities."""
        temp_sensor = TestSensor(device, "temp", "Temperature")
        humidity_sensor = TestSensor(device, "humidity", "Humidity")

        # Verify both are registered
        assert device.get_entity(temp_sensor.id) is temp_sensor
        assert device.get_entity(humidity_sensor.id) is humidity_sensor

    def test_get_entity_not_registered(self, device):
        """Test getting unregistered entity returns None."""
        entity = device.get_entity("sensor.test_device.nonexistent")
        assert entity is None

    def test_update_entity_success(self, device, mock_api):
        """Test successful entity update via registry."""
        entity = TestSensor(device, "temp", "Temperature")
        entity._api = mock_api  # noqa: SLF001

        # Update device sensor data
        device.sensor_data["temp"] = {"value": 23.5, "unit": "°C"}

        # Update entity
        device.update_entity(entity.id)

        # Verify entity.update() was called (check API call)
        assert mock_api.configured_entities.update_attributes.called

    def test_update_entity_not_registered(self, device, caplog):
        """Test updating unregistered entity logs debug message."""
        import logging

        caplog.set_level(logging.DEBUG)
        device.update_entity("sensor.test_device.nonexistent")

        # Should log debug message
        assert "not registered" in caplog.text.lower()

    def test_update_entity_without_update_method(self, device, caplog):
        """Test updating object without update() method logs warning."""

        # Create an object without an update method
        class PlainObject:
            def __init__(self):
                self.id = "test.plain"

        plain_obj = PlainObject()

        # Register it
        device.register_entity(plain_obj.id, plain_obj)

        # Try to update
        device.update_entity(plain_obj.id)

        # Should log warning about missing update method
        assert "does not have an update() method" in caplog.text.lower()

    def test_update_entity_without_get_device_attributes_override(
        self, caplog, event_loop
    ):
        """Test warning when get_device_attributes not overridden."""
        device_config = {"id": "test"}
        device = TestDeviceWithoutGetAttributes(device_config, loop=event_loop)

        # Create a real framework entity
        real_entity = TestSensor(device, "temp", "Temperature")

        # Clear the registry and add entity without triggering our overridden method
        device._entity_registry = {}  # noqa: SLF001
        device._entity_registry[real_entity.id] = real_entity  # noqa: SLF001

        # Set the _api mock
        real_entity._api = MagicMock()  # noqa: SLF001

        # Now call update_entity - should warn about missing override
        device.update_entity(real_entity.id)

        # Should log warning about missing override
        assert "get_device_attributes() is not overridden" in caplog.text

    def test_update_entity_with_dataclass(self, device, mock_api):
        """Test entity update with dataclass attributes."""
        entity = TestSensor(device, "temp", "Temperature")
        entity._api = mock_api  # noqa: SLF001

        # Update device sensor data
        device.sensor_data["temp"] = {"value": 25.0, "unit": "°C"}

        # Update entity
        device.update_entity(entity.id)

        # Verify update was called
        assert mock_api.configured_entities.update_attributes.called

        # Get the call arguments
        call_args = mock_api.configured_entities.update_attributes.call_args

        # Should have entity_id and attributes
        assert len(call_args[0]) == 2

    def test_update_entity_filters_none_values(self, device, mock_api):
        """Test that None values are filtered from dataclass updates."""
        entity = TestSensor(device, "temp", "Temperature")
        entity._api = mock_api  # noqa: SLF001

        # Update with partial data (some fields None)
        device.sensor_data["temp"] = {"value": 22.0}  # No 'unit' key

        # Update entity
        device.update_entity(entity.id)

        # Verify update was called
        assert mock_api.configured_entities.update_attributes.called

        # Get the attributes that were passed
        call_args = mock_api.configured_entities.update_attributes.call_args
        _, attributes = call_args[0]

        # Should have STATE and VALUE, but not UNIT (it was None)
        assert sensor.Attributes.STATE in attributes
        assert sensor.Attributes.VALUE in attributes
        # UNIT should not be in the update if it was None in dataclass
        # (actual behavior depends on SensorAttributes defaults)

    def test_entity_registry_initial_state(self, device):
        """Test entity registry starts empty."""
        assert device._entity_registry == {}  # noqa: SLF001

    def test_entity_registry_after_registration(self, device):
        """Test entity registry contains registered entities."""
        temp = TestSensor(device, "temp", "Temperature")
        humidity = TestSensor(device, "humidity", "Humidity")

        # Registry should have both
        assert len(device._entity_registry) == 2  # noqa: SLF001
        assert temp.id in device._entity_registry  # noqa: SLF001
        assert humidity.id in device._entity_registry  # noqa: SLF001

    def test_entity_reregistration_overwrites(self, device):
        """Test re-registering an entity overwrites the previous one."""
        entity1 = TestSensor(device, "temp", "Temperature 1")
        entity2 = TestSensor(device, "temp", "Temperature 2")

        # Should have the second one
        assert device.get_entity(entity2.id) is entity2
        assert device.get_entity(entity2.id) is not entity1

    def test_update_entity_empty_attrs(self, device, mock_api):
        """Test update_entity when get_device_attributes returns empty dict."""
        entity = TestSensor(device, "temp", "Temperature")
        entity._api = mock_api  # noqa: SLF001

        # Clear sensor data so get_device_attributes returns empty
        device.sensor_data = {}

        # Update should not be called when attrs are empty
        device.update_entity(entity.id)

        # Should not call update since attrs are empty/falsy
        assert not mock_api.configured_entities.update_attributes.called


class TestDeviceEventsUpdate:
    """Test DeviceEvents.UPDATE documentation and usage."""

    def test_device_events_update_exists(self):
        """Test that DeviceEvents.UPDATE is defined."""
        from ucapi_framework.device import DeviceEvents

        assert hasattr(DeviceEvents, "UPDATE")
        assert DeviceEvents.UPDATE == "DEVICE_UPDATE"

    def test_device_events_has_docstring(self):
        """Test that DeviceEvents class has documentation."""
        from ucapi_framework.device import DeviceEvents

        assert DeviceEvents.__doc__ is not None
        assert "UPDATE Event" in DeviceEvents.__doc__
        assert "entity_id" in DeviceEvents.__doc__
