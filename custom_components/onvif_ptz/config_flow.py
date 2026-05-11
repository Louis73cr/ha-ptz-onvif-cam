"""Config flow for ONVIF PTZ integration."""
from __future__ import annotations

import requests
from requests.auth import HTTPDigestAuth
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_CAMERA_NAME,
    CONF_CAMERA_MODEL,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PROFILE_TOKEN,
    CONF_PRESET_1,
    CONF_PRESET_2,
    CONF_PRESET_3,
    CAMERA_MODELS,
    DEFAULT_PORT,
    DEFAULT_PROFILE_TOKEN,
    DEFAULT_PRESET_1,
    DEFAULT_PRESET_2,
    DEFAULT_PRESET_3,
)

MODEL_OPTIONS = {key: info["name"] for key, info in CAMERA_MODELS.items()}

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CAMERA_NAME): str,
        vol.Required(CONF_CAMERA_MODEL): vol.In(MODEL_OPTIONS),
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERNAME, default="admin"): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PROFILE_TOKEN, default=DEFAULT_PROFILE_TOKEN): str,
        vol.Optional(CONF_PRESET_1, default=DEFAULT_PRESET_1): str,
        vol.Optional(CONF_PRESET_2, default=DEFAULT_PRESET_2): str,
        vol.Optional(CONF_PRESET_3, default=DEFAULT_PRESET_3): str,
    }
)


def _test_connection(host: str, port: int, username: str, password: str) -> bool:
    """Test if we can connect to the camera ONVIF service."""
    soap = """<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <GetServiceCapabilities xmlns="http://www.onvif.org/ver20/ptz/wsdl"/>
  </Body>
</Envelope>"""
    try:
        resp = requests.post(
            f"http://{host}:{port}/onvif/ptz_service",
            data=soap,
            headers={"Content-Type": "application/soap+xml"},
            auth=HTTPDigestAuth(username, password),
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


class OnvifPtzConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ONVIF PTZ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Test connection in executor to avoid blocking
            can_connect = await self.hass.async_add_executor_job(
                _test_connection,
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )

            if not can_connect:
                errors["base"] = "cannot_connect"
            else:
                # Use camera name + host as unique id
                await self.async_set_unique_id(
                    f"{user_input[CONF_CAMERA_NAME]}_{user_input[CONF_HOST]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_CAMERA_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class OnvifPtzOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for ONVIF PTZ."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PRESET_1,
                    default=self._entry.options.get(
                        CONF_PRESET_1,
                        self._entry.data.get(CONF_PRESET_1, DEFAULT_PRESET_1),
                    ),
                ): str,
                vol.Optional(
                    CONF_PRESET_2,
                    default=self._entry.options.get(
                        CONF_PRESET_2,
                        self._entry.data.get(CONF_PRESET_2, DEFAULT_PRESET_2),
                    ),
                ): str,
                vol.Optional(
                    CONF_PRESET_3,
                    default=self._entry.options.get(
                        CONF_PRESET_3,
                        self._entry.data.get(CONF_PRESET_3, DEFAULT_PRESET_3),
                    ),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


async def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> OnvifPtzOptionsFlowHandler:
    """Return the options flow handler."""
    return OnvifPtzOptionsFlowHandler(config_entry)
