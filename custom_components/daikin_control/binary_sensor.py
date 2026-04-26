"""Binary sensor platform for Daikin Control Cloud (Gateway online status)."""
import logging
import time

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DaikinControlCoordinator

_LOGGER = logging.getLogger(__name__)

# Threshold: gateway is considered offline if last contact > this many seconds ago
GATEWAY_OFFLINE_THRESHOLD_SEC = 600  # 10 minutes
CANBUS_OFFLINE_THRESHOLD_SEC = 600


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DaikinControlCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        DaikinGatewayOnlineSensor(coordinator, entry),
        DaikinCanBusOnlineSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class _DaikinCloudBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Daikin cloud-based binary sensors."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self, coordinator: DaikinControlCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._installation_id = entry.data.get("installation_id")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{self._installation_id}_cloud")},
            "name": f"Daikin {self._installation_id} Cloud",
            "manufacturer": "Daikin/Rotex",
            "model": "Cloud Gateway",
        }


class DaikinGatewayOnlineSensor(_DaikinCloudBinarySensorBase):
    """Binary sensor for RoCon G1 gateway online status."""

    _attr_icon = "mdi:cloud-check"

    def __init__(
        self, coordinator: DaikinControlCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "Gateway Online"
        self._attr_unique_id = f"daikin_control_{self._installation_id}_gateway_online"

    @property
    def is_on(self) -> bool | None:
        info = self.coordinator.installation_info
        if not info:
            return None
        last_contact = info.get("latestGatewayContact")
        if last_contact is None:
            return None
        return (time.time() - last_contact) < GATEWAY_OFFLINE_THRESHOLD_SEC

    @property
    def extra_state_attributes(self) -> dict:
        info = self.coordinator.installation_info
        attrs = {
            "active_within_last_hour": info.get("activeWithinLastHour"),
            "last_gateway_contact_unix": info.get("latestGatewayContact"),
            "firmware_version": info.get("swVersion"),
        }
        last = info.get("latestGatewayContact")
        if last:
            attrs["seconds_since_last_contact"] = int(time.time() - last)
            from datetime import datetime
            attrs["last_contact"] = datetime.fromtimestamp(last).isoformat()
        return attrs


class DaikinCanBusOnlineSensor(_DaikinCloudBinarySensorBase):
    """Binary sensor for CanBus (heat pump <-> RoCon) online status."""

    _attr_icon = "mdi:lan-connect"

    def __init__(
        self, coordinator: DaikinControlCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "CanBus Online"
        self._attr_unique_id = f"daikin_control_{self._installation_id}_canbus_online"

    @property
    def is_on(self) -> bool | None:
        info = self.coordinator.installation_info
        if not info:
            return None
        last_contact = info.get("lastCanBusContact")
        if last_contact is None:
            return None
        return (time.time() - last_contact) < CANBUS_OFFLINE_THRESHOLD_SEC

    @property
    def extra_state_attributes(self) -> dict:
        info = self.coordinator.installation_info
        attrs = {
            "last_canbus_contact_unix": info.get("lastCanBusContact"),
        }
        last = info.get("lastCanBusContact")
        if last:
            attrs["seconds_since_last_contact"] = int(time.time() - last)
            from datetime import datetime
            attrs["last_contact"] = datetime.fromtimestamp(last).isoformat()
        return attrs
