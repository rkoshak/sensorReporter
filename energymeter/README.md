# pafal_reader.pafal_reader.PafalReader

This sensor allows reading out a Pafal 5EC3gr00006 device using a strongly tailored subset of the iec62056 protocol.
It can be used to monitor the by the "smart meter" recoreded exported and imported energy.

## Dependencies

Uses [serial](https://pypi.org/project/pyserial/) to communicate with via the connected serial device

Requires that sensor_reporter has read/write access to the device file used for communication.

A serial connection to the metering device is required (e.g. via a cp210x UART-USB device like
http://wiki.volkszaehler.org/hardware/controllers/ir-schreib-lesekopf-usb-ausgang)

## Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `energymeter.read_meter_values.Pafal20ec3gr` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. This sensor has 2 outputs, see below. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number in seconds | How often to publish the uptime, must be >= 60.
`SerialDevice` | X | The serial device file to read from

### Outputs
The Pafal20ec3gr has 2 outputs which can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).

Output | Purpose
-|-
`Import` | Where to publish the imported energy amount to (OBIS 1.8.0).
`Export` | Where to publish the exported energy amount to (OBIS 2.8.0).

## Example Config

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

SensorPafal:
    Class: energymeter.read_meter_values.Pafal20ec3gr
    Connections:
        openHAB:
            Import:
                Item: Energy_ImportedTotalkWh
            Export:
                Item: Energy_ExportedTotalkWh
    Poll: 60
    SerialDevice: /dev/ttyUSB0
```

# Energy Meter Test script

Using the script `test_pafal.py` one can check for the connection to the energy meter.
```
python3 energymeter/test_pafal.py --port /dev/ttyUSB0
```