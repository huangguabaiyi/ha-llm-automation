"""Config flow for HA LLM Automation integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_EXTRA_VISIBLE_DOMAINS,
    CONF_HIDDEN_DOMAINS,
    CONF_LLM_API_KEY,
    CONF_LLM_BASE_URL,
    CONF_LLM_MAX_TOKENS,
    CONF_LLM_MODEL,
    CONF_LLM_PROVIDER,
    CONF_LLM_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_ANTHROPIC,
    DEFAULT_MODEL_OPENAI,
    DEFAULT_TEMPERATURE,
    DOMAIN,
)

_PROVIDER_OPTIONS = ["openai_compatible", "openai", "anthropic"]

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LLM_PROVIDER, default="openai_compatible"): vol.In(
            _PROVIDER_OPTIONS
        ),
        vol.Required(CONF_LLM_API_KEY): str,
        vol.Optional(CONF_LLM_BASE_URL, default=""): str,
        vol.Required(CONF_LLM_MODEL, default=DEFAULT_MODEL_OPENAI): str,
        vol.Optional(CONF_LLM_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(
            int, vol.Range(min=512, max=32768)
        ),
        vol.Optional(CONF_LLM_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
            float, vol.Range(min=0.0, max=1.0)
        ),
    }
)


class HALLMAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA LLM Automation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        # Only allow one config entry
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate by trying to import llm_client
            try:
                llm_config = {
                    "provider": user_input[CONF_LLM_PROVIDER],
                    "api_key": user_input[CONF_LLM_API_KEY],
                    "model": user_input[CONF_LLM_MODEL],
                    "max_tokens": user_input.get(CONF_LLM_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                    "temperature": user_input.get(CONF_LLM_TEMPERATURE, DEFAULT_TEMPERATURE),
                }
                base_url = user_input.get(CONF_LLM_BASE_URL, "").strip()
                if base_url:
                    llm_config["base_url"] = base_url

                # Basic validation: check if api_key is non-empty
                if not llm_config["api_key"]:
                    errors[CONF_LLM_API_KEY] = "invalid_auth"
                else:
                    return self.async_create_entry(
                        title=f"HA LLM ({user_input[CONF_LLM_PROVIDER]})",
                        data=user_input,
                    )
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HALLMAutomationOptionsFlow:
        """Get the options flow for this handler."""
        return HALLMAutomationOptionsFlow(config_entry)


class HALLMAutomationOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HA LLM Automation."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options
        data = self._config_entry.data

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LLM_MODEL,
                    default=current.get(CONF_LLM_MODEL, data.get(CONF_LLM_MODEL, DEFAULT_MODEL_OPENAI)),
                ): str,
                vol.Optional(
                    CONF_LLM_MAX_TOKENS,
                    default=current.get(CONF_LLM_MAX_TOKENS, data.get(CONF_LLM_MAX_TOKENS, DEFAULT_MAX_TOKENS)),
                ): vol.All(int, vol.Range(min=512, max=32768)),
                vol.Optional(
                    CONF_LLM_TEMPERATURE,
                    default=current.get(CONF_LLM_TEMPERATURE, data.get(CONF_LLM_TEMPERATURE, DEFAULT_TEMPERATURE)),
                ): vol.All(float, vol.Range(min=0.0, max=1.0)),
                vol.Optional(
                    CONF_EXTRA_VISIBLE_DOMAINS,
                    default=current.get(CONF_EXTRA_VISIBLE_DOMAINS, ""),
                ): str,
                vol.Optional(
                    CONF_HIDDEN_DOMAINS,
                    default=current.get(CONF_HIDDEN_DOMAINS, ""),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
