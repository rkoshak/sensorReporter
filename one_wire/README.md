# Sensors that use the 1-Wire interface

This module contains:
* [one_wire.ds18x20_sensor.Ds18x20Sensor](#one_wireds18x20_sensords18x20sensor)


## `one_wire.ds18x20_sensor.Ds18x20Sensor`

A polling sensor that reads temperature from a DS18S20 or DS18B20 1-Wire bus sensor connected wired to the Raspberry Pi's GPIO pins.

### Dependencies

This sensor communicates via the `1-Wire interface` on your Raspberry Pi.
The 1-Wire interface uses GPIO4 by default.
This can be changed in the `/boot/config.txt`, see details [here](https://pinout.xyz/pinout/1_wire).
To work properly it also need the kernel modules w1-gpio and w1-therm.

To enable the 1-Wire interface run (boot partition must be writable):

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh one_wire
```

To load the `w1-gpio` and `w1-therm` kernel modules, add the following to `/etc/modules`:

```bash
# Load modules for DS18x20 1-Wire temperature sensors
w1-gpio
w1-therm
```

Reboot the Raspberry Pi.

### Parameters

| Parameter     | Required           | Restrictions                            | Purpose                                                                                                                                                     |
|---------------|--------------------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`       | X                  | `one_wire.ds18x20_sensor.Ds18x20Sensor` |                                                                                                                                                             |
| `Connections` | X                  | Dictionary of connectors                | Defines where to publish the sensor status for each connection.                                                                                             |
| `Level`       |                    | `DEBUG`, `INFO`, `WARNING`, `ERROR`     | Override the global log level and use another one for this sensor.                                                                                          |
| `Poll`        | X                  | Positive number                         | Refresh interval for the sensor in seconds.                                                                                                                 |
| `Mac`         | X                  |                                         | Full 1-Wire device address. To list all 1-Wire devices, run `ls /sys/bus/w1/devices`. To read a specific one, run `cat /sys/bus/w1/devices/<Mac>/w1_slave`. |
| `TempUnit`    |                    | `F` or `C`                              | Temperature unit to use, defaults to `C`.                                                                                                                   |
| `Smoothing`   |                    | Boolean                                 | If `True`, publishes the average of the last five readings instead of each individual reading.                                                              |

### Outputs

The DS18x20 sensor has only one output, the temperature.

### Configuration Example

Publishes to a MQTT connection with name `MQTT`:

```yaml
#Logging and connection configuration omitted

SensorTempOutside:
    Class: one_wire.ds18x20_sensor.Ds18x20Sensor
    Connections:
        MQTT:
            StateDest: temp/outside
    Poll: 10
    Mac: 28-a66c801e64ff
```

