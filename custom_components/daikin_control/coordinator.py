"""Data update coordinator for Daikin Control."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DaikinControlApi, DaikinControlApiError, DaikinControlTransientError
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
        self._installation_info: dict = {}
        self._consecutive_transient_failures: int = 0
        self._transient_failure_threshold: int = 5

    @property
    def installation_info(self) -> dict:
        """Latest installation info (gateway status)."""
        return self._installation_info

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            # Fetch installation info (gateway status) - lightweight, do first
            try:
                info = await self.api.get_installation_info()
                self._installation_info = info
            except DaikinControlTransientError as err:
                _LOGGER.debug("Could not fetch installation info: %s", err)
                # Don't fail the whole update for this - keep old info

            new_data = await self.api.get_latest_values()
            self._consecutive_transient_failures = 0
            for key, value in new_data.items():
                existing = self._accumulated_data.get(key)
                if existing is None or value.get("date", 0) > existing.get("date", 0):
                    self._accumulated_data[key] = value
            return self._accumulated_data
        except DaikinControlTransientError as err:
            self._consecutive_transient_failures += 1
            if self._consecutive_transient_failures >= self._transient_failure_threshold:
                _LOGGER.error(
                    "Too many consecutive transient failures (%d), marking unavailable: %s",
                    self._consecutive_transient_failures, err,
                )
                raise UpdateFailed(f"Persistent failure: {err}") from err
            _LOGGER.warning(
                "Transient error (%d/%d), keeping last known values: %s",
                self._consecutive_transient_failures,
                self._transient_failure_threshold,
                err,
            )
            return self._accumulated_data
        except DaikinControlApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
