# Qingping integration for Home Assistant

<img src="https://brands.home-assistant.io/qingping_cgs1/dark_icon.png" alt="Qingping CGSx Icon" width="150" align="left" style="margin-right: 20px;">

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs) ![Download](https://img.shields.io/github/downloads/mash2k3/qingping_cgs1/total.svg?label=Downloads) ![Analytics](https://img.shields.io/badge/dynamic/json?label=Installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.qingping_cgs1.total)

This custom component integrates the Qingping devices with Home Assistant, allowing you to monitor various environmental parameters in realtime.
<br /><br /><br />
## Requirements

- MQTT integration installed and configured.
- Enable MQTT on Qingping devices using instructions below.
- HACS installed.

## Supported Devices

|   | Model | MQTT Format |
|---|-------|-------------|
| <img width="64" height="64" alt="image" src="https://github.com/user-attachments/assets/860613a7-2b3d-4cd6-a77c-a007195277b2" /> | Air Monitor Lite `(CGDN1)` | JSON |
| <img width="64" height="74" alt="image" src="https://github.com/user-attachments/assets/8be6d4fc-bf5f-4c2d-b8f4-2c406e70aa88" /> | Air Monitor Pro `(CGS1)` | JSON |
| <img width="64" height="74" alt="image" src="https://github.com/user-attachments/assets/394e61fa-47d8-46e3-a034-041122daf1e4" /> | Air Monitor Pro 2 `(CGS2)` | JSON |
| <img width="64" height="64" alt="image" src="https://github.com/user-attachments/assets/dee1356d-1c6b-4fcc-9640-77772e87b652" /> | Temp & RH Monitor Pro S `(CGP22W)` | TLV Binary |
| <img width="64" height="64" alt="image" src="https://github.com/user-attachments/assets/b7c993cb-8a1f-418b-bc38-387daba02756" /> | Temp & RH Barometer Pro S `(CGP23W)` | TLV Binary |
| <img width="64" height="64" alt="image" src="https://github.com/user-attachments/assets/c23b6cbf-ba75-486b-b221-73cd2b18105d" /> | CO₂ & Temp & RH Monitor `(CGP22C)` | TLV Binary |
| <img width="64" height="64" alt="image" src="https://github.com/user-attachments/assets/8b758081-20b9-49f4-a97e-500cab179291" /> | Indoor Environment Monitor `(CGR1PW, CGR1W)` | TLV Binary |
 
## Features

- Automatic discovery of Qingping devices *
- Real-time updates of air quality data
- Configurable offsets
- Configuration entites
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
2. Download the Qingping repository.
3. Restart Home Assistant
4. Go to "Configuration" -> "Integrations" and click "+" to add a new integration
5. Search for "Qingping" and follow the configuration steps

## Configuration

<img src="https://github.com/user-attachments/assets/8c712b1f-e13d-424b-8239-16046bbf50ff" alt="Device Discovery" width="250" align="left" ></img>
- The integration supports automatic discovery of Qingping devices.<br /> 
`⚠️ For discovery: JSON devices must be actively sending data, while TLV devices require a 2-second button press to appear in the list.`
- Make sure to select the correct model from dropdown in order to get the correct sensors.
- If your device is not discovered automatically, you can add it manually by providing the MAC address. 
`⚠️ Do not include : in your MAC address. example: 532D38701E1F`
<br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />

## How it Works
<img src="https://github.com/user-attachments/assets/55a42477-59a7-48b6-b70b-f743c5e2a69a" alt="Device Discovery" width="275" align="right">

1. **Device Discovery**: The integration uses MQTT to discover Qingping devices on your network. It listens for messages on the MQTT topic `qingping/#` to identify available devices.

2. **Configuration**: Once a device is discovered, you can add it to your Home Assistant instance through the UI. The integration will prompt you to enter a name and model for the device and confirm its MAC address.

3. **Sensors**: The integration creates several sensors for each Qingping CGS1/CGS2/CGDN1 device:
   - Temperature
   - Humidity
   - CO2 level
   - PM2.5
   - PM10
   - TVOC (ppb, ppm and mg/m³) `Only on CGS1`
   - eTVOC (ppb, VOC index and mg/m³) `Only on CGS2`
   - Noise level `Only on CGS2, CGR1PW, CGR1W`
   - Temp & Humidity Offsets
   - PM2.5 Offsets
   - PM10 Offsets
   - TVOC Offsets `Only on CGS1`
   - eTVOC Offsets `Only on CGS2`
   - Pressure Offset `Only on CGP23W`
   - CO2 Offsets
   - CO₂ Interval `Only on CGP22C`
   - Auto Sliding `Only on CGDN1`
   - Auto CO2 Calibration `Only on CGDN1, CGP22C, CGR1PW, CGR1W`
   - Manual Calibration `Only on CGDN1, CGP22C, CGR1PW, CGR1W`
   - Night Mode `Only on CGDN1`
   - Power Off Time `Only on CGDN1, CGP22C`
   - Screensaver `Only on CGDN1`
   - Timezone `Only on CGDN1`
   - Pressure `Only on CGP23W`
   - Light/Illuminance `Only on CGR1PW, CGR1W`
   - Battery Charging State
   - Battery level
   - Device status (online/offline)
   - Firmware version
   - Report type (realtime /historic) `⚠️ TLV Devices real-time mode only work when device is USB powered`
   - MAC address

4. **TVOC Sensor**: The sensor can be set to 3 different measurement units, by default it is ppb. The component converts from ppb to get ppm and mg/m³.
   - ppm = ppb/1000
   - mg/m³ = ppb/218.77<br />
   
   **eTVOC Sensor**: The sensor can be set to 3 different measurement units, by default it is VOC index. The component converts from voc index to get ppb and mg/m³.
   - ppb = ( math.log ( 501 - voc_index ) - 6.24) * -2215.4
   - mg/m³ = ( ppb * 4.5 * 10 + 5 ) / 10 / 1000
      
5. **Data Updates**: The component subscribes to MQTT messages from the device. When new data is received, it updates the relevant sensors in Home Assistant.
   - ⚠️ Configuration changes **only work when device is USB powered** `Only on TLV Devices`
   - ⚠️ Real-time mode **only work when device is USB powered** `Only on TLV Devices`

7. **Offset Adjustments**: The integration allows you to set offset values for sesor readings. These offsets are applied to the device before it's displayed in Home Assistant.

8. **Reporting**: You can configure how often the device should report new data.
   - **Update Interval**: This is done through a number entity that allows you to set the update interval in seconds. `Only on JSON Devices, JSON devices only support realtime data on this integration`
   - **Report Interval**: How often device sends data (10-60 minutes, historic mode only) `Only on TLV Devices`
   - **Sample Interval**: How often device reads sensors (10-300 seconds, historic mode only) `Only on TLV Devices`
   - **Report Mode**: Manual override for real-time/historic mode `Only on TLV Devices`

9. **Configuration Publishing**: The integration periodically publishes configuration messages to the device via MQTT. This ensures that the device maintains the correct reporting interval, realtime reporting and other settings. `⚠️ Note: For battery operating TLV devices, configuration changes only work while device is plugged into USB power`

10. **Status Monitoring**:
    - Real-time mode: Offline after 5 minutes of no activity. `JSON and TLV Devices`
    - Historic mode: Offline after 15 minutes of no activity. `Only on TLV Devices`

11. **Unit Conversion**:
    - The integration automatically converts temperature readings to the unit system configured in your Home Assistant instance (Celsius or Fahrenheit). `Only on JSON Devices`
    - Temperature Unit: Switch between Celsius (°C) and Fahrenheit (°F) on device page  `Only on TLV Devices`
    -  ⚠️ Time format (12h/24h) cannot be changed via MQTT Yet.  `Only on TLV Devices`
    
13. **Automatic Report Mode Switching**: `Only on TLV Devices`
    - Real-time mode: Automatically enabled when USB powered (fast updates every 3-5 seconds)
    - Historic mode: Automatically enabled when on battery (slower updates, battery friendly)

14. **TLV Protocol Support**: Newer devices use TLV (Type-Length-Value) binary format instead of JSON:
    - Automatic detection of message format
    - Support for historical data buffering (CMD 0x42)
    - Always displays most recent sensor readings
    - Enhanced configuration options via TLV commands

## Troubleshooting

If you encounter any issues:
1. Check that your Qingping device can send data via MQTT
2. Ensure MQTT is set up on each device as instructed
3. Ensure that MQTT is properly set up in your Home Assistant instance
4. Check the Home Assistant logs for any error messages related to this integration

## Contributing

Contributions to this project are welcome! Please feel free to submit a Pull Request.

Buy me a coffee: https://buymeacoffee.com/mash2k3

## Support

If you have any questions or need help, please open an issue on GitHub.

## Acknowledgments

Special thanks to the **Qingping team** for their technical support and for providing sample devices to help improve this integration for the community. Their collaboration has been invaluable in bringing enhanced support for TLV protocol devices and advanced configuration features to Home Assistant users.
