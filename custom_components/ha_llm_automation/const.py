"""Constants for HA LLM Automation integration."""
from __future__ import annotations

DOMAIN = "ha_llm_automation"
PLATFORM_NAME = "HA LLM Automation"

# Config entry keys
CONF_LLM_PROVIDER = "provider"
CONF_LLM_API_KEY = "api_key"
CONF_LLM_BASE_URL = "base_url"
CONF_LLM_MODEL = "model"
CONF_LLM_MAX_TOKENS = "max_tokens"
CONF_LLM_TEMPERATURE = "temperature"
CONF_EXTRA_VISIBLE_DOMAINS = "extra_visible_domains"
CONF_HIDDEN_DOMAINS = "hidden_domains"
CONF_LOG_PROMPT = "log_prompt"
CONF_USE_DOCS = "use_docs"
CONF_AREA_FILTER = "area_filter"
CONF_LABEL_FILTER = "label_filter"
CONF_INTEGRATION_FILTER = "integration_filter"

# Defaults
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MODEL_OPENAI = "gpt-4o"
DEFAULT_MODEL_ANTHROPIC = "claude-sonnet-4-6"

# Storage keys
STORAGE_KEY = f"{DOMAIN}.config"

# WebSocket event types (for log streaming)
WS_EVENT_LOG = f"{DOMAIN}_log"
WS_EVENT_RESULT = f"{DOMAIN}_result"

# Frontend path
FRONTEND_URL = f"/{DOMAIN}/frontend"
PANEL_URL = f"/{DOMAIN}"
PANEL_TITLE = "LLM Automation"
PANEL_ICON = "mdi:creation"
PANEL_NAME = "ha-llm-automation"
