"""Data update coordinator for Daikin Control."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DaikinControlApi, DaikinControlApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DaikinControlCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Daikin Control Cloud."""

    def __init__(
        self, hass: HomeAssistant, api: DaikinControlApi, scan_interval: int
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._accumulated_data: dict[str, dict] = {}

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            new_data = await self.api.get_latest_values()
            # Merge new data into accumulated data
            # This ensures parameters that don't appear in every poll
            # are still available as sensors with their last known value
            for key, value in new_data.items():
                existing = self._accumulated_data.get(key)
                if existing is None or value.get("date", 0) > existing.get("date", 0):
                    self._accumulated_data[key] = value
            return self._accumulated_data
        except DaikinControlApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
