"""Light platform for UniFi Network integration.

Support for controlling LED status lights on UniFi devices.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aiounifi.interfaces.api_handlers import APIHandler, ItemEvent
from aiounifi.interfaces.devices import Devices
from aiounifi.models.api import ApiItem
from aiounifi.models.device import Device, DeviceSetLedStatus

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UnifiConfigEntry
from .entity import (
    UnifiEntity,
    UnifiEntityDescription,
    async_device_available_fn,
    async_device_device_info_fn,
)

if TYPE_CHECKING:
    from .hub import UnifiHub


@callback
def async_device_led_supported_fn(hub: UnifiHub, obj_id: str) -> bool:
    """Check if device supports LED control."""
    device = hub.api.devices[obj_id]
    return device.supports_led_ring


@callback
def async_device_led_is_on_fn(hub: UnifiHub, device: Device) -> bool:
    """Check if device LED is on."""
    return device.led_override == "on"


async def async_device_led_control_fn(
    hub: UnifiHub, obj_id: str, **kwargs: Any
) -> None:
    """Control device LED."""
    device = hub.api.devices[obj_id]

    # Determine the status
    if "turn_on" in kwargs:
        status = "on" if kwargs["turn_on"] else "off"
    else:
        status = device.led_override or "on"

    # Get brightness (0-255 -> 0-100 for UniFi)
    brightness = None
    if ATTR_BRIGHTNESS in kwargs:
        brightness = int((kwargs[ATTR_BRIGHTNESS] / 255) * 100)
    elif device.led_override_color_brightness is not None:
        brightness = device.led_override_color_brightness

    # Get RGB color (convert to hex string)
    color = None
    if ATTR_RGB_COLOR in kwargs:
        rgb = kwargs[ATTR_RGB_COLOR]
        color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    elif device.led_override_color:
        color = device.led_override_color

    await hub.api.request(
        DeviceSetLedStatus.create(
            device=device,
            status=status,
            brightness=brightness,
            color=color,
        )
    )


@dataclass(frozen=True, kw_only=True)
class UnifiLightEntityDescription[HandlerT: APIHandler, ApiItemT: ApiItem](
    LightEntityDescription, UnifiEntityDescription[HandlerT, ApiItemT]
):
    """Class describing UniFi light entity."""

    control_fn: Callable[..., Awaitable[None]]
    is_on_fn: Callable[[UnifiHub, ApiItemT], bool]


ENTITY_DESCRIPTIONS: tuple[UnifiLightEntityDescription, ...] = (
    UnifiLightEntityDescription[Devices, Device](
        key="LED control",
        translation_key="led_control",
        api_handler_fn=lambda api: api.devices,
        available_fn=async_device_available_fn,
        control_fn=async_device_led_control_fn,
        device_info_fn=async_device_device_info_fn,
        is_on_fn=async_device_led_is_on_fn,
        name_fn=lambda device: f"{device.name} LED",
        object_fn=lambda api, obj_id: api.devices[obj_id],
        supported_fn=async_device_led_supported_fn,
        unique_id_fn=lambda hub, obj_id: f"led-{obj_id}",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: UnifiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up lights for UniFi Network integration."""
    config_entry.runtime_data.entity_loader.register_platform(
        async_add_entities,
        UnifiLightEntity,
        ENTITY_DESCRIPTIONS,
    )


class UnifiLightEntity[HandlerT: APIHandler, ApiItemT: ApiItem](
    UnifiEntity[HandlerT, ApiItemT], LightEntity
):
    """Base representation of a UniFi light."""

    entity_description: UnifiLightEntityDescription[HandlerT, ApiItemT]

    def __init__(
        self,
        obj_id: str,
        hub: UnifiHub,
        description: UnifiLightEntityDescription[HandlerT, ApiItemT],
    ) -> None:
        """Initialize UniFi light entity."""
        super().__init__(obj_id, hub, description)
        self._attr_supported_features = 0  # type: ignore[assignment]
        self._attr_color_mode = ColorMode.RGB
        self._attr_supported_color_modes = {ColorMode.RGB}

    @callback
    def async_initiate_state(self) -> None:
        """Initiate entity state."""
        self.async_update_state(ItemEvent.ADDED, self._obj_id)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on light."""
        await self.entity_description.control_fn(
            self.hub, self._obj_id, turn_on=True, **kwargs
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        await self.entity_description.control_fn(
            self.hub, self._obj_id, turn_on=False, **kwargs
        )

    @callback
    def async_update_state(self, event: ItemEvent, obj_id: str) -> None:
        """Update entity state."""
        description = self.entity_description
        device_obj = description.object_fn(self.api, self._obj_id)

        # Cast to Device for type checking
        device: Device = device_obj  # type: ignore[assignment]

        # Update on/off state
        self._attr_is_on = description.is_on_fn(self.hub, device_obj)

        # Update brightness (UniFi uses 0-100, HA uses 0-255)
        if device.led_override_color_brightness is not None:
            self._attr_brightness = int(
                (device.led_override_color_brightness / 100) * 255
            )
        else:
            self._attr_brightness = 255 if self._attr_is_on else 0

        # Update RGB color
        if device.led_override_color:
            # Convert hex color to RGB tuple
            color_hex = device.led_override_color.lstrip("#")
            if len(color_hex) == 6:
                try:
                    rgb_tuple = tuple(int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
                    # Ensure it's exactly 3 elements for RGB
                    if len(rgb_tuple) == 3:
                        self._attr_rgb_color = (
                            rgb_tuple[0],
                            rgb_tuple[1],
                            rgb_tuple[2],
                        )
                    else:
                        self._attr_rgb_color = (255, 255, 255)  # Default to white
                except ValueError:
                    self._attr_rgb_color = (255, 255, 255)  # Default to white
            else:
                self._attr_rgb_color = (255, 255, 255)  # Default to white
        else:
            self._attr_rgb_color = (255, 255, 255)  # Default to white
