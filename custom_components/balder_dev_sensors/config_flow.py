"""Config flow for Balder Dev Sensors."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

DOMAIN = "balder_dev_sensors"


class BalderDevSensorsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Balder Dev Sensors."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Single step — no options needed."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Balder Dev Sensors", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
