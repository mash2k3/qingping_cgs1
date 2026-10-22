"""Constants for the Qingping integration."""

DOMAIN = "qingping_cgs1"
CONF_MAC = "mac"
CONF_NAME = "name"
CONF_MODEL = "model"

# Sensor types
SENSOR_BATTERY = "battery"
SENSOR_CO2 = "co2"
SENSOR_HUMIDITY = "humidity"
SENSOR_PM10 = "pm10"
SENSOR_PM25 = "pm25"
SENSOR_TEMPERATURE = "temperature"
SENSOR_TVOC = "tvoc"
SENSOR_ETVOC = "tvoc_index"
SENSOR_TLV_ETVOC = "tvoc"
SENSOR_NOISE = "noise"

# Unit of measurement
PERCENTAGE = "%"
PPM = "ppm"
CONCENTRATION = "µg/m³"
PPB = "ppb"
DB = "dB"
CONF_TVOC_UNIT = "tvoc_unit"
CONF_TEMPERATURE_UNIT = "temperature_unit"
CONF_ETVOC_UNIT = "etvoc_unit"
CONF_PRESSURE_OFFSET = "pressure_offset"
CONF_LED_INDICATOR = "led_indicator"

# Offsets
CONF_TEMPERATURE_OFFSET = "temperature_offset"
CONF_HUMIDITY_OFFSET = "humidity_offset"
CONF_UPDATE_INTERVAL = "update_interval"
# TLV device intervals
CONF_REPORT_INTERVAL = "report_interval"  # Minutes (KEY 0x04)
CONF_SAMPLE_INTERVAL = "sample_interval"  # Seconds (KEY 0x05)
# TLV device report modes
CONF_REPORT_MODE = "report_mode"
REPORT_MODE_HISTORIC = "historic"
REPORT_MODE_REALTIME = "realtime"

# Default values for offsets and update interval
DEFAULT_OFFSET = 0
DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes (was 15 seconds)

# MQTT topics
MQTT_TOPIC_PREFIX = "qingping"

# Configuration message
ATTR_TYPE = "type"
ATTR_UP_ITVL = "up_itvl"
ATTR_DURATION = "duration"

DEFAULT_TYPE = "12"
DEFAULT_DURATION = "21600"

SENSOR_PRESSURE = "pressure"
SENSOR_LIGHT = "light"
SENSOR_SIGNAL_STRENGTH = "signal_strength"
# Device models
# JSON format devices (old protocol)
JSON_MODELS = ["CGS1", "CGS2", "CGDN1"]
# TLV binary format devices (new protocol)
TLV_MODELS = ["CGP22C", "CGP23W", "CGP22W","CGR1W", "CGR1PW"]
# All supported models
QP_MODELS = JSON_MODELS + TLV_MODELS
DEFAULT_MODEL = "CGS1"

# Model to Product ID mapping (for TLV devices)
MODEL_PRODUCT_IDS = {
    "CGP22C": 93,  # CO₂ & Temp & RH Monitor
    "CGP23W": 38,  # Temp & RH Barometer Pro S
    "CGP22W": 92,  # Temp & RH Monitor Pro S
    "CGR1W": 96,  # Indoor Environment Monitor Screenless
    "CGR1PW": 96,  # Indoor Environment Monitor
}

# Device-specific settings
CONF_CO2_ASC = "co2_asc"
CONF_CO2_CALIBRATION = "co2_calibration"
CONF_CO2_OFFSET = "co2_offset"
CONF_PM25_OFFSET = "pm25_offset"
CONF_PM10_OFFSET = "pm10_offset"
CONF_NOISE_OFFSET = "noise_offset"
CONF_TVOC_OFFSET = "tvoc_zoom"
CONF_TVOC_INDEX_OFFSET = "tvoc_index_zoom"

# Default values for device settings
DEFAULT_SENSOR_OFFSET = 0

# CGDN1 specific settings
CONF_POWER_OFF_TIME = "power_off_time"
CONF_DISPLAY_OFF_TIME = "display_off_time"
CONF_NIGHT_MODE_START_TIME = "night_mode_start_time"
CONF_NIGHT_MODE_END_TIME = "night_mode_end_time"
CONF_AUTO_SLIDING_TIME = "auto_slideing_time"
CONF_SCREENSAVER_TYPE = "screensaver_type"
CONF_TIMEZONE = "timezone"

# Fork: Per-device configurable options
CONF_AUTO_SWITCH_REPORT_MODE = "auto_switch_report_mode"
CONF_OFFLINE_TIMEOUT_MINUTES = "offline_timeout_minutes"
DEFAULT_OFFLINE_TIMEOUT_MINUTES = 65
DEFAULT_AUTO_SWITCH_REPORT_MODE = False