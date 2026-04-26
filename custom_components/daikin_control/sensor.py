"""Sensor platform for Daikin Control Cloud."""
import logging
from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PARAMETER_MAP
from .coordinator import DaikinControlCoordinator

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPE_NAMES = {
    "direct": "Heizkreis",
    "water": "Warmwasser",
}

# Parameters that should be ENABLED by default (the important ones)
ENABLED_BY_DEFAULT = {
    "cAUSSENTEMP",
    "cAUSSENTEMP_WAERMEPUMPE",
    "cSPEICHERISTTEMP",
    "eVORLAUFISTTEMP",
    "eVORLAUFSOLLTEMP",
    "cKESSELISTTEMP",
    "cKESSELSOLLTEMP",
    "cRUECKLAUFTEMP",
    "cRAUMISTTEMP",
    "cRAUMSOLLTEMP_I",
    "cRAUMSOLLTEMP_II",
    "cRAUMSOLLTEMP_III",
    "cT_TVBH",
    "cT_TVBHMIX",
    "cT_TVBH1",
    "cVOLUMENSTROM",
    "cPUMPENLAUFZEIT",
    "cKOMPRESSORLAUFZEIT",
    "cPROGRAMMSCHALTER",
    "cWW_AKTIV",
    "cEINMAL_WW_AKTIV",
    "cFEHLER_AKTUELL",
    "eHZKKURVE",
    "eMAX_VORLAUFTEMP",
    "cEINSTELL_SPEICHERSOLLTEMP",
    "cVERSTELLTE_SPEICHERSOLLTEMP",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DaikinControlCoordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()

    # Track which keys already have entities - only create important ones
    known_keys: set[str] = set()
    entities = []
    if coordinator.data:
        for key, data in coordinator.data.items():
            known_keys.add(key)
            if data.get("name", "") in ENABLED_BY_DEFAULT:
                entities.append(DaikinControlSensor(coordinator, entry, key, data))

    # Add cloud status sensors (always created)
    entities.extend([
        DaikinSecondsSinceGatewayContactSensor(coordinator, entry),
        DaikinSecondsSinceCanBusContactSensor(coordinator, entry),
        DaikinFirmwareVersionSensor(coordinator, entry),
        DaikinLastGatewayContactSensor(coordinator, entry),
        DaikinLastCanBusContactSensor(coordinator, entry),
    ])

    async_add_entities(entities, update_before_add=False)

    # Listen for new parameters appearing in future updates
    @callback
    def _async_check_new_entities() -> None:
        """Add entities for newly discovered parameters."""
        if not coordinator.data:
            return
        new_entities = []
        for key, data in coordinator.data.items():
            if key not in known_keys:
                known_keys.add(key)
                if data.get("name", "") in ENABLED_BY_DEFAULT:
                    new_entities.append(
                        DaikinControlSensor(coordinator, entry, key, data)
                    )
                    _LOGGER.info("Discovered new parameter: %s", key)
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_async_check_new_entities)


class DaikinControlSensor(CoordinatorEntity, RestoreSensor):
    """Sensor for a Daikin Control parameter.

    Uses RestoreSensor so the last known value is retained across restarts
    and when the parameter temporarily disappears from the API response.
    """

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

        # Cached last known values (used when coordinator.data is missing this key)
        self._last_value = None
        self._last_update_iso: str | None = None

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

        # Only enable important sensors by default, disable the rest
        if self._param_name not in ENABLED_BY_DEFAULT:
            self._attr_entity_registry_enabled_default = False

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.data.get('installation_id')}_{self._device_name}")},
            "name": f"Daikin {self._device_name} ({device_label})",
            "manufacturer": "Daikin/Rotex",
            "model": f"{self._device_name} ({self._device_type})",
        }

    async def async_added_to_hass(self) -> None:
        """Restore last known value on startup."""
        await super().async_added_to_hass()
        last_sensor_data = await self.async_get_last_sensor_data()
        if last_sensor_data is not None:
            self._last_value = last_sensor_data.native_value
            _LOGGER.debug(
                "Restored %s to %s", self._attr_name, self._last_value
            )
        # Also try to restore last state/attributes
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.attributes:
            saved_update = last_state.attributes.get("last_update")
            if saved_update:
                self._last_update_iso = saved_update

    @property
    def available(self) -> bool:
        """Always report available once we have any value (current or restored)."""
        if self.coordinator.data and self._key in self.coordinator.data:
            return True
        if self._last_value is not None:
            return True
        return False

    @property
    def native_value(self):
        """Return current value or last known value."""
        if self.coordinator.data and self._key in self.coordinator.data:
            val = self.coordinator.data[self._key].get("value", "")
            try:
                parsed = float(val)
            except (ValueError, TypeError):
                parsed = val
            # Cache for future fallback
            self._last_value = parsed
            ts = self.coordinator.data[self._key].get("date", 0)
            if ts:
                self._last_update_iso = datetime.fromtimestamp(ts).isoformat()
            return parsed
        # Fallback to last known value
        return self._last_value

    @property
    def extra_state_attributes(self):
        attrs = {
            "parameter": self._param_name,
            "device": self._device_name,
            "device_type": self._device_type,
        }
        if self.coordinator.data and self._key in self.coordinator.data:
            ts = self.coordinator.data[self._key].get("date", 0)
            attrs["last_update"] = (
                datetime.fromtimestamp(ts).isoformat() if ts else None
            )
        else:
            attrs["last_update"] = self._last_update_iso
            attrs["stale"] = True
        return attrs


import time as _time


class _DaikinCloudInfoSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for sensors that read from coordinator.installation_info."""

    def __init__(
        self, coordinator: DaikinControlCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._installation_id = entry.data.get("installation_id")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{self._installation_id}_cloud")},
            "name": f"Daikin {self._installation_id} Cloud",
            "manufacturer": "Daikin/Rotex",
            "model": "Cloud Gateway",
        }


class DaikinSecondsSinceGatewayContactSensor(_DaikinCloudInfoSensorBase):
    _attr_name = "Sekunden seit Gateway-Kontakt"
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"daikin_control_{self._installation_id}_seconds_since_gateway"
        )

    @property
    def native_value(self):
        info = self.coordinator.installation_info
        ts = info.get("latestGatewayContact") if info else None
        if ts is None:
            return None
        return int(_time.time() - ts)


class DaikinSecondsSinceCanBusContactSensor(_DaikinCloudInfoSensorBase):
    _attr_name = "Sekunden seit CanBus-Kontakt"
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"daikin_control_{self._installation_id}_seconds_since_canbus"
        )

    @property
    def native_value(self):
        info = self.coordinator.installation_info
        ts = info.get("lastCanBusContact") if info else None
        if ts is None:
            return None
        return int(_time.time() - ts)


class DaikinFirmwareVersionSensor(_DaikinCloudInfoSensorBase):
    _attr_name = "Firmware-Version"
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"daikin_control_{self._installation_id}_firmware"
        )

    @property
    def native_value(self):
        info = self.coordinator.installation_info
        return info.get("swVersion") if info else None


class DaikinLastGatewayContactSensor(_DaikinCloudInfoSensorBase):
    _attr_name = "Letzter Gateway-Kontakt"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"daikin_control_{self._installation_id}_last_gateway_contact"
        )

    @property
    def native_value(self):
        info = self.coordinator.installation_info
        ts = info.get("latestGatewayContact") if info else None
        if ts is None:
            return None
        from datetime import datetime, timezone
        return datetime.fromtimestamp(ts, tz=timezone.utc)


class DaikinLastCanBusContactSensor(_DaikinCloudInfoSensorBase):
    _attr_name = "Letzter CanBus-Kontakt"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"daikin_control_{self._installation_id}_last_canbus_contact"
        )

    @property
    def native_value(self):
        info = self.coordinator.installation_info
        ts = info.get("lastCanBusContact") if info else None
        if ts is None:
            return None
        from datetime import datetime, timezone
        return datetime.fromtimestamp(ts, tz=timezone.utc)
