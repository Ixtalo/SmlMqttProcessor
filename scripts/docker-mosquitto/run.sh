#!/bin/sh
set -x
# https://hub.docker.com/_/eclipse-mosquitto
podman run --rm -it --name mqttserver -p 1883:1883 -p 9001:9001 -u 1000:1000 \
  -v "$PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" \
  -v "$PWD/users.txt:/mosquitto/config/users.txt:ro" \
  docker.io/eclipse-mosquitto:2
#sleep 3
#docker logs --timestamps --follow mqttserver
