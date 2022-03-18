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
`Class` | X | `gpio.dht_sensor.DhtSensor` |
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
Additionally the Sensor can detect toggle events and report the time of the event to different locations depending on the event duration.

### Dependencies

The user running sensor_reporter must have permission to access the GPIO pins.
To grant the `sensorReporter` user GPIO permissions add the user to the group `gpio`:  `sudo adduser sensorReporter gpio`

Depends on RPi.GPIO.

```
$ sudo pip3 install RPI.GPIO
```

### Basic parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `gpio.rpi_gpio.RpiGpioSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` |  | Positive number | How often to call the command. When not present the sensor will watch the pin in the background and report as it starts to change state.
`PUD` | | The Pull UP/DOWN for the pin | Defaults to "DOWN"
`EventDetection` | | RISING, FALLING, or BOTH | When present, Poll is ignored. Indicates which GPIO event to listen for in the background.
`Pin` | X | IO Pin | Pin to use as sensor input, using the pin numbering defined in `PinNumbering` (see below).
`Destination` | X | | Location/openHAB string item to publish the pin state.


### Advanced parameters
For a valid configuration the basic parameters marked as required are necessary, avanced parameters are optional

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Values` | | | Values to replace the default state message as comma separeted list. Eg. `OFF,ON` (default is CLOSED,OPEN)
`Short_Press-Dest` | | | Location/openHAB string/datetime item to publish an update after a short button press happend. Which are two chages of the logic level at the selected pin (eg. LOW, HIGH, LOW) and the duration of the button press is between `Short_Press-Threshold` and `Long_Press-Threshold`. For the recommended setup see example config #2 at the bottom of the page
`Short_Press-Threshold` | | decimal number | Defines the lower bound of short button press event in seconds, if the duration of the button press was shorter no update will be send. Usful to ignor false detection of button press due to electrical interferences. (default is 0)
`Long_Press-Dest` | | | Location/openHAB string/datetime item to publish an update after a long button press happend, requires `Long_Press-Threshold`, `Short_Press-Dest`
`Long_Press-Threshold` | | decimal number | Defines the lower bound of long button press event in seconds, if the duration of the button press was shorter a short button event will be triggered. Can be determinded via the sensor-reporter log when set on info level.
`Btn_Pressed_State` | | LOW or HIGH | Sets the expected input level for short and long button press events. Set it to `LOW` if the input pin is connected to ground while the button is pressed (default is determined via PUD config value: `PUD = UP` will assume `Btn_Pressed_State = LOW`)

### Global parameters
Can only be set for all GPIO devices (sensors and actuators).
Global parametes are set in the `[DEFAULT]` section.
See example at the bottom of the page.

Parameter | Required | Restrictions | Purpose
-|-|-|-
`PinNumbering` | | BCM or BOARD | Select which numbering to use for the IO Pin's. Use BCM when GPIO numbering is desired. BOARD refers to the pin numbers on the P1 header of the Raspberry Pi board. (default BCM)

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
A recieved command will be sent back on all configured connections to the configured `CommandSrc`, to keep them up to date.

### Dependencies

The user running sensor_reporter must have permission to access the GPIO pins.
To grant the `sensorReporter` user GPIO permissions add the user to the group `gpio`:  `sudo adduser sensorReporter gpio`

Depends on RPi.GPIO.

```
$ sudo pip3 install RPI.GPIO
```

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `gpio.rpi_gpio.RpiGpioActuator` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`CommandSrc` | X | | Destination/openHAB switch item where commands are received, expects ON/OFF. If Toggle is set all messages trigger a toggle.
`ToggleCommandSrc` | | | Destination/openHAB string item where toggle commands are recieverd. This is intended to be used for direct connections to a sensor via the Short_Press-Dest/Long_Press-Dest parameter. Expects the string TOGGLE, when recieved the output of the actuator will get toggled e.g. from LOW to HIGH until further commands. If the parameter `SimulateButton` is configured to TRUE this parameter is ignored. If not configured no ToggleCommandSrc will be registerd.
`ToggleDebounce` | | decimal number | The interval in seconds during which repeated toggle commands are ignored (Default 0.15 seconds)
`Pin` | X | IO Pin | Pin to use as actuator output, using the pin numbering defined in `PinNumbering` (see below).
`InitialState` | | ON or OFF | Optional, when set to ON the pin's state is initialized to HIGH.
`SimulateButton` | | Boolean | When `True` simulates a button press by setting the pin to HIGH for half a second and then back to LOW. In case of `InitalState` ON it will toggle the other way around.
`InvertOut` | | Boolean | Inverts the output when set to `True`. When inverted sending `ON` to the actuator will set the output to LOW, `OFF` will set the output to HIGH.

### Global parameters
Can only be set for all GPIO devices (sensors and actuators). Global parametes are set in the `[DEFAULT]` section
Parameter | Required | Restrictions | Purpose
-|-|-|-
`PinNumbering` | | BCM or BOARD | Select which numbering to use for the IO Pin's. Use BCM when GPIO numbering is desired. BOARD refers to the pin numbers on the P1 header of the Raspberry Pi board. (default BCM)

### Example Config

```ini
[DEFAULT]
PinNumbering=BOARD

[Logging]
Syslog = YES
Level = INFO

[Connection1]
Class = openhab_rest.rest_conn.OpenhabREST
Name = openHAB
URL = http://localhost:8080
RefreshItem = Test_Refresh

[Actuator0]
Class = gpio.rpi_gpio.RpiGpioActuator
Connection = openHAB
CommandSrc = GarageDoorCmd
Pin = 35
InitialState = ON
Toggle = True
Level = DEBUG
```

### Example Config #2
Useing a local connection to toggle an actuator, which is also connected to openHAB. 
The actuator shows alway the correct status in openHAB, even it is toggled locally.

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection_openHAB]
Class = openhab_rest.rest_conn.OpenhabREST
Name = openHAB
URL = http://localhost:8080
RefreshItem = Test_Refresh

[Connection0]
Class = local.local_conn.LocalConnection
Name = local

[Sensor1]
Class = gpio.rpi_gpio.RpiGpioSensor
Connection = local
Pin = 17
PUD = UP
EventDetection = BOTH
Destination = some_lightswitch
Short_Press-Dest = toggle_garage_light
Btn_Pressed_State = HIGH

[Actuator0]
Class = gpio.rpi_gpio.RpiGpioActuator
Connection = local,openHAB
CommandSrc = garage_light
ToggleCommandSrc = toggle_garage_light
Pin = 19
```

Circuit diagram

![example2](circuit_diagram/example2_circuit.png)