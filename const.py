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
TEMP_CELSIUS = "°C"
CONCENTRATION = "µg/m³"

# MQTT topics
MQTT_TOPIC_PREFIX = "qingping"

# Configuration message
ATTR_TYPE = "type"
ATTR_UP_ITVL = "up_itvl"
ATTR_DURATION = "duration"

DEFAULT_TYPE = "12"
DEFAULT_UP_ITVL = "15"
DEFAULT_DURATION = "86400"

RECONNECTION_INTERVAL = 86400  # 24 hours in seconds