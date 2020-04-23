#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smltextmqttprocessor.py - Process SML from libsml-sml_server and send it to MQTT.

Processor for Smart Message Language (SML) messages from
the output of libsml-sml_server binary, and sending of
processed SML values to MQTT.

Run it with:
`./sml_server_arm /dev/ttyAMA0 | python smltextmqttprocessor.py -v config.local.ini -`

Usage:
  smltextmqttprocessor.py [options] <config-file.ini> <input>
  smltextmqttprocessor.py -h | --help
  smltextmqttprocessor.py --version

Arguments:
  config-file.ini Configuration file [default: config.local.ini]
  input           Input file or '-' for STDIN.

Options:
  --no-mqtt       Do not send over MQTT (mainly for testing).
  -q --quiet      Be quiet, show only errors.
  -v --verbose    Verbose output.
  --debug         Debug mode (logging.DEBUG).
  -h --help       Show this screen.
  --version       Show version.
"""
##
## LICENSE:
##
## Copyright (C) 2020 Alexander Streicher
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
import os
import sys
import time
import logging
import configparser
import statistics

from codecs import open
from docopt import docopt
import numpy as np
## https://pypi.org/project/paho-mqtt/#usage-and-api
import paho.mqtt.client as mqtt
## PySML, https://pypi.org/project/pysml/
# noinspection PyUnresolvedReferences,PyPackageRequirements
import sml

__version__ = "1.2"
__date__ = "2020-04-21"
__updated__ = "2020-04-23"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"

SML_POWER_ACTUAL = '1-0:16.7.0*255'
SML_POWER_TOTAL = '1-0:1.8.0*255'
SML_ACT_SENSOR_TIME = 'act_sensor_time'

DEBUG = 0
TESTRUN = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)


class DummyMqtt:
    def connect(self, host, port=1883, keepalive=60, bind_address=""):
        logging.info("DummyMqtt: %s:%d", host, port)

    def publish(self, topic, payload=None, qos=0, retain=False):
        logging.info("DummyMqtt: %s: %s", topic, payload)

def on_connect(client, userdata, flags, rc):
    logging.info("MQTT connected: %s (%d)", mqtt.error_string(rc), rc)


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning("MQTT unexpected disconnection! %s (%d)", mqtt.error_string(rc), rc)
        rc = client.reconnect()
        if rc != 0:
            logging.error("MQTT reconnect failed! %s (%d)", mqtt.error_string(rc), rc)


def main():
    arguments = docopt(__doc__, version="SmlTextMqttProcessor %s (%s)" % (__version__, __updated__))
    # print(arguments)

    arg_configfile = arguments['<config-file.ini>']
    arg_input = arguments['<input>']
    arg_verbose = arguments['--verbose']
    arg_debug = arguments['--debug']
    arg_quiet = arguments['--quiet']
    arg_no_mqtt = arguments['--no-mqtt']

    ## setup logging
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(name)-10s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    if DEBUG or arg_debug:
        logging.getLogger('').setLevel(logging.DEBUG)
        logging.debug('---- ENABLING DEBUG OUTPUT!!! -------')
        logging.debug(arguments)
    elif arg_verbose:
        logging.getLogger('').setLevel(logging.INFO)
    elif arg_quiet:
        logging.getLogger('').setLevel(logging.ERROR)

    ## Configuration
    if not os.path.isabs(arg_configfile):
        arg_configfile = os.path.join(__script_dir, arg_configfile)
    arg_configfile = os.path.abspath(arg_configfile)
    logging.info("Config file: %s", arg_configfile)
    config = configparser.ConfigParser()
    config.read(arg_configfile)

    ## MQTT
    if arg_no_mqtt:
        client = DummyMqtt()
    else:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        if config.has_option('Mqtt', 'username'):
            client.username_pw_set(config.get('Mqtt', 'username'), password=config.get('Mqtt', 'password'))
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        client.connect(config.get('Mqtt', 'host'), port=config.getint('Mqtt', 'port', fallback=1883))

    ## rolling window period
    block_size = config.getint(configparser.DEFAULTSECT, 'block_size')
    logging.info('Block size: %d', block_size)
    client.publish("tele/smartmeter/block/size", block_size)

    if arg_input == '-':
        istream = sys.stdin
        istream_size = -1
    else:
        istream = open(arg_input)
        istream_size = os.stat(arg_input).st_size

    logging.info(istream)

    a_total = []
    a_actual = []
    a_times = []
    while True:
        if len(a_total) > block_size:
            ## MQTT publishing
            logging.info("MQTT sending ...")
            client.publish("tele/smartmeter/time/first", a_times[0])
            client.publish("tele/smartmeter/time/last", a_times[-1])
            client.publish("tele/smartmeter/power/total/value", a_total[-1])
            client.publish("tele/smartmeter/power/actual/first", a_actual[0])
            client.publish("tele/smartmeter/power/actual/last", a_actual[-1])
            client.publish("tele/smartmeter/power/actual/median", statistics.median(a_actual))
            client.publish("tele/smartmeter/power/actual/mean", round(statistics.mean(a_actual)))
            client.publish("tele/smartmeter/power/actual/min", min(a_actual))
            client.publish("tele/smartmeter/power/actual/max", max(a_actual))
            client.publish("tele/smartmeter/power/actual/percentile20", np.percentile(a_actual, 20))
            client.publish("tele/smartmeter/power/actual/percentile80", np.percentile(a_actual, 80))

            ## reset
            a_total = []
            a_actual = []
            a_times = []

        ## 1-0:96.50.1*1#ISK#
        ## 1-0:96.1.0*255#0a 01 49 53 4b 01 23 45 67 89 #
        ## 1-0:1.8.0*255#837566.4#Wh
        ## 1-0:16.7.0*255#273#W
        line = istream.readline().strip()
        if not line or not line.startswith('1-0:96.50.1*1#') or line.startswith('#'):
            time.sleep(0.3)
            continue

        istream.readline()  ## do not use
        line_power_total = istream.readline().strip()
        line_power_actual = istream.readline().strip()

        ## heuristic to check if next line is act_sensor_time
        ## (special version of sml_server EXE)
        cur_pos = istream.tell()
        line_act_sensor_time = istream.readline().strip()
        if line_act_sensor_time.startswith(SML_ACT_SENSOR_TIME):
            ## found a matching line, take the value from this line for the act_sensor_time
            _, value, _ = line_act_sensor_time.split('#', 2)
            value = int(value)
            logging.debug("act_time_heuristic: found! %d", value)
            a_times.append(value)
        else:
            logging.debug("act_time_heuristic: nothing found, using time.time()")
            ## no act_sensor_time field found, rollback in stream
            istream.seek(cur_pos)
            ## use our current timestamp because none from SML
            a_times.append(int(time.time()))

        if line_power_total.startswith(SML_POWER_TOTAL):
            ## "1-0:1.8.0*255#837566.4#Wh"
            _, value, unit = line_power_total.split('#', 2)
            value = float(value)
            a_total.append(value)

        if line_power_actual.startswith(SML_POWER_ACTUAL):
            ## "1-0:16.7.0*255#273#W"
            _, value, unit = line_power_actual.split('#', 2)
            value = float(value)
            a_actual.append(value)

        ## if this is a file stream then break when EOF is reached
        if istream_size > 0 and istream.tell() >= istream_size:
            break

    return 0


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("--debug")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = __file__ + '.profile.bin'
        cProfile.run('main()', profile_filename)
        with open("%s.txt" % profile_filename, "wb") as statsfp:
            p = pstats.Stats(profile_filename, stream=statsfp)
            stats = p.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())
