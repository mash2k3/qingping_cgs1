# Qingping Pro AQM [CGS1/CGS2] integration for Home Assistant

<img src="https://brands.home-assistant.io/qingping_cgs1/dark_icon.png" alt="Qingping CGSx Icon" width="150" align="left" style="margin-right: 20px;">

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs) ![Download](https://img.shields.io/github/downloads/mash2k3/qingping_cgs1/total.svg?label=Downloads) ![Analytics](https://img.shields.io/badge/dynamic/json?label=Installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.qingping_cgs1.total)

This custom component integrates the Qingping Pro Air Quality Monitor [CGS1/CGS2] with Home Assistant, allowing you to monitor various environmental parameters in realtime.
<br /><br /><br />
## Requirements

- MQTT integration installed and configured.
- Enable MQTT on Qingping AQM devices using instructions below.
- HACS installed.
  
## Features

- Automatic discovery of Qingping CGS1/CGS2 devices
- Real-time updates of air quality data
- Configurable temperature and humidity offsets
- Adjustable update interval
- Automatic unit conversion for temperature
- Device status monitoring
- Battery level monitoring

<div style="clear: both;"></div>

## Installation

> [!NOTE]
> Before you begin you must enable mqtt on the device. Follow the instructions provided by GreyEarl [here](https://github.com/mash2k3/qingping_cgs1/blob/main/enableMQTT.md).
> </br> Client ID, Up Topic and Down Topic must be filled out extacly as shown in [example](https://github.com/user-attachments/assets/48b19fc4-78a5-464c-9a65-cc164d0e3571).
</br>After that is complete continue with HACS installation.

1. Use HACS to install this integration:
   <br /><br /><a href="https://my.home-assistant.io/redirect/hacs_repository/?repository=qingping_cgs1&category=integration&owner=mash2k3" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>
2. Download the Qingping Pro AQM repository
3. Restart Home Assistant
4. Go to "Configuration" -> "Integrations" and click "+" to add a new integration
5. Search for "Qingping Pro AQM" and follow the configuration steps

## Configuration
<img src="https://github.com/user-attachments/assets/b27d218e-e815-4e64-b342-a44b1287d9a1" alt="Device Discovery" width="250" align="left">
The integration supports automatic discovery of Qingping CGS1/CGS2 devices.
<br />If your device is not discovered automatically, you can add it manually by providing the MAC address. 
<br />⚠️ Do not include : in your MAC address. example: 532D38701E1F
<br /><br /><br /><br /><br /><br /><br /><br />


## How it Works
<img src="https://github.com/user-attachments/assets/46567747-a8cb-443e-be23-78a87e741a42" alt="Device Discovery" width="275" align="right">

1. **Device Discovery**: The integration uses MQTT to discover Qingping CGS1/CGS2 devices on your network. It listens for messages on the MQTT topic `qingping/#` to identify available devices.

2. **Configuration**: Once a device is discovered, you can add it to your Home Assistant instance through the UI. The integration will prompt you to enter a name for the device and confirm its MAC address.

3. **Sensors**: The integration creates several sensors for each Qingping CGS1/CGS2 device:
   - Temperature
   - Humidity
   - CO2 level
   - PM2.5
   - PM10
   - TVOC (ppb, ppm and mg/m³) `Only on CGS1`
   - eTVOC (ppb, VOC index and mg/m³) `Only on CGS2`
   - Noise level `Only on CGS2`
   - Battery level
   - Device status (online/offline)
   - Firmware version
   - Report type (12 = realtime / 17 = historic)
   - MAC address

4. **TVOC Sensor**: The sensor can be set to 3 different measurement units, by default it is ppb. The component converts from ppb to get ppm and mg/m³.
   - ppm = ppb/1000
   - mg/m³ = ppb/1000 * 0.0409 * 111.1 (concentration (ppm) x 0.0409 x molecular weight)<br />
   
   **eTVOC Sensor**: The sensor can be set to 3 different measurement units, by default it is VOC index. The component converts from voc index to get ppb and mg/m³.
   - ppb = index * 10
   - mg/m³ = index * 0.0001
      
5. **Data Updates**: The component subscribes to MQTT messages from the device. When new data is received, it updates the relevant sensors in Home Assistant.

6. **Offset Adjustments**: The integration allows you to set offset values for temperature and humidity readings. These offsets are applied to the raw sensor data before it's displayed in Home Assistant.

7. **Update Interval**: You can configure how often the device should report new data. This is done through a number entity that allows you to set the update interval in seconds.

8. **Configuration Publishing**: The integration periodically publishes configuration messages to the device via MQTT. This ensures that the device maintains the correct reporting interval, realtime reporting and other settings.

9. **Status Monitoring**: The integration tracks the device's online/offline status based on the timestamp of the last received message. If no message is received for 5 minutes, the device is considered offline.

10. **Unit Conversion**: The integration automatically converts temperature readings to the unit system configured in your Home Assistant instance (Celsius or Fahrenheit).

## Troubleshooting

If you encounter any issues:
1. Check that your Qingping CGS1/CGS2 device can send data via MQTT
2. Ensure MQTT is set up on each device as instructed
3. Ensure that MQTT is properly set up in your Home Assistant instance
4. Check the Home Assistant logs for any error messages related to this integration

## Contributing

Contributions to this project are welcome! Please feel free to submit a Pull Request.

## Support

If you have any questions or need help, please open an issue on GitHub.
