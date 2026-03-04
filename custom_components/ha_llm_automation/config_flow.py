"""Config flow for HA LLM Automation integration."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries

from .const import DOMAIN, PLATFORM_NAME


class HALLMAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA LLM Automation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step — just a confirmation, no fields."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(title=PLATFORM_NAME, data={})

        return self.async_show_form(step_id="user")
