#!/bin/sh
set -x
docker run --rm -d -it -p 1883:1883 -p 9001:9001 -u 1000:1000 -v "$PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" -v "$PWD/users.txt:/mosquitto/config/users.txt:ro" eclipse-mosquitto
