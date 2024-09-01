# Qingping Pro Air Quality Monitor [CGS1] integration

**Note!⚠️ Before you begin you must enable mqtt on the device. Follow the instructions provided by GreyEarl [here](https://github.com/mash2k3/qingping_cgs1/blob/main/enableMQTT.md).**
</br>After that is complete continue with HACS installation.

## Requirements
- MQTT integration installed and configured.
- Enable MQTT on Qingping AQM devices using instructions above.
  </b> Client ID, Up Topic and Down Topic must be filled out extacly as shown in [example](https://github.com/mash2k3/qingping_cgs1/blob/main/enableMQTT.md).
- HACS installed.

## HACS Installation
- Go to http://homeassistant.local:8123/hacs/integrations
- Add https://github.com/mash2k3/qingping_cgs1 custom integration repository
- Download the Qingping Pro AQM repository
- Go to Home Assistant devices/integrations and add new integration
- Choose "Qingping Pro AQM" from the list and follow the config flow steps
- Devices should be discovered and listed, if not just manually add them.
- Add the device name and mac address. **Note!**⚠️ do not include : in your mac address. example: 532D38701E1F

## How it works
This integration uses report type 12, which is realtime reporting. Default update interval is set to 15 seconds and it is adjustable in the device config page. By default the Qingping Pro AQM device is set to report type 17, which historic data reporting and updates every 15 minutes.
</br>The integration will set report type to 12 for a duration of 24 hours and when it expires it will reset it again. The same goes if the device goes offline and comes back online.

