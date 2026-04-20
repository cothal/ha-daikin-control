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
        self._consecutive_transient_failures: int = 0
        # After this many consecutive transient failures, we give up and mark unavailable
        self._transient_failure_threshold: int = 5

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            new_data = await self.api.get_latest_values()
            # Reset transient failure counter on success
            self._consecutive_transient_failures = 0
            # Merge new data into accumulated data
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
            # Return previously accumulated data - sensors stay on last value
            return self._accumulated_data
        except DaikinControlApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
