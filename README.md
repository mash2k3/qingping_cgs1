# Qingping Pro AQM [CGS1] integration for Home Assistant

<img src="https://brands.home-assistant.io/qingping_cgs1/dark_icon.png" alt="Qingping CGS1 Icon" width="150" align="left" style="margin-right: 20px;">

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This custom component integrates the Qingping Pro Air Quality Monitor [CGS1] with Home Assistant, allowing you to monitor various environmental parameters in realtime.

## Requirements

- MQTT integration installed and configured.
- Enable MQTT on Qingping AQM devices using instructions below.
- HACS installed.
  
## Features

- Automatic discovery of Qingping CGS1 devices
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
> </br> Client ID, Up Topic and Down Topic must be filled out extacly as shown in [example](https://private-user-images.githubusercontent.com/33351068/273692035-ee11872a-9cc5-4d79-9951-9948facb8a59.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MjUxNTY2MDcsIm5iZiI6MTcyNTE1NjMwNywicGF0aCI6Ii8zMzM1MTA2OC8yNzM2OTIwMzUtZWUxMTg3MmEtOWNjNS00ZDc5LTk5NTEtOTk0OGZhY2I4YTU5LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDA5MDElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwOTAxVDAyMDUwN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTlmZDdkMDNiMDdjOGI3ODhmODM2Zjk0OTI0ODBlYzkxM2RhODc2ZDE0OTY5MTYxMzFlMDA0YTMyODVmMGRhNzQmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.N_q8hPLFs8DHPib0zDzEfid5q8_4plWgoUwsAd98D38).
</br>After that is complete continue with HACS installation.

1. Use HACS to install this integration:
   <br /><br /><a href="https://my.home-assistant.io/redirect/hacs_repository/?repository=qingping_cgs1&category=integration&owner=mash2k3" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>
2. Download the Qingping Pro AQM repository
3. Restart Home Assistant
4. Go to "Configuration" -> "Integrations" and click "+" to add a new integration
5. Search for "Qingping Pro AQM" and follow the configuration steps

## Configuration

The integration supports automatic discovery of Qingping CGS1 devices. If your device is not discovered automatically, you can add it manually by providing the MAC address. 
⚠️ Do not include : in your MAC address. example: 532D38701E1F

## Screenshots

[**Device Page**](https://github.com/user-attachments/assets/0414e373-b107-4545-b42d-32a29f30709b)  
[**Device Discovery**](https://github.com/user-attachments/assets/b27d218e-e815-4e64-b342-a44b1287d9a1)

## How it Works

1. **Device Discovery**: The integration uses MQTT to discover Qingping CGS1 devices on your network. It listens for messages on the MQTT topic `qingping/#` to identify available devices.

2. **Configuration**: Once a device is discovered, you can add it to your Home Assistant instance through the UI. The integration will prompt you to enter a name for the device and confirm its MAC address.

3. **Sensors**: The integration creates several sensors for each Qingping CGS1 device:
   - Temperature
   - Humidity
   - CO2 level
   - PM2.5
   - PM10
   - TVOC
   - Battery level
   - Device status (online/offline)
   - Firmware version
   - Report type (12 = realtime / 17 = historic)
   - MAC address

4. **Data Updates**: The component subscribes to MQTT messages from the device. When new data is received, it updates the relevant sensors in Home Assistant.

5. **Offset Adjustments**: The integration allows you to set offset values for temperature and humidity readings. These offsets are applied to the raw sensor data before it's displayed in Home Assistant.

6. **Update Interval**: You can configure how often the device should report new data. This is done through a number entity that allows you to set the update interval in seconds.

7. **Configuration Publishing**: The integration periodically publishes configuration messages to the device via MQTT. This ensures that the device maintains the correct reporting interval, realtime reporting and other settings.

8. **Status Monitoring**: The integration tracks the device's online/offline status based on the timestamp of the last received message. If no message is received for 5 minutes, the device is considered offline.

9. **Unit Conversion**: The integration automatically converts temperature readings to the unit system configured in your Home Assistant instance (Celsius or Fahrenheit).

## Troubleshooting

If you encounter any issues:
1. Check that your Qingping CGS1 device can send data via MQTT
2. Ensure MQTT is set up on each device as instructed
3. Ensure that MQTT is properly set up in your Home Assistant instance
4. Check the Home Assistant logs for any error messages related to this integration

## Contributing

Contributions to this project are welcome! Please feel free to submit a Pull Request.

## Support

If you have any questions or need help, please open an issue on GitHub.
