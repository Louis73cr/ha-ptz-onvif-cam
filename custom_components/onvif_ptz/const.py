"""Constants for the ONVIF PTZ integration."""

DOMAIN = "onvif_ptz"

CONF_CAMERA_NAME = "camera_name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PROFILE_TOKEN = "profile_token"
CONF_CAMERA_MODEL = "camera_model"

CAMERA_MODELS = {
    "imou_ipc_s21fe": {"name": "Imou - IPC-S21FE", "manufacturer": "Imou", "model": "IPC-S21FE"},
}

DEFAULT_PORT = 80
DEFAULT_PROFILE_TOKEN = "Profile000"

PTZ_SPEED = 0.3
PTZ_DURATION = 0.2
