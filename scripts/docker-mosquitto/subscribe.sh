#!/bin/sh
#mosquitto_sub -h localhost -u foo -P bar -t "#" -t "\$SYS/#"
mosquitto_sub -v -h localhost -u foo -P bar -t "#"
