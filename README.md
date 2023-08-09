# Livisi Unofficial Fork

This project is in "works for me" state and I do not advise anyone to use it nor can or will I provide support on how to install it.
It can be added as a custom repo to HACS and then installed as an integration. This will override the existing livisi integration and add the following features:

* Support VariableActuators (Boolean vars in livisi)
* Support motion detector brightness sensor
* Events are sent for button presses and motion detection (basically, device triggers based on these events are also implemented but untested)
* Battery level indicators (experimental und untested, I have to wait until a battery runs out in my installation to see if it works)


## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `livisi`.
1. Download _all_ the files from the `custom_components/livisi/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "livisi"

## Configuration

All configuration in done in the UI

## TODO

* Remove device triggers and replace them by event entities (for motion and button presses, maybe also smoke alert if that's possible)
* Remove LivisiEvent and handle Websocket updates directly in the coordinator - this is useless complexity
* Check how to handle luminance, which is provided in percent by Livisi. Currently we get a warning: `<LivisiSensor> is using native unit of measurement '%' which is not a valid unit for the device class ('illuminance') it is using; expected one of ['lx']`


