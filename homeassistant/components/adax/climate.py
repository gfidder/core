"""Support for Adax wifi-enabled home heaters."""
from __future__ import annotations

from typing import Any

from adax import Adax

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ACCOUNT_ID, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Adax thermostat with config flow."""
    adax_data_handler = Adax(
        entry.data[ACCOUNT_ID],
        entry.data[CONF_PASSWORD],
        websession=async_get_clientsession(hass),
    )

    async_add_entities(
        (
            AdaxDevice(room, adax_data_handler)
            for room in await adax_data_handler.get_rooms()
        ),
        True,
    )


class AdaxDevice(ClimateEntity):
    """Representation of a heater."""

    _attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
    _attr_max_temp = 35
    _attr_min_temp = 5
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(self, heater_data: dict[str, Any], adax_data_handler: Adax) -> None:
        """Initialize the heater."""
        self._device_id = heater_data["id"]
        self._adax_data_handler = adax_data_handler

        self._attr_unique_id = f"{heater_data['homeId']}_{heater_data['id']}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, heater_data["id"])},
            name=self.name,
            manufacturer="Adax",
        )

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            temperature = max(self.min_temp, self.target_temperature or self.min_temp)
            await self._adax_data_handler.set_room_target_temperature(
                self._device_id, temperature, True
            )
        elif hvac_mode == HVAC_MODE_OFF:
            await self._adax_data_handler.set_room_target_temperature(
                self._device_id, self.min_temp, False
            )
        else:
            return
        await self._adax_data_handler.update()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._adax_data_handler.set_room_target_temperature(
            self._device_id, temperature, True
        )

    async def async_update(self) -> None:
        """Get the latest data."""
        for room in await self._adax_data_handler.get_rooms():
            if room["id"] != self._device_id:
                continue
            self._attr_name = room["name"]
            self._attr_current_temperature = room.get("temperature")
            self._attr_target_temperature = room.get("targetTemperature")
            if room["heatingEnabled"]:
                self._attr_hvac_mode = HVAC_MODE_HEAT
                self._attr_icon = "mdi:radiator"
            else:
                self._attr_hvac_mode = HVAC_MODE_OFF
                self._attr_icon = "mdi:radiator-off"
            return
