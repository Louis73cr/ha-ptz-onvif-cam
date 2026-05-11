"""Button platform for ONVIF PTZ integration."""
from __future__ import annotations

import time
import logging

import requests
from requests.auth import HTTPDigestAuth

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    PTZ_SPEED,
    PTZ_DURATION,
    ZOOM_SPEED,
    ZOOM_DURATION,
)

_LOGGER = logging.getLogger(__name__)

PTZ_DIRECTIONS = [
    {"key": "right", "name": "Droite", "x": PTZ_SPEED, "y": 0, "icon": "mdi:pan-right"},
    {"key": "left", "name": "Gauche", "x": -PTZ_SPEED, "y": 0, "icon": "mdi:pan-left"},
    {"key": "up", "name": "Haut", "x": 0, "y": PTZ_SPEED, "icon": "mdi:pan-up"},
    {"key": "down", "name": "Bas", "x": 0, "y": -PTZ_SPEED, "icon": "mdi:pan-down"},
]

ZOOM_ACTIONS = [
    {"key": "zoom_in", "name": "Zoom +", "speed": ZOOM_SPEED, "icon": "mdi:magnify-plus"},
    {"key": "zoom_out", "name": "Zoom -", "speed": -ZOOM_SPEED, "icon": "mdi:magnify-minus"},
]

DEFAULT_PRESET_NAMES = ["Entrée", "Garage", "Jardin"]
DEFAULT_PRESET_TOKENS = ["preset_1", "preset_2", "preset_3"]


def _get_presets(entry: ConfigEntry) -> list[dict]:
    """Get presets from entry data."""
    presets: list[dict] = []
    preset_names = [
        entry.options.get(
            CONF_PRESET_1,
            entry.data.get(CONF_PRESET_1, DEFAULT_PRESET_NAMES[0]),
        ),
        entry.options.get(
            CONF_PRESET_2,
            entry.data.get(CONF_PRESET_2, DEFAULT_PRESET_NAMES[1]),
        ),
        entry.options.get(
            CONF_PRESET_3,
            entry.data.get(CONF_PRESET_3, DEFAULT_PRESET_NAMES[2]),
        ),
    ]
    for idx, name in enumerate(preset_names, start=1):
        preset_name = name.strip()
        if preset_name:
            presets.append(
                {
                    "number": idx,
                    "name": preset_name,
                    "token": DEFAULT_PRESET_TOKENS[idx - 1],
                }
            )
    return presets


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ONVIF PTZ buttons from a config entry."""
    entities = [
        OnvifPtzButton(entry, direction) for direction in PTZ_DIRECTIONS
    ]
    # Ajouter les boutons de zoom
    entities.extend([
        OnvifPtzZoomButton(entry, zoom_action) for zoom_action in ZOOM_ACTIONS
    ])
    # Ajouter les boutons de preset
    presets = _get_presets(entry)
    entities.extend([
        OnvifPtzSavePresetButton(entry, preset) for preset in presets
    ])
    entities.extend([
        OnvifPtzPresetButton(entry, preset) for preset in presets
    ])
    async_add_entities(entities)


class OnvifPtzButton(ButtonEntity):
    """A button that triggers a PTZ movement."""

    def __init__(self, entry: ConfigEntry, direction: dict) -> None:
        """Initialize the PTZ button."""
        camera_name = entry.data[CONF_CAMERA_NAME]
        self._entry = entry
        self._direction = direction
        self._attr_name = f"{camera_name} PTZ {direction['name']}"
        self._attr_unique_id = f"{entry.entry_id}_ptz_{direction['key']}"
        self._attr_icon = direction["icon"]
        model_key = entry.data.get(CONF_CAMERA_MODEL, "")
        model_info = CAMERA_MODELS.get(model_key, {})
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": camera_name,
            "manufacturer": model_info.get("manufacturer", "ONVIF"),
            "model": model_info.get("model", "PTZ Camera"),
        }

    def _send_ptz(self) -> None:
        """Send PTZ move + stop commands (blocking)."""
        data = self._entry.data
        host = data[CONF_HOST]
        port = data[CONF_PORT]
        username = data[CONF_USERNAME]
        password = data[CONF_PASSWORD]
        token = data.get(CONF_PROFILE_TOKEN, "Profile000")
        auth = HTTPDigestAuth(username, password)
        url = f"http://{host}:{port}/onvif/ptz_service"
        headers = {"Content-Type": "application/soap+xml"}

        x = self._direction["x"]
        y = self._direction["y"]

        soap_move = f"""<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <ContinuousMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>{token}</ProfileToken>
      <Velocity>
        <PanTilt x="{x}" y="{y}" xmlns="http://www.onvif.org/ver10/schema"/>
      </Velocity>
    </ContinuousMove>
  </Body>
</Envelope>"""

        soap_stop = f"""<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <Stop xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>{token}</ProfileToken>
      <PanTilt>true</PanTilt>
    </Stop>
  </Body>
</Envelope>"""

        try:
            requests.post(url, data=soap_move, headers=headers, auth=auth, timeout=5)
            time.sleep(PTZ_DURATION)
            requests.post(url, data=soap_stop, headers=headers, auth=auth, timeout=5)
        except requests.RequestException as err:
            _LOGGER.error("PTZ %s failed: %s", self._direction["key"], err)

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hass.async_add_executor_job(self._send_ptz)


class OnvifPtzZoomButton(ButtonEntity):
    """A button that triggers a PTZ zoom action."""

    def __init__(self, entry: ConfigEntry, zoom_action: dict) -> None:
        """Initialize the PTZ zoom button."""
        camera_name = entry.data[CONF_CAMERA_NAME]
        self._entry = entry
        self._zoom_action = zoom_action
        self._attr_name = f"{camera_name} {zoom_action['name']}"
        self._attr_unique_id = f"{entry.entry_id}_zoom_{zoom_action['key']}"
        self._attr_icon = zoom_action["icon"]
        model_key = entry.data.get(CONF_CAMERA_MODEL, "")
        model_info = CAMERA_MODELS.get(model_key, {})
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": camera_name,
            "manufacturer": model_info.get("manufacturer", "ONVIF"),
            "model": model_info.get("model", "PTZ Camera"),
        }

    def _send_zoom(self) -> None:
        """Send zoom move + stop commands (blocking)."""
        data = self._entry.data
        host = data[CONF_HOST]
        port = data[CONF_PORT]
        username = data[CONF_USERNAME]
        password = data[CONF_PASSWORD]
        token = data.get(CONF_PROFILE_TOKEN, "Profile000")
        auth = HTTPDigestAuth(username, password)
        url = f"http://{host}:{port}/onvif/ptz_service"
        headers = {"Content-Type": "application/soap+xml"}

        zoom_speed = self._zoom_action["speed"]

        soap_zoom = f"""<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <ContinuousMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>{token}</ProfileToken>
      <Velocity>
        <Zoom x="{zoom_speed}" xmlns="http://www.onvif.org/ver10/schema"/>
      </Velocity>
    </ContinuousMove>
  </Body>
</Envelope>"""

        soap_stop = f"""<?xml version="1.0"?>
<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope">
  <Body>
    <Stop xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>{token}</ProfileToken>
      <Zoom>true</Zoom>
    </Stop>
  </Body>
</Envelope>"""

        try:
            requests.post(url, data=soap_zoom, headers=headers, auth=auth, timeout=5)
            time.sleep(ZOOM_DURATION)
            requests.post(url, data=soap_stop, headers=headers, auth=auth, timeout=5)
        except requests.RequestException as err:
            _LOGGER.error("Zoom %s failed: %s", self._zoom_action["key"], err)

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hass.async_add_executor_job(self._send_zoom)


class OnvifPtzSavePresetButton(ButtonEntity):
    """A button that saves the current position as a PTZ preset."""

    def __init__(self, entry: ConfigEntry, preset: dict) -> None:
        """Initialize the save-preset button."""
        camera_name = entry.data[CONF_CAMERA_NAME]
        self._entry = entry
        self._preset = preset
        self._attr_name = f"{camera_name} Définir {preset['name']}"
        self._attr_unique_id = f"{entry.entry_id}_preset_save_{preset['number']}"
        self._attr_icon = "mdi:bookmark-plus-outline"
        model_key = entry.data.get(CONF_CAMERA_MODEL, "")
        model_info = CAMERA_MODELS.get(model_key, {})
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": camera_name,
            "manufacturer": model_info.get("manufacturer", "ONVIF"),
            "model": model_info.get("model", "PTZ Camera"),
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hass.services.async_call(
            DOMAIN,
            "set_preset",
            {
                "entry_id": self._entry.entry_id,
                "preset_name": self._preset["name"],
                "preset_token": self._preset["token"],
            },
            blocking=True,
        )


class OnvifPtzPresetButton(ButtonEntity):
    """A button that triggers movement to a PTZ preset position."""

    def __init__(self, entry: ConfigEntry, preset: dict) -> None:
        """Initialize the PTZ preset button."""
        camera_name = entry.data[CONF_CAMERA_NAME]
        self._entry = entry
        self._preset = preset
        self._attr_name = f"{camera_name} {preset['name']}"
        self._attr_unique_id = f"{entry.entry_id}_preset_goto_{preset['number']}"
        self._attr_icon = "mdi:map-marker"
        model_key = entry.data.get(CONF_CAMERA_MODEL, "")
        model_info = CAMERA_MODELS.get(model_key, {})
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": camera_name,
            "manufacturer": model_info.get("manufacturer", "ONVIF"),
            "model": model_info.get("model", "PTZ Camera"),
        }

    def _goto_preset(self) -> None:
        """Go to the selected preset using the integration service."""
        return None

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hass.services.async_call(
            DOMAIN,
            "goto_preset",
            {
                "entry_id": self._entry.entry_id,
                "preset_token": self._preset["token"],
            },
            blocking=True,
        )