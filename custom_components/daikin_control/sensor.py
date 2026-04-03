"""Sensor platform for Daikin Control Cloud."""
import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PARAMETER_MAP
from .coordinator import DaikinControlCoordinator

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPE_NAMES = {
    "direct": "Heizkreis",
    "water": "Warmwasser",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DaikinControlCoordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()

    entities = []
    if coordinator.data:
        for key, data in coordinator.data.items():
            entities.append(DaikinControlSensor(coordinator, entry, key, data))

    async_add_entities(entities, update_before_add=False)


class DaikinControlSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a Daikin Control parameter."""

    def __init__(
        self,
        coordinator: DaikinControlCoordinator,
        entry: ConfigEntry,
        key: str,
        initial_data: dict,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._param_name = initial_data["name"]
        self._device_name = initial_data["device_name"]
        self._device_type = initial_data["device_type"]

        device_label = DEVICE_TYPE_NAMES.get(self._device_type, self._device_type)
        param_info = PARAMETER_MAP.get(self._param_name)

        if param_info:
            friendly_name, unit, device_class, icon = param_info
            self._attr_name = f"{device_label} {friendly_name}"
            self._attr_native_unit_of_measurement = unit
            if device_class:
                self._attr_device_class = device_class
            self._attr_icon = icon
        else:
            self._attr_name = f"{device_label} {self._param_name}"
            self._attr_icon = "mdi:information-outline"

        self._attr_unique_id = f"daikin_control_{entry.data.get('installation_id')}_{key}"
        self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.data.get('installation_id')}_{self._device_name}")},
            "name": f"Daikin {self._device_name} ({device_label})",
            "manufacturer": "Daikin/Rotex",
            "model": f"{self._device_name} ({self._device_type})",
        }

    @property
    def native_value(self):
        if self.coordinator.data and self._key in self.coordinator.data:
            val = self.coordinator.data[self._key].get("value", "")
            try:
                return float(val)
            except (ValueError, TypeError):
                return val
        return None

    @property
    def extra_state_attributes(self):
        if self.coordinator.data and self._key in self.coordinator.data:
            data = self.coordinator.data[self._key]
            ts = data.get("date", 0)
            return {
                "parameter": self._param_name,
                "device": self._device_name,
                "device_type": self._device_type,
                "last_update": datetime.fromtimestamp(ts).isoformat() if ts else None,
            }
        return {}
