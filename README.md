# Qingping Pro Air Quality Monitor [CGS1] integration

**Note!⚠️ Before you begin you must enable mqtt on the device. Follow the instructions provided by GreyEarl [here](https://github.com/mash2k3/qingping_cgs1/blob/main/enableMQTT.md).**
</br>After that is complete continue with HACS installation.

## Requirements
- MQTT integration installed and configured.
- Enable MQTT on Qingping AQM devices using instructions above.
  </b> Client ID, Up Topic and Down Topic must be filled out extacly as shown in [example](https://private-user-images.githubusercontent.com/33351068/273692035-ee11872a-9cc5-4d79-9951-9948facb8a59.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MjUxNTY2MDcsIm5iZiI6MTcyNTE1NjMwNywicGF0aCI6Ii8zMzM1MTA2OC8yNzM2OTIwMzUtZWUxMTg3MmEtOWNjNS00ZDc5LTk5NTEtOTk0OGZhY2I4YTU5LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDA5MDElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwOTAxVDAyMDUwN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTlmZDdkMDNiMDdjOGI3ODhmODM2Zjk0OTI0ODBlYzkxM2RhODc2ZDE0OTY5MTYxMzFlMDA0YTMyODVmMGRhNzQmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.N_q8hPLFs8DHPib0zDzEfid5q8_4plWgoUwsAd98D38).
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

