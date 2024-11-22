# Scripts

Some useful scripts for setup and development.

- docker-mosquitto: Docker MQTT for local testing.
- example-data-sender: simple Python script to simulate libsml's sml_server textual, decoded output.
- systemd: for automatic starts, `smltextmqttprocessor.service`


## Local Test Setup

1. run `docker-mosquitto/run.sh` to start the MQTT server
2. run `docker-mosquitto/subscribe.sh` to listen
3. `DEBUG=1 poetry run python main.py --config config.dev.ini tests/testdata/ISKRA_MT175_eHZ.txt`
4. stop it (CTRL+C)
5. look at the output in the listen-process, it should read:
   `tele/smartmeter {"time": {"value": 128972260, "first": 128972252, "last": 128972260}, "total": {"value": 22462414.0, "first": 22462413.6, "last": 22462414.0}, "total_tariff1": {"value": 22462414.0, "first": 22462413.6, "last": 22462414.0, "median": 22462413.8, "mean": 22462413.8, "min": 22462413.6, "max": 22462414.0, "stdev": 0.2}, "total_tariff2": {"value": 0.0, "first": 0.0, "last": 0.0, "median": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0, "stdev": 0.0}, "actual": {"value": 168, "first": 168, "last": 168, "median": 168, "mean": 169.6, "min": 168, "max": 173, "stdev": 2.3}, "actual_l1": {"value": 117, "first": 117, "last": 117, "median": 117, "mean": 117.6, "min": 117, "max": 119, "stdev": 0.9}, "actual_l2": {"value": 22, "first": 22, "last": 22, "median": 22, "mean": 21.8, "min": 21, "max": 22, "stdev": 0.4}, "actual_l3": {"value": 28, "first": 29, "last": 28, "median": 29, "mean": 29.4, "min": 28, "max": 32, "stdev": 1.5}}`

What happens:
1. SmlMqttProcessor read the persisted smart meter data from ISKRA_MT175_eHZ.txt.
2. It parsed the messages and sent an aggregated MQTT message.
