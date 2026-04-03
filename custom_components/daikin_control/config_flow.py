"""Config flow for Daikin Control Cloud."""
import logging

import voluptuous as vol

from homeassistant import config_entries

from .api import DaikinControlApi
from .const import (
    CONF_INSTALLATION_ID,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class DaikinControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Daikin Control."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            api = DaikinControlApi(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_INSTALLATION_ID],
            )
            try:
                if await api.test_connection():
                    await api.close()
                    await self.async_set_unique_id(user_input[CONF_INSTALLATION_ID])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Daikin {user_input[CONF_INSTALLATION_ID]}",
                        data=user_input,
                    )
                else:
                    errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            finally:
                await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_INSTALLATION_ID): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(int, vol.Range(min=30, max=3600)),
                }
            ),
            errors=errors,
        )
