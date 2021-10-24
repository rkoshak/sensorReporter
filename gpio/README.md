# Sensors that Use GPIO and GPIO Pin Actuator

## `gpio.dht_sensor.DhtSensor`

A Polling Sensor that reads temperature and humidity from a DHT11, DHT22, or AM2302 sensor wired to the GPIO pins.

### Dependencies

This sensor uses the [adaFruit CircuitPython libraries](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup).

```
$ sudo apt-get install libgpiod2
$ sudo pip3 install RPI.GPIO
$ sudo pip3 install adafruit-blinka
$ sudo pip3 install adafruit-circuitpython-dht
```

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `btle_sensor.exec_actuator.ExecSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number | How often to call the command
`Sensor` | X | `DHT11`, `DHT22`, or `AM2302` | The type of the sensor.
`Pin` | X | | GPIO data pin in BMC numbering.
`HumiDest` | X | | Where to publish the humidity.
`TempDest` | X | | Where to publishd the temperature.
`TempUnit` | X | `F` or `C` | The temperature units
`Smoothing` | | Boolean | When `True`, publishes the average of the last five readings instead of each individual reading.

### Example Config

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection1]
Class = openhab_rest.rest_conn.OpenhabREST
Name = openHAB
URL = http://localhost:8080
RefreshItem = Test_Refresh
Level = INFO

[Sensor1]
Class = gpio.dht_sensor.DhtSensor
Connection = openHAB
Poll = 2
Sensor = AM2302
Pin = 7
HumiDest = humidity
TempDest = temperature
TempUnit = F
Smoothing = False
Level = DEBUG
```

## `gpio.rpi_gpio.RpiGpioSensor`

A Sensor that can behave as either a Polling Sensor or a Background Sensor that reports the HIGH/LOW status of a GPIO pin.

### Dependencies

The user running sensor_reporter must have permission to access the GPIO pins.

Depends on RPi.GPIO.

```
$ sudo pip3 install RPI.GPIO
```

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `gpio.rpi_gpio.RpiGpioSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` |  | Positive number | How often to call the command. When not present the sensor will watch the pin in the background and report as it starts to change state.
`PUD` | | The Pull UP/DOWN for the pin | Defaults to "DOWN"
`EventDetection` | | RISING, FALLING, or BOTH | When present, Poll is ignored. Indicates which GPIO event to listen for in the background.
`Destination` | X | | Location/openHAB string item to publish the pin state as OPEN/CLOSED (default).
`Values` | | | Values to replace OPEN,CLOSED message as comma separeted list. Eg. `OFF,ON`
`Short_Press-Dest` | | | Location/openHAB string/datetime item to publish an update after a short button press happend. Which are two chages of the logic level at the selected pin. Eg. with `PUD = DOWN` LOW > HIGH > LOW and the duration between the edges is between `Short_Press-Threshold` and `Long_Press-Threshold`. Works best with `EventDetection = BOTH`
`Short_Press-Threshold` | | float | Devines the lower bound of short button press event in seconds, if the duration of the button press was shorter no update will be send. Usful to ignor false detection of button press due to electrical interferences. (default is 0)
`Long_Press-Dest` | | | Location/openHAB string/datetime item to publish an update after a long button press happend, requires `Long_Press-Threshold`, `Short_Press-Dest`
`Long_Press-Threshold` | | float | Devines the lower bound of long button press event in seconds, if the duration of the button press was shorter a short button event will be triggered

### Example Config

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection1]
Class = openhab_rest.rest_conn.OpenhabREST
Name = openHAB
URL = http://localhost:8080
RefreshItem = Test_Refresh
Level = INFO

[Sensor1]
Class = gpio.rpi_gpio.RpiGpioSensor
Connection = openHAB
Pin = 17
PUD = UP
EventDetection = BOTH
Destination = back_door
Short_Press-Dest = back_door_short
Long_Press-Dest = back_door_long
Long_Press-Threshold = 1.2
Level = INFO

[Sensor2]
Class = gpio.rpi_gpio.RpiGpioSensor
Connection = openHAB
Poll = 1
Pin = 18
PUD = UP
Destination = front_door
Values = OFF,ON
Level = DEBUG
```

## `gpio.rpi_gpio.RpiGpioActuator`

Commands a GPIO pin to go high, low, or if configured with a toggle it goes high for half a second and then goes to low.

### Dependencies

The user running sensor_reporter must have permission to access the GPIO pins.

Depends on RPi.GPIO.

```
$ sudo pip3 install RPI.GPIO
```

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `btle_sensor.exec_actuator.ExecSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`CommandSrc` | X | | Destination/openHAB switch item where commands are received, expects ON/OFF. If Toggle is set all messages trigger a toggle.
`Pin` | X | GPIO Pin in BCM numbering
`InitialState` | | ON or OFF | Optional, when set to ON the pin's state is initialized to HIGH.
`Toggle` | | Boolean | When `True` simulates a button press by setting the pin to HIGH for half a second and then back to LOW. In case of `InitalState` ON it will toggle the other way around.

### Example Config

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection1]
Class = openhab_rest.rest_conn.OpenhabREST
Name = openHAB
URL = http://localhost:8080
RefreshItem = Test_Refresh
Level = INFO

[Actuator0]
Class = gpio.rpi_gpio.RpiGpioActuator
Connection = openHAB
CommandSrc = GarageDoorCmd
Pin = 19
InitialState = ON
Toggle = True
Level = DEBUG
```
