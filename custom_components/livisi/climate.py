"""Code to handle a Livisi Virtual Climate Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .livisi_device import LivisiDevice

from .const import (
    DOMAIN,
    LIVISI_STATE_CHANGE,
    LOGGER,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    VRCC_DEVICE_TYPES,
    OPERATION_MODE_AUTO,
    OPERATION_MODE_MANU,
)

from .coordinator import LivisiDataUpdateCoordinator
from .entity import LivisiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate device."""
    coordinator: LivisiDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    known_devices = set()

    @callback
    def handle_coordinator_update() -> None:
        """Add climate device."""
        shc_devices: list[LivisiDevice] = coordinator.data
        entities: list[ClimateEntity] = []
        for device in shc_devices:
            if device.type in VRCC_DEVICE_TYPES and device.id not in known_devices:
                known_devices.add(device.id)
                livisi_climate: ClimateEntity = LivisiClimate(
                    config_entry, coordinator, device
                )
                LOGGER.debug("Include device type: %s", device.type)
                coordinator.devices.add(device.id)
                entities.append(livisi_climate)
        async_add_entities(entities)

    config_entry.async_on_unload(
        coordinator.async_add_listener(handle_coordinator_update)
    )


class LivisiClimate(LivisiEntity, ClimateEntity):
    """Represents the Livisi Climate."""

    _attr_hvac_modes = []
    _attr_hvac_mode = HVACMode.HEAT
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: LivisiDataUpdateCoordinator,
        device: LivisiDevice,
    ) -> None:
        """Initialize the Livisi Climate."""
        super().__init__(
            config_entry, coordinator, device, use_room_as_device_name=True
        )

        self._target_temperature_capability = self.capabilities["RoomSetpoint"]
        self._temperature_capability = self.capabilities["RoomTemperature"]
        self._humidity_capability = self.capabilities["RoomHumidity"]

        config = device.capability_config.get("RoomSetpoint", {})
        self._attr_max_temp = config.get("maxTemperature", MAX_TEMPERATURE)
        self._attr_min_temp = config.get("minTemperature", MIN_TEMPERATURE)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        success = await self.aio_livisi.async_set_state(
            self._target_temperature_capability,
            key=(
                "setpointTemperature"
                if self.coordinator.aiolivisi.controller.is_v2
                else "pointTemperature"
            ),
            value=kwargs.get(ATTR_TEMPERATURE),
        )
        if not success:
            self.update_reachability(False)
            raise HomeAssistantError(f"Failed to set temperature on {self._attr_name}")
        self.update_reachability(True)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        await super().async_added_to_hass()

        target_temperature = await self.coordinator.aiolivisi.async_get_device_state(
            self._target_temperature_capability,
            (
                "setpointTemperature"
                if self.coordinator.aiolivisi.controller.is_v2
                else "pointTemperature"
            ),
        )
        temperature = await self.coordinator.aiolivisi.async_get_device_state(
            self._temperature_capability, "temperature"
        )
        humidity = await self.coordinator.aiolivisi.async_get_device_state(
            self._humidity_capability, "humidity"
        )
        if temperature is None:
            self._attr_current_temperature = None
            self.update_reachability(False)
        else:
            self._attr_target_temperature = target_temperature
            self._attr_current_temperature = temperature
            self._attr_current_humidity = humidity
            self.update_reachability(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{LIVISI_STATE_CHANGE}_{self._target_temperature_capability}",
                self.update_target_temperature,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{LIVISI_STATE_CHANGE}_{self._temperature_capability}",
                self.update_temperature,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{LIVISI_STATE_CHANGE}_{self._humidity_capability}",
                self.update_humidity,
            )
        )

    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Do nothing as LIVISI devices do not support changing the hvac mode."""

    @property
    def hvac_action(self) -> HVACAction | None:
        """Calculate current hvac state based on target and current temperature."""
        if (
            self._attr_current_temperature is None
            or self._attr_target_temperature is None
        ):
            return HVACAction.OFF
        if self._attr_target_temperature > self._attr_current_temperature:
            return HVACAction.HEATING
        if self._attr_target_temperature == self._attr_min_temp:
            return HVACAction.OFF
        return HVACAction.IDLE

    @callback
    def update_target_temperature(self, target_temperature: float) -> None:
        """Update the target temperature of the climate device."""
        self._attr_target_temperature = target_temperature
        self.async_write_ha_state()

    @callback
    def update_temperature(self, current_temperature: float) -> None:
        """Update the current temperature of the climate device."""
        self._attr_current_temperature = current_temperature
        self.async_write_ha_state()

    @callback
    def update_humidity(self, humidity: int) -> None:
        """Update the humidity of the climate device."""
        self._attr_current_humidity = humidity
        self.async_write_ha_state()
