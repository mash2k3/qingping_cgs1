"""Constants for the Qingping CGS1 integration."""

DOMAIN = "qingping_cgs1"
CONF_MAC = "mac"
CONF_NAME = "name"

# Sensor types
SENSOR_BATTERY = "battery"
SENSOR_CO2 = "co2"
SENSOR_HUMIDITY = "humidity"
SENSOR_PM10 = "pm10"
SENSOR_PM25 = "pm25"
SENSOR_TEMPERATURE = "temperature"
SENSOR_TVOC = "tvoc"

# Unit of measurement
PERCENTAGE = "%"
PPM = "ppm"
CONCENTRATION = "µg/m³"
PPB = "ppb"
CONF_TVOC_UNIT = "tvoc_unit"

# Offsets
CONF_TEMPERATURE_OFFSET = "temperature_offset"
CONF_HUMIDITY_OFFSET = "humidity_offset"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values for offsets and update interval
DEFAULT_OFFSET = 0
DEFAULT_UPDATE_INTERVAL = 15

# MQTT topics
MQTT_TOPIC_PREFIX = "qingping"

# Configuration message
ATTR_TYPE = "type"
ATTR_UP_ITVL = "up_itvl"
ATTR_DURATION = "duration"

DEFAULT_TYPE = "12"
DEFAULT_DURATION = "86400"