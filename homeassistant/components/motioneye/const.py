"""Constants for the motionEye integration."""
from datetime import timedelta
from typing import Final

from motioneye_client.const import (
    KEY_WEB_HOOK_CS_CAMERA_ID,
    KEY_WEB_HOOK_CS_CHANGED_PIXELS,
    KEY_WEB_HOOK_CS_DESPECKLE_LABELS,
    KEY_WEB_HOOK_CS_EVENT,
    KEY_WEB_HOOK_CS_FILE_PATH,
    KEY_WEB_HOOK_CS_FILE_TYPE,
    KEY_WEB_HOOK_CS_FPS,
    KEY_WEB_HOOK_CS_FRAME_NUMBER,
    KEY_WEB_HOOK_CS_HEIGHT,
    KEY_WEB_HOOK_CS_HOST,
    KEY_WEB_HOOK_CS_MOTION_CENTER_X,
    KEY_WEB_HOOK_CS_MOTION_CENTER_Y,
    KEY_WEB_HOOK_CS_MOTION_HEIGHT,
    KEY_WEB_HOOK_CS_MOTION_VERSION,
    KEY_WEB_HOOK_CS_MOTION_WIDTH,
    KEY_WEB_HOOK_CS_NOISE_LEVEL,
    KEY_WEB_HOOK_CS_THRESHOLD,
    KEY_WEB_HOOK_CS_WIDTH,
)

DOMAIN: Final = "motioneye"

ATTR_EVENT_TYPE: Final = "event_type"
ATTR_WEBHOOK_ID: Final = "webhook_id"

CONF_ACTION: Final = "action"
CONF_CLIENT: Final = "client"
CONF_COORDINATOR: Final = "coordinator"
CONF_ADMIN_PASSWORD: Final = "admin_password"
CONF_ADMIN_USERNAME: Final = "admin_username"
CONF_STREAM_URL_TEMPLATE: Final = "stream_url_template"
CONF_SURVEILLANCE_USERNAME: Final = "surveillance_username"
CONF_SURVEILLANCE_PASSWORD: Final = "surveillance_password"
CONF_WEBHOOK_SET: Final = "webhook_set"
CONF_WEBHOOK_SET_OVERWRITE: Final = "webhook_set_overwrite"

DEFAULT_WEBHOOK_SET: Final = True
DEFAULT_WEBHOOK_SET_OVERWRITE: Final = False
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)

EVENT_MOTION_DETECTED: Final = "motion_detected"
EVENT_FILE_STORED: Final = "file_stored"

EVENT_MOTION_DETECTED_KEYS: Final = [
    KEY_WEB_HOOK_CS_EVENT,
    KEY_WEB_HOOK_CS_FRAME_NUMBER,
    KEY_WEB_HOOK_CS_CAMERA_ID,
    KEY_WEB_HOOK_CS_CHANGED_PIXELS,
    KEY_WEB_HOOK_CS_NOISE_LEVEL,
    KEY_WEB_HOOK_CS_WIDTH,
    KEY_WEB_HOOK_CS_HEIGHT,
    KEY_WEB_HOOK_CS_MOTION_WIDTH,
    KEY_WEB_HOOK_CS_MOTION_HEIGHT,
    KEY_WEB_HOOK_CS_MOTION_CENTER_X,
    KEY_WEB_HOOK_CS_MOTION_CENTER_Y,
    KEY_WEB_HOOK_CS_THRESHOLD,
    KEY_WEB_HOOK_CS_DESPECKLE_LABELS,
    KEY_WEB_HOOK_CS_FPS,
    KEY_WEB_HOOK_CS_HOST,
    KEY_WEB_HOOK_CS_MOTION_VERSION,
]

EVENT_FILE_STORED_KEYS: Final = [
    KEY_WEB_HOOK_CS_EVENT,
    KEY_WEB_HOOK_CS_FRAME_NUMBER,
    KEY_WEB_HOOK_CS_CAMERA_ID,
    KEY_WEB_HOOK_CS_NOISE_LEVEL,
    KEY_WEB_HOOK_CS_WIDTH,
    KEY_WEB_HOOK_CS_HEIGHT,
    KEY_WEB_HOOK_CS_FILE_PATH,
    KEY_WEB_HOOK_CS_FILE_TYPE,
    KEY_WEB_HOOK_CS_THRESHOLD,
    KEY_WEB_HOOK_CS_FPS,
    KEY_WEB_HOOK_CS_HOST,
    KEY_WEB_HOOK_CS_MOTION_VERSION,
]

EVENT_FILE_URL: Final = "file_url"
EVENT_MEDIA_CONTENT_ID: Final = "media_content_id"

MOTIONEYE_MANUFACTURER: Final = "motionEye"

SERVICE_SET_TEXT_OVERLAY: Final = "set_text_overlay"
SERVICE_ACTION: Final = "action"
SERVICE_SNAPSHOT: Final = "snapshot"

SIGNAL_CAMERA_ADD: Final = f"{DOMAIN}_camera_add_signal.{{}}"
SIGNAL_CAMERA_REMOVE: Final = f"{DOMAIN}_camera_remove_signal.{{}}"

TYPE_MOTIONEYE_ACTION_SENSOR = f"{DOMAIN}_action_sensor"
TYPE_MOTIONEYE_MJPEG_CAMERA: Final = "motioneye_mjpeg_camera"
TYPE_MOTIONEYE_SWITCH_BASE: Final = f"{DOMAIN}_switch"

WEB_HOOK_SENTINEL_KEY: Final = "src"
WEB_HOOK_SENTINEL_VALUE: Final = "hass-motioneye"
