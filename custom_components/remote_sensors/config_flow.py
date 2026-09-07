"""Config flow for Remote Sensors."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "remote_sensors"
CONF_REMOTE_NAME = "remote_name"
DEFAULT_REMOTE_NAME = "Remote"


class RemoteSensorsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Remote Sensors."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "RemoteSensorsOptionsFlow":
        """Get the options flow for this handler."""
        return RemoteSensorsOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Single step — no options needed."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_REMOTE_NAME],
                data={CONF_REMOTE_NAME: user_input[CONF_REMOTE_NAME]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REMOTE_NAME, default=DEFAULT_REMOTE_NAME): str,
                }
            ),
        )


class RemoteSensorsOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Remote Sensors."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the integration options."""
        if user_input is not None:
            remote_name = str(user_input[CONF_REMOTE_NAME]).strip() or DEFAULT_REMOTE_NAME
            return self.async_create_entry(title="", data={CONF_REMOTE_NAME: remote_name})

        current_remote_name = str(
            self.config_entry.options.get(
                CONF_REMOTE_NAME,
                self.config_entry.data.get(CONF_REMOTE_NAME, DEFAULT_REMOTE_NAME),
            )
        ).strip() or DEFAULT_REMOTE_NAME

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REMOTE_NAME, default=current_remote_name): str,
                }
            ),
        )
