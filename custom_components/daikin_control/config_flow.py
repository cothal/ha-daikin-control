"""Config flow for Daikin Control Cloud."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return DaikinControlOptionsFlow(config_entry)

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


class DaikinControlOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Daikin Control."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._entry_id = config_entry.entry_id

    async def async_step_init(self, user_input=None):
        """Manage options."""
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        current_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(int, vol.Range(min=30, max=3600)),
                }
            ),
        )
