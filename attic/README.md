# Attic

## `smlmqttprocessor.py`

*Process SML from serial port and send it to MQTT.
Processor for Smart Message Language (SML) packets and
sending of SML values to MQTT.*

This is a first prototype which directly works on the serial port byte stream from the sensor.

Although that worked, it could be hard to maintain, e.g., if some SML values or features have not been considered, or if (unlikely) SML changes or some SML definitions are changed.

Probably a better solution approach is to use a well-established SML library such as **libsml** and process its SML parsing results.
