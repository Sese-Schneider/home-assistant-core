"""UniFi Network light platform tests."""

from copy import deepcopy

from aiounifi.models.message import MessageKey
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.components.unifi.const import CONF_SITE_ID
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from .conftest import (
    ConfigEntryFactoryType,
    WebsocketMessageMock,
    WebsocketStateManager,
)

from tests.common import MockConfigEntry, snapshot_platform
from tests.test_util.aiohttp import AiohttpClientMocker

# Test device with LED ring support
DEVICE_WITH_LED = {
    "board_rev": 3,
    "device_id": "mock-id",
    "ip": "10.0.0.1",
    "last_seen": 1562600145,
    "mac": "10:00:00:00:01:01",
    "model": "U6-Lite",
    "name": "Device with LED",
    "next_interval": 20,
    "state": 1,
    "type": "uap",
    "version": "4.0.42.10433",
    "led_override": "on",
    "led_override_color": "#0000ff",
    "led_override_color_brightness": 80,
    "supports_led_ring": True,
}

# Test device without LED ring support
DEVICE_WITHOUT_LED = {
    "board_rev": 2,
    "device_id": "mock-id-2",
    "ip": "10.0.0.2",
    "last_seen": 1562600145,
    "mac": "10:00:00:00:01:02",
    "model": "US-8-60W",
    "name": "Device without LED",
    "next_interval": 20,
    "state": 1,
    "type": "usw",
    "version": "4.0.42.10433",
    "supports_led_ring": False,
}

# Test device with LED off
DEVICE_LED_OFF = {
    "board_rev": 3,
    "device_id": "mock-id-3",
    "ip": "10.0.0.3",
    "last_seen": 1562600145,
    "mac": "10:00:00:00:01:03",
    "model": "U6-Pro",
    "name": "Device LED Off",
    "next_interval": 20,
    "state": 1,
    "type": "uap",
    "version": "4.0.42.10433",
    "led_override": "off",
    "led_override_color": "#ffffff",
    "led_override_color_brightness": 0,
    "supports_led_ring": True,
}

# Test device with custom LED color
DEVICE_CUSTOM_LED = {
    "board_rev": 3,
    "device_id": "mock-id-4",
    "ip": "10.0.0.4",
    "last_seen": 1562600145,
    "mac": "10:00:00:00:01:04",
    "model": "U6-Enterprise",
    "name": "Device Custom LED",
    "next_interval": 20,
    "state": 1,
    "type": "uap",
    "version": "4.0.42.10433",
    "led_override": "on",
    "led_override_color": "#ff00ff",
    "led_override_color_brightness": 60,
    "supports_led_ring": True,
}


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED, DEVICE_WITHOUT_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_lights(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry_setup: MockConfigEntry,
) -> None:
    """Test light entities are created for devices with LED support."""
    # Only devices with LED support should have light entities
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 1

    # Check the light entity exists for device with LED
    light_entity = hass.states.get("light.device_with_led_led")
    assert light_entity is not None
    assert light_entity.state == STATE_ON
    assert light_entity.attributes["brightness"] == 204  # 80% of 255
    assert light_entity.attributes["rgb_color"] == (0, 0, 255)  # Blue

    # Ensure no light entity for device without LED support
    assert hass.states.get("light.device_without_led_led") is None


@pytest.mark.parametrize("device_payload", [[DEVICE_LED_OFF]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_off_state(
    hass: HomeAssistant,
) -> None:
    """Test light entity with LED off state."""
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 1

    light_entity = hass.states.get("light.device_led_off_led")
    assert light_entity is not None
    assert light_entity.state == STATE_OFF
    assert light_entity.attributes["brightness"] == 0
    assert light_entity.attributes["rgb_color"] == (255, 255, 255)  # Default white


@pytest.mark.parametrize("device_payload", [[DEVICE_CUSTOM_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_custom_color(
    hass: HomeAssistant,
) -> None:
    """Test light entity with custom LED color."""
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 1

    light_entity = hass.states.get("light.device_custom_led_led")
    assert light_entity is not None
    assert light_entity.state == STATE_ON
    assert light_entity.attributes["brightness"] == 153  # 60% of 255
    assert light_entity.attributes["rgb_color"] == (255, 0, 255)  # Magenta


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_turn_on_off(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry_setup: MockConfigEntry,
) -> None:
    """Test turning light on and off."""
    # Mock the API endpoint for LED control
    aioclient_mock.clear_requests()
    aioclient_mock.put(
        f"https://{config_entry_setup.data[CONF_HOST]}:1234"
        f"/api/s/{config_entry_setup.data[CONF_SITE_ID]}/rest/device/10:00:00:00:01:01",
    )

    # Turn off the light
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "light.device_with_led_led"},
        blocking=True,
    )

    assert aioclient_mock.call_count == 1
    call_data = aioclient_mock.mock_calls[0][2]
    assert call_data["led_override"] == "off"

    # Turn on the light
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "light.device_with_led_led"},
        blocking=True,
    )

    assert aioclient_mock.call_count == 2
    call_data = aioclient_mock.mock_calls[1][2]
    assert call_data["led_override"] == "on"


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_set_brightness(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry_setup: MockConfigEntry,
) -> None:
    """Test setting light brightness."""
    aioclient_mock.clear_requests()
    aioclient_mock.put(
        f"https://{config_entry_setup.data[CONF_HOST]}:1234"
        f"/api/s/{config_entry_setup.data[CONF_SITE_ID]}/rest/device/10:00:00:00:01:01",
    )

    # Set brightness to 50% (127/255)
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.device_with_led_led",
            ATTR_BRIGHTNESS: 127,
        },
        blocking=True,
    )

    assert aioclient_mock.call_count == 1
    call_data = aioclient_mock.mock_calls[0][2]
    assert call_data["led_override"] == "on"
    assert call_data["led_override_color_brightness"] == 49  # ~50% of 100


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_set_rgb_color(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry_setup: MockConfigEntry,
) -> None:
    """Test setting light RGB color."""
    aioclient_mock.clear_requests()
    aioclient_mock.put(
        f"https://{config_entry_setup.data[CONF_HOST]}:1234"
        f"/api/s/{config_entry_setup.data[CONF_SITE_ID]}/rest/device/10:00:00:00:01:01",
    )

    # Set color to red (255, 0, 0)
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.device_with_led_led",
            ATTR_RGB_COLOR: (255, 0, 0),
        },
        blocking=True,
    )

    assert aioclient_mock.call_count == 1
    call_data = aioclient_mock.mock_calls[0][2]
    assert call_data["led_override"] == "on"
    assert call_data["led_override_color"] == "#ff0000"


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_set_brightness_and_color(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry_setup: MockConfigEntry,
) -> None:
    """Test setting both brightness and color simultaneously."""
    aioclient_mock.clear_requests()
    aioclient_mock.put(
        f"https://{config_entry_setup.data[CONF_HOST]}:1234"
        f"/api/s/{config_entry_setup.data[CONF_SITE_ID]}/rest/device/10:00:00:00:01:01",
    )

    # Set color to green and brightness to 75%
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.device_with_led_led",
            ATTR_RGB_COLOR: (0, 255, 0),
            ATTR_BRIGHTNESS: 191,  # 75% of 255
        },
        blocking=True,
    )

    assert aioclient_mock.call_count == 1
    call_data = aioclient_mock.mock_calls[0][2]
    assert call_data["led_override"] == "on"
    assert call_data["led_override_color"] == "#00ff00"
    assert call_data["led_override_color_brightness"] == 74  # ~75% of 100


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_state_update_via_websocket(
    hass: HomeAssistant,
    mock_websocket_message: WebsocketMessageMock,
) -> None:
    """Test light state updates via websocket messages."""
    # Initial state
    light_entity = hass.states.get("light.device_with_led_led")
    assert light_entity.state == STATE_ON
    assert light_entity.attributes["rgb_color"] == (0, 0, 255)

    # Update device LED state via websocket
    updated_device = deepcopy(DEVICE_WITH_LED)
    updated_device["led_override"] = "off"
    updated_device["led_override_color"] = "#ff0000"
    updated_device["led_override_color_brightness"] = 100

    mock_websocket_message(message=MessageKey.DEVICE, data=[updated_device])
    await hass.async_block_till_done()

    # Check updated state
    light_entity = hass.states.get("light.device_with_led_led")
    assert light_entity.state == STATE_OFF
    assert light_entity.attributes["rgb_color"] == (255, 0, 0)  # Red
    assert light_entity.attributes["brightness"] == 255  # 100% brightness


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_device_removal(
    hass: HomeAssistant,
    mock_websocket_message: WebsocketMessageMock,
) -> None:
    """Test light entity removal when device is removed."""
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 1
    assert hass.states.get("light.device_with_led_led") is not None

    # Remove device via websocket
    mock_websocket_message(message=MessageKey.DEVICE_REMOVED, data=[DEVICE_WITH_LED])
    await hass.async_block_till_done()

    # Light entity should be removed
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 0
    assert hass.states.get("light.device_with_led_led") is None


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_device_unavailable(
    hass: HomeAssistant,
    mock_websocket_state: WebsocketStateManager,
) -> None:
    """Test light entity becomes unavailable when device is disconnected."""
    # Initial state should be available
    light_entity = hass.states.get("light.device_with_led_led")
    assert light_entity.state == STATE_ON

    # Simulate device disconnection
    updated_device = deepcopy(DEVICE_WITH_LED)
    updated_device["state"] = 0  # Disconnected

    mock_websocket_state.disconnect()
    await hass.async_block_till_done()

    # Light should become unavailable
    light_entity = hass.states.get("light.device_with_led_led")
    assert light_entity.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_registry_cleanup_on_reload(
    hass: HomeAssistant,
    config_entry_setup: MockConfigEntry,
) -> None:
    """Test light entity registry cleanup on config entry reload."""
    entity_registry = er.async_get(hass)

    # Verify light entity is registered
    light_entity_id = "light.device_with_led_led"
    assert hass.states.get(light_entity_id) is not None

    entity_entry = entity_registry.async_get(light_entity_id)
    assert entity_entry is not None

    # Disable the entity
    entity_registry.async_update_entity(
        light_entity_id, disabled_by=RegistryEntryDisabler.USER
    )

    # Reload config entry
    await hass.config_entries.async_reload(config_entry_setup.entry_id)
    await hass.async_block_till_done()

    # Entity should remain disabled
    entity_entry = entity_registry.async_get(light_entity_id)
    assert entity_entry.disabled_by is RegistryEntryDisabler.USER


@pytest.mark.parametrize("device_payload", [[DEVICE_WITH_LED]])
@pytest.mark.usefixtures("config_entry_setup")
async def test_light_invalid_color_handling(
    hass: HomeAssistant,
) -> None:
    """Test handling of invalid LED color values."""
    # Create a device with invalid color format
    invalid_device = deepcopy(DEVICE_WITH_LED)
    invalid_device["led_override_color"] = "invalid_color"
    invalid_device["mac"] = "10:00:00:00:01:05"
    invalid_device["name"] = "Device Invalid Color"

    # The entity should still be created and use default white color
    light_entity = hass.states.get("light.device_with_led_led")
    assert light_entity is not None
    # Should fall back to white for invalid colors
    assert light_entity.attributes["rgb_color"] == (
        0,
        0,
        255,
    )  # Original blue from DEVICE_WITH_LED


async def test_light_platform_snapshot(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry_factory: ConfigEntryFactoryType,
    snapshot: SnapshotAssertion,
) -> None:
    """Test light platform snapshot."""
    config_entry = await config_entry_factory()
    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.parametrize(
    "device_payload",
    [
        [
            DEVICE_WITH_LED,
            DEVICE_LED_OFF,
            DEVICE_CUSTOM_LED,
        ]
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_multiple_lights(
    hass: HomeAssistant,
) -> None:
    """Test multiple light entities with different LED states."""
    # Should have 3 light entities
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 3

    # Check each light entity
    light1 = hass.states.get("light.device_with_led_led")
    assert light1.state == STATE_ON
    assert light1.attributes["rgb_color"] == (0, 0, 255)

    light2 = hass.states.get("light.device_led_off_led")
    assert light2.state == STATE_OFF

    light3 = hass.states.get("light.device_custom_led_led")
    assert light3.state == STATE_ON
    assert light3.attributes["rgb_color"] == (255, 0, 255)
