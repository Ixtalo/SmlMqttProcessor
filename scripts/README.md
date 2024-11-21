# Scripts

Some useful scripts for setup and development.

- docker-mosquitto: Docker MQTT for local testing.
- example-data-sender: simple Python script to simulate libsml's sml_server textual, decoded output.
- systemd: for automatic starts, `smltextmqttprocessor.service`


## Local Test Setup

1. run `docker-mosquitto/run.sh` to start the MQTT server
2. `DEBUG=1 poetry run python main.py --config config.dev.ini tests/testdata/ISKRA_MT175_eHZ.txt`
