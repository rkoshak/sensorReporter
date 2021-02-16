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
`Connection` | X | Comma separated list of Connections | Where the messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number in seconds | How often to publish the uptime, must be >= 60.
`Import_Dst` | X | | Destination to publish the imported energy amount to (OBIS 1.8.0).
`Export_Dst` | X | | Destination to publish the exported energy amount to (OBIS 2.8.0).

## Example Config

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

[SensorPafal]
Class = energymeter.read_meter_values.Pafal20ec3gr
Connection = openHAB
Poll = 60
Import_Dst = Energy_ImportedTotalkWh
Export_Dst = Energy_ExportedTotalkWh
Level = INFO
```

# Energy Meter Test script

Using the script `test_pafal.py` one can check for the connection to the energy meter.
```
python3 energymeter/test_pafal.py --port /dev/ttyUSB0
```