#!/bin/sh
CMD="mosquitto_pub -h localhost -u foo -P bar"
$CMD -t tele/smartmeter/time/first -m 42716005
$CMD -t tele/smartmeter/time/last -m 42716068
$CMD -t tele/smartmeter/power/total/value -m 4050963.7
$CMD -t tele/smartmeter/power/actual/first -m 147.0
$CMD -t tele/smartmeter/power/actual/last -m 309.0
$CMD -t tele/smartmeter/power/actual/median -m 149.0
$CMD -t tele/smartmeter/power/actual/mean -m 193
$CMD -t tele/smartmeter/power/actual/min -m 144.0
$CMD -t tele/smartmeter/power/actual/max -m 310.0
