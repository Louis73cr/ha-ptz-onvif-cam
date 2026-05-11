"""Constants for the ONVIF PTZ integration."""

DOMAIN = "onvif_ptz"

CONF_CAMERA_NAME = "camera_name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PROFILE_TOKEN = "profile_token"
CONF_CAMERA_MODEL = "camera_model"
CONF_PRESET_1 = "preset_1"
CONF_PRESET_2 = "preset_2"
CONF_PRESET_3 = "preset_3"

CAMERA_MODELS = {
    "imou_ipc_s21fe": {"name": "Imou - IPC-S21FE", "manufacturer": "Imou", "model": "IPC-S21FE"},
}

DEFAULT_PORT = 80
DEFAULT_PROFILE_TOKEN = "Profile000"

PTZ_SPEED = 0.3
PTZ_DURATION = 0.2

# Zoom
ZOOM_SPEED = 0.5
ZOOM_DURATION = 0.2
