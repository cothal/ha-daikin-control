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

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            return await self.api.get_latest_values()
        except DaikinControlApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
