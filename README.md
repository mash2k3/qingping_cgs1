# Qingping Pro AQM component

**Before you begin you must enable mqtt on the device. Follow the instructions provided by GreyEarl below HACS insallation section.**
After that is complete continue with HACS installation.

## HACS Installation
- Go to http://homeassistant.local:8123/hacs/integrations
- Add https://github.com/mash2k3/qingping_cgs1 custom integration repository
- Download the Qingping Pro AQM repository
- Go to Home Assistant devices/integrations and add new integration
- Choose "Qingping Pro AQM" from the list and follow the config flow steps

# qingping-air-monitor-mqtt
Use local MQTT functionality of the Qingping Air Monitor

The goal is to have a fully functioning device without the need or dependency of the cloud. For this to work the initial setup does need internet access to sync your MQTT settings with the device. At moment of writing there is no option to insert the settings via the GUI of the device.

**Note!** ⚠️ Make sure you have at least firmware 4.1.8_0267 to accomodate option number two below.

## Options
There are two ways getting MQTT to work on your Qingping Air Monitor.

1. Connect to support@qingping.co (easiest way)
2. Configuring yourself via https://developer.qingping.co/ (the more customizable way)

For option number one you connect to support and mention you want to use the 'Privatization function' of your device. List the MAC address and your MQTT details. You will get a reply back to factory reset your device.
After resetting the MQTT setting will be synced with your device. From that point you monitor traffic to your MQTT server to verify the workings.

Option number is described in more detail below.

## Pairing and configuring your device

For this you need to download either Qingping+ or the Qingping IoT app on your Android or iOS device. My preference is the IoT app, so the following instructions are based on this.

1. Go to settings on the Air Monitor and select either 'Qingping+ App' or 'Qingping IoT App'. We choose the latter in this case.
2. Pair the device with app and follow the instructions both on the app as on the screen of Air Monitor.
3. Now go to https://developer.qingping.co/login. Register and/or login.
4. Go to 'Private Access Config and select Configurations. Create a new configuration. This will contain your MQTT and interval settings. Fill in as shown as example.
   
![image](https://github.com/GreyEarl/qingping-air-monitor-mqtt/assets/33351068/3dc2df5d-ecba-42a4-9164-897d9b88d98e)

5. Click on the edit button in the 'Self-built MQTT information' section and fill in according to your situation. The MAC address is meant to be used as an identifier if you have multiple devices.

![image](https://github.com/GreyEarl/qingping-air-monitor-mqtt/assets/33351068/ee11872a-9cc5-4d79-9951-9948facb8a59)

6. Now go back to the 'Private Access Config' and select Device.

![image](https://github.com/GreyEarl/qingping-air-monitor-mqtt/assets/33351068/ed3084d2-536a-4985-9e2d-c2f8f44005a8)

7. Add a new device, select your device model and you should see your newly added device as paired earlier in the app.
8. Continue and select the configuration you created before.

![image](https://github.com/GreyEarl/qingping-air-monitor-mqtt/assets/33351068/9e7a60d1-ee03-4491-9907-66816fd28dce)

You should be done now. If you don't see activity from the device to your MQTT server, reboot the device. You can use MQTT Explorer to validate and/or troubleshoot. On the device you can also check Settings > Private Cloud. Here you can see the connection       status to your MQTT server.

You can now disable internet access or block the DNS requests the device is sending. Be aware, the device could be generating a lot of DNS requests if it senses no internet connection. I have given this as feedback to Qingping. Perhaps in later firmware updates the device will behave differently.

**Note! ⚠️ If you change the configuration from now on, you need to factory reset the device to apply the changes.**

