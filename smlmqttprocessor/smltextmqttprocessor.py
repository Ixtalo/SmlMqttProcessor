#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smltextmqttprocessor.py - Process SML from libsml-sml_server and send it to MQTT.

Processor for Smart Message Language (SML) messages from
the output of libsml-sml_server binary, and sending of
processed SML values to MQTT.

Run it with:
`./sml_server_arm /dev/ttyAMA0 | python smltextmqttprocessor.py -v config.local.ini -`

Usage:
  smltextmqttprocessor.py [options] [--config config.ini] <input>
  smltextmqttprocessor.py -h | --help
  smltextmqttprocessor.py --version

Arguments:
  input           SML input, file or '-' for STDIN (e.g., from libsml-binary).

Options:
  --config <file> Configuration file [default: config.local.ini]
  --no-mqtt       Do not send over MQTT (mainly for testing).
  -q --quiet      Be quiet, show only errors.
  -t --timeout=N  Timeout in seconds [default: 0].
  -v --verbose    Verbose output (INFO level).
  -w --window=N   Window size.
  -h --help       Show this screen.
  --version       Show version.
"""
#
# LICENSE:
#
# Copyright (C) 2020-2024 Ixtalo, ixtalo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import configparser
import logging
import os
import sys
import time
# pylint: disable=redefined-builtin
from codecs import open
from pathlib import Path
from pprint import pprint

# https://pypi.org/project/paho-mqtt/#usage-and-api
# PySML, https://pypi.org/project/pysml/
# noinspection PyUnresolvedReferences,PyPackageRequirements
# pylint: disable=import-error,unused-import
import sml  # noqa: F401
from docopt import docopt

from smlmqttprocessor.mqtt import MyMqtt
from smlmqttprocessor.utils.message_utils import convert_messages2records
from smlmqttprocessor.utils.mylogging import setup_logging

__version__ = "1.17.0"
__date__ = "2020-04-21"
__updated__ = "2024-11-20"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"

########################################################################
# Configure the following to suit your actual smart meter configuration
#

# SML OBIS fields
# dictionary: MQTT-topic --> OBIS-code
# for OBIS codes see e.g. https://wiki.volkszaehler.org/software/obis
SML_FIELDS = {
    'total': '1-0:1.8.0*255',  # Zählerstand Bezug
    'total_tariff1': '1-0:1.8.1*255',  # Zählerstand Bezug Tarif 1
    'total_tariff2': '1-0:1.8.2*255',  # Zählerstand Bezug Tarif 2
    'total_tariff3': '1-0:1.8.3*255',  # Zählerstand Bezug Tarif 3
    'total_tariff4': '1-0:1.8.4*255',  # Zählerstand Bezug Tarif 4

    'total_export': '1-0:2.8.0*255',  # Zählerstand Lieferung
    'total_export_tariff1': '1-0:2.8.1*255',  # Zählerstand Lieferung Tarif 1
    'total_export_tariff2': '1-0:2.8.2*255',  # Zählerstand Lieferung Tarif 2
    'total_export_tariff3': '1-0:2.8.3*255',  # Zählerstand Lieferung Tarif 3
    'total_export_tariff4': '1-0:2.8.4*255',  # Zählerstand Lieferung Tarif 4

    'actual': '1-0:16.7.0*255',  # Leistung (Momentan)
    'actual_l1': '1-0:36.7.0*255',  # Leistung L1 (Momentan)
    'actual_l2': '1-0:56.7.0*255',  # Leistung L2 (Momentan)
    'actual_l3': '1-0:76.7.0*255',  # Leistung L3 (Momentan)
    'actual_170': '1-0:1.7.0*255',  # Wirkleistung

    'time': 'act_sensor_time'
}

# SML headers as list/tuple for header-detection heuristic
# (OBIS code for manufacturer identification)
SML_HEADERS = ('1-0:96.50.1*1#', '129-129:199.130.3*255#')

##
########################################################################

# Python 3.5 is the version of my Raspian 8 (Jessie) which has Python 3.5
# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

DEBUG = bool(os.getenv("DEBUG", "").lower() in ("1", "true", "yes"))
__script_dir = Path(__file__).parent.parent  # project root


def check_stream_packet_begin(line):
    """Check if the given string line contains an SML header indicating a new message block.

    :param line: line (string)
    :return: True if begin of new message
    """
    for header in SML_HEADERS:
        if line.startswith(header):
            # yes, this is the starting line
            return True
    return False


def parse_line(line):
    """Parse a single SML line.

    :param line: SML message line
    :return: (fieldname, value) tuple according to SML_FIELDS
    """
    if not line:
        return None
    for name, pattern in SML_FIELDS.items():
        if line.startswith(pattern):
            # found a matching line, take the value from this line
            _, value, _ = line.split('#', 2)  # (OBIS code, value, unit)

            # detect int/float values
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            return name, value
    return None


def processing_loop(input_stream, window_size, callback, timeout=0, deltas=None):
    """Run the main processing loop on the input stream.

    If size of rolling window is reached then call handler function mqtt_or_println.
    A timeout can be specified to stop after n seconds of no data (e.g. for STDIN).

    :param input_stream: input stream
    :param window_size: rolling window size, size of aggregation window
    :param callback: reference to messages handling callback function
    :param timeout: timeout in seconds, 0 for no timeout
    :param deltas: dictionary fieldname->float with difference (delta) thresholds
    :return: Nothing
    """
    message = {}
    messages = []
    n_nodata = 0
    while True:
        line = input_stream.readline().strip()
        if not line:
            n_nodata += 1
            if timeout and n_nodata >= timeout:
                logging.warning("#%d times no data observed, timeout hit, aborting!",
                                n_nodata)
                messages.append(message)
                callback(messages)
                break
            logging.debug("no data observed...waiting 1 second...")
            time.sleep(1)

        if isinstance(line, bytes):
            # make sure line is a string, not bytes
            line = line.decode()

        # check if this is a header line, i.e. beginning of new message block
        if check_stream_packet_begin(line):
            if message:  # initial loops have empty message...
                # record current message
                messages.append(message)
                logging.debug("message: %s", message)

            # new header line, new message
            message = {}

            n_msgs = len(messages)
            if n_msgs >= window_size:
                logging.info("window (%d) filled, handling #%d messages...",
                             window_size, n_msgs)
                callback(messages)  # handle all messages
                messages = []  # start a new collection
            elif deltas and n_msgs >= 2:
                # dynamic checking of all fields in message according to declared delta-thresholds
                for field_name, delta_value in deltas.items():
                    if field_name not in messages[-2] or field_name not in messages[-1]:
                        logging.warning("No such field with name '%s' in message!",
                                        field_name)
                        continue

                    # compute delta/difference of the latest 2 messages
                    prev = messages[-2][field_name]
                    curr = messages[-1][field_name]
                    delta = abs(prev - curr)
                    logging.debug("delta: %.1f, prev: %.1f, curr: %.1f, field: %s",
                                  delta, prev, curr, field_name)

                    # determine if there's a change
                    # if 0 <= delta_value <= 1 then use relative (percentage), else absolute
                    is_change = delta >= delta_value * curr if delta_value < 1 \
                        else delta >= delta_value

                    if is_change:
                        logging.info("field '%s', delta: %d, above threshold (%d), handling...",
                                     field_name, delta, delta_value)
                        callback(messages)  # handle all messages
                        messages = []  # start a new collection
                        # stop delta stuff, i.e., only 1 handling when delta event happens
                        break

            # current header-line is done, proceed to next line
            continue

        # try to parse the next incoming line (from sml_server_time)
        try:
            # parse libSML text line
            result = parse_line(line)
            if result:
                field_name, value = result
                # add to message
                # NOTE: duplicate lines of same type would overwrite old values
                # until a new header line occurs (i.e., next SML message block)
                message[field_name] = value
        except ValueError as ex:
            logging.error("Invalid message '%s': %s", line, ex)

        time.sleep(0.01)


def main():
    """Run the main program entry point.

    :return: exit/return code
    """
    version_string = "SmlTextMqttProcessor %s (%s)" % (__version__, __updated__)
    arguments = docopt(__doc__, version=version_string)
    arg_input = arguments['<input>']
    arg_configfile = arguments['--config']
    arg_verbose = arguments['--verbose']
    arg_quiet = arguments['--quiet']
    arg_no_mqtt = arguments['--no-mqtt']
    arg_timeout = int(arguments['--timeout'])
    arg_window_size = arguments['--window']

    log_level = logging.WARNING
    if arg_verbose:
        log_level = logging.INFO
    if arg_quiet:
        log_level = logging.ERROR
    if DEBUG:
        log_level = logging.DEBUG
    setup_logging(level=log_level)

    logging.info(version_string)
    logging.debug("arguments: %s", arguments)

    # Configuration
    config = configparser.ConfigParser()
    if arg_configfile:
        configfile = Path(arg_configfile)
        if not configfile.is_absolute():
            # if not an absolute path then make it one based on this very script's folder
            configfile = __script_dir.joinpath(configfile)
        logging.info("Config file: %s", configfile.resolve())
        if not (configfile.is_file() and os.access(configfile, os.R_OK)):
            raise RuntimeError('Config file is not a file or not accessible! Aborting.')
        config.read(configfile)  # does not fail by itself when configfile is not accessible
        # combine all config dicts, and mask password
        logging.info("Configuration: %s", {**config.defaults(), **dict(config.items())})

    # set the threshold deltas from config
    deltas = {}
    if config.has_section("DeltaThresholds"):
        for name, value in config.items("DeltaThresholds"):
            if name in config.defaults():
                # do not include options of the DEFAULT section
                continue
            value = config.getfloat("DeltaThresholds", name)
            if value > 0:
                deltas[name] = value
            else:
                logging.warning("Invalid value for DeltaThresholds '%s'!", name)
        logging.info("DeltaThresholds: %s", deltas)

    # rolling window period
    window_size = config.getint(configparser.DEFAULTSECT, 'block_size', fallback=30)
    if arg_window_size:
        # overwrite by CLI
        window_size = int(arg_window_size)
    logging.info('Aggregation/rolling window size: %d', window_size)

    # input stream
    # pylint: disable=consider-using-with
    istream = sys.stdin if arg_input == "-" else open(arg_input)
    logging.info("Input stream: %s", istream)

    # MQTT
    mymqtt = MyMqtt(config)

    # this callback will be called when a message has arrived and has been parsed
    def mqtt_or_println(messages):
        records = convert_messages2records(messages)
        if arg_no_mqtt:
            mqttdata = MyMqtt.construct_mqttdata(records)
            print('mqttdata:')
            pprint(mqttdata)
        else:
            mymqtt.send(records)

    # main processing loop on input stream
    # IF (size of rolling window is reached) THEN call handler function mqtt_or_println
    processing_loop(istream, window_size, mqtt_or_println, deltas=deltas, timeout=arg_timeout)

    return 0


if __name__ == '__main__':
    sys.exit(main())
