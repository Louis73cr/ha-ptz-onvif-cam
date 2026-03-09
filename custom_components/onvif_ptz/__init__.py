"""The ONVIF PTZ integration."""
from __future__ import annotations

import logging

import requests
from requests.auth import HTTPDigestAuth
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PROFILE_TOKEN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["button"]

SERVICE_GOTO_PRESET = "goto_preset"
SERVICE_SET_PRESET = "set_preset"
SERVICE_REMOVE_PRESET = "remove_preset"


def _build_auth(entry_data: dict) -> HTTPDigestAuth:
    return HTTPDigestAuth(entry_data[CONF_USERNAME], entry_data[CONF_PASSWORD])


def _build_url(entry_data: dict) -> str:
    return f"http://{entry_data[CONF_HOST]}:{entry_data[CONF_PORT]}/onvif/ptz_service"


def _send_soap(entry_data: dict, soap_body: str) -> bool:
    """Send a SOAP request to the camera."""
    try:
        resp = requests.post(
            _build_url(entry_data),
            data=soap_body,
            headers={"Content-Type": "application/soap+xml"},
            auth=_build_auth(entry_data),
            timeout=5,
        )
        return resp.status_code == 200
    except requests.RequestException as err:
        _LOGGER.error("ONVIF PTZ request failed: %s", err)
        return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ONVIF PTZ from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register preset services
    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    """Register PTZ preset services."""

    if hass.services.has_service(DOMAIN, SERVICE_GOTO_PRESET):
        return  # Already registered

    async def async_goto_preset(call: ServiceCall) -> None:
        """Go to a PTZ preset."""
        entry_id = call.data["entry_id"]
        preset_token = call.data["preset_token"]
        entry_data = hass.data[DOMAIN].get(entry_id)
        if not entry_data:
            _LOGGER.error("Entry %s not found", entry_id)
            return
        token = entry_data.get(CONF_PROFILE_TOKEN, "Profile000")
        soap = f"""<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <GotoPreset xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>{token}</ProfileToken>
      <PresetToken>{preset_token}</PresetToken>
    </GotoPreset>
  </Body>
</Envelope>"""
        await hass.async_add_executor_job(_send_soap, entry_data, soap)

    async def async_set_preset(call: ServiceCall) -> None:
        """Save current position as a preset."""
        entry_id = call.data["entry_id"]
        preset_name = call.data["preset_name"]
        preset_token = call.data.get("preset_token", "")
        entry_data = hass.data[DOMAIN].get(entry_id)
        if not entry_data:
            _LOGGER.error("Entry %s not found", entry_id)
            return
        token = entry_data.get(CONF_PROFILE_TOKEN, "Profile000")
        preset_token_xml = (
            f"<PresetToken>{preset_token}</PresetToken>" if preset_token else ""
        )
        soap = f"""<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <SetPreset xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>{token}</ProfileToken>
      <PresetName>{preset_name}</PresetName>
      {preset_token_xml}
    </SetPreset>
  </Body>
</Envelope>"""
        await hass.async_add_executor_job(_send_soap, entry_data, soap)

    async def async_remove_preset(call: ServiceCall) -> None:
        """Remove a PTZ preset."""
        entry_id = call.data["entry_id"]
        preset_token = call.data["preset_token"]
        entry_data = hass.data[DOMAIN].get(entry_id)
        if not entry_data:
            _LOGGER.error("Entry %s not found", entry_id)
            return
        token = entry_data.get(CONF_PROFILE_TOKEN, "Profile000")
        soap = f"""<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <RemovePreset xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>{token}</ProfileToken>
      <PresetToken>{preset_token}</PresetToken>
    </RemovePreset>
  </Body>
</Envelope>"""
        await hass.async_add_executor_job(_send_soap, entry_data, soap)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GOTO_PRESET,
        async_goto_preset,
        schema=vol.Schema(
            {
                vol.Required("entry_id"): cv.string,
                vol.Required("preset_token"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PRESET,
        async_set_preset,
        schema=vol.Schema(
            {
                vol.Required("entry_id"): cv.string,
                vol.Required("preset_name"): cv.string,
                vol.Optional("preset_token"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_PRESET,
        async_remove_preset,
        schema=vol.Schema(
            {
                vol.Required("entry_id"): cv.string,
                vol.Required("preset_token"): cv.string,
            }
        ),
    )
