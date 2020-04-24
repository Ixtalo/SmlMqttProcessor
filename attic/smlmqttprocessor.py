#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smlmqttprocessor.py - Process SML from serial port and send it to MQTT.

Processor for Smart Message Language (SML) packets and
sending of SML values to MQTT.

Usage:
  smlmqttprocessor.py [options] <config-file.ini>
  smlmqttprocessor.py -h | --help
  smlmqttprocessor.py --version

Arguments:
  <config-file.ini> Configuration file [default: config.local.ini]

Options:
  -q --quiet      Be quiet, show only errors.
  -v --verbose    Verbose output.
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
import logging
import configparser
import statistics

from codecs import open
from docopt import docopt
## PySerial, https://pypi.org/project/pyserial/
import serial
## https://pypi.org/project/paho-mqtt/#usage-and-api
import paho.mqtt.client as mqtt
## PySML, https://pypi.org/project/pysml/
import sml

__version__ = "1.0"
__date__ = "2020-04-21"
__updated__ = "2020-04-21"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"

SML_START = b'\x1b\x1b\x1b\x1b\x01\x01\x01\x01'
SML_END = b'\x1b\x1b\x1b\x1b\x1a'
SML_POWER_ACTUAL = '1-0:16.7.0*255'
SML_POWER_TOTAL = '1-0:1.8.0*255'
SML_SENSOR_TIME = 'actSensorTime'

DEBUG = 0
TESTRUN = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)


def on_connect(client, userdata, flags, rc):
    logging.info("MQTT connected: %s (%d)", mqtt.error_string(rc), rc)


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning("Unexpected disconnection! %s (%d)", mqtt.error_string(rc), rc)
        client.reconnect()


def main():
    arguments = docopt(__doc__, version="SmlMqttProcessor %s (%s)" % (__version__, __updated__))
    if DEBUG: print(arguments)

    arg_configfile = arguments['<config-file.ini>']
    arg_verbose = arguments['--verbose']
    arg_quiet = arguments['--quiet']

    ## setup logging
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(name)-10s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    if DEBUG:
        logging.getLogger('').setLevel(logging.DEBUG)
        logging.debug('---- ENABLING DEBUG OUTPUT!!! -------')
        logging.debug(arguments)
    elif arg_verbose:
        logging.getLogger('').setLevel(logging.INFO)
    elif arg_quiet:
        logging.getLogger('').setLevel(logging.ERROR)

    ## Configuration
    config = configparser.ConfigParser()
    config.read(arg_configfile)

    ## PySerial
    ser = serial.Serial(config.get('Serial', 'port'),
                        baudrate=config.get('Serial', 'baudrate', fallback=9600),
                        timeout=config.getfloat('Serial', 'timeout', fallback=1.0)
                        )
    logging.info("Serial port: %s", str(ser))

    ## MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    if config.has_option('Mqtt', 'username'):
        client.username_pw_set(config.get('Mqtt', 'username'), password=config.get('Mqtt', 'password'))
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    client.connect(config.get('Mqtt', 'host'), port=config.getint('Mqtt', 'port', fallback=1883))

    ## SML parser
    s = sml.SmlBase()
    logging.getLogger('sml').setLevel(logging.WARNING)  ## lot's of debugging output!

    ## Rolling window period
    block_size = config.getint(configparser.DEFAULTSECT, 'block_size')
    logging.info('Block size: %d', block_size)
    client.publish("tele/smartmeter/block/size", block_size)

    a_total = []
    a_actual = []
    a_times = []
    n_errors = 0
    while True:
        if len(a_total) > block_size:
            logging.warning('%d errors since last block finish', n_errors)

            ## MQTT publishing
            client.publish("tele/smartmeter/block/errors", n_errors)
            client.publish("tele/smartmeter/sensor_time/value", a_times[-1])
            client.publish("tele/smartmeter/power/total/value", a_total[-1])
            client.publish("tele/smartmeter/power/actual/mean", round(statistics.mean(a_actual)))

            ## reset
            a_total = []
            a_actual = []
            a_times = []
            n_errors = 0

        ## read from input stream/serial port
        ## must be >= 216 bytes (typical size of 1 SML packet for ISKRA smartmeter)
        buffer = ser.read(400)
        logging.debug("%d bytes read", len(buffer))

        ## check if data contains SML packet
        if not (SML_START in buffer and SML_END in buffer):
            logging.warning("No SML packet indicators found!")
            continue

        ## parse SML
        frame = None
        try:
            ## extract SML packet bytes
            p0, p1 = buffer.index(SML_START), buffer.index(SML_END)
            packet = buffer[p0:p0 + p1 + len(SML_END) + 3]
            ## parse SML
            ## result if ok: nf=(nbytes, frame)
            ## result if no data: nf=0
            nf = s.parse_frame(packet)
            if len(nf) == 2:
                frame = nf[1]
        except sml.SmlParserError as ex:
            logging.error(ex)
        except ValueError as ex:
            logging.exception(ex)
        except Exception as ex:
            logging.exception(ex)

        if not frame:
            n_errors += 1
            continue

        ## find relevant messageBody in valList
        ## and convert its objects to a simple dictionary
        data = {}
        for entry in frame:
            if 'messageBody' in entry and SML_SENSOR_TIME in entry['messageBody']:
                mb = entry['messageBody']
                data[SML_SENSOR_TIME] = mb[SML_SENSOR_TIME][1]
                for val in mb['valList']:
                    if 'unit' in val:
                        obj_name = val['objName']
                        value = val['value']
                        data[obj_name] = value
                break

        if DEBUG: logging.debug(data)

        ## record values
        a_total.append(data[SML_POWER_TOTAL])
        a_actual.append(data[SML_POWER_ACTUAL])
        a_times.append(data[SML_SENSOR_TIME])

    return 0


if __name__ == "__main__":
    if DEBUG:
        # sys.argv.append("-h")
        pass
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
