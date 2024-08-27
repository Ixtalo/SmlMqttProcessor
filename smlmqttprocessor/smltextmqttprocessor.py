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
  -v --verbose    Verbose output.
  --debug         Debug mode (logging.DEBUG).
  -h --help       Show this screen.
  --version       Show version.
"""
#
# LICENSE:
#
# Copyright (C) 2020-2023 Alexander Streicher
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
import json
import logging
import os
import statistics
import sys
import time
# pylint: disable=redefined-builtin
from codecs import open
from enum import IntEnum
from pprint import pprint

# https://pypi.org/project/paho-mqtt/#usage-and-api
import paho.mqtt.client as mqtt
# PySML, https://pypi.org/project/pysml/
# noinspection PyUnresolvedReferences,PyPackageRequirements
# pylint: disable=import-error,unused-import
import sml  # noqa: F401
from docopt import docopt

__version__ = "1.15.0"
__date__ = "2020-04-21"
__updated__ = "2024-08-27"
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
    'total': '1-0:1.8.0*255',          # Zählerstand Bezug
    'total_tariff1': '1-0:1.8.1*255',  # Zählerstand Bezug Tarif 1
    'total_tariff2': '1-0:1.8.2*255',  # Zählerstand Bezug Tarif 2
    'total_tariff3': '1-0:1.8.3*255',  # Zählerstand Bezug Tarif 3
    'total_tariff4': '1-0:1.8.4*255',  # Zählerstand Bezug Tarif 4

    'total_export': '1-0:2.8.0*255',          # Zählerstand Lieferung
    'total_export_tariff1': '1-0:2.8.1*255',  # Zählerstand Lieferung Tarif 1
    'total_export_tariff2': '1-0:2.8.2*255',  # Zählerstand Lieferung Tarif 2
    'total_export_tariff3': '1-0:2.8.3*255',  # Zählerstand Lieferung Tarif 3
    'total_export_tariff4': '1-0:2.8.4*255',  # Zählerstand Lieferung Tarif 4

    'actual': '1-0:16.7.0*255',     # Leistung (Momentan)
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

# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

DEBUG = 0
PROFILE = 0
__SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# check for Python3
if sys.version_info < (3, 5):
    sys.stderr.write("Minimum required version is Python 3.5!\n")
    sys.exit(1)


class ExitCodes(IntEnum):
    """Exit/return codes."""

    OK = 0
    CONFIG_FAIL = 3


class MyMqtt:
    """MQTT publishing."""

    def __init__(self, config):
        """MQTT publishing.

        :param config: ConfigParser object, e.g. from config.ini
        """
        self.client = None
        self.config = config
        self.connected = False

    def connect(self):
        """Connect to MQTT server and handle disconnection/reconnection events."""
        # noinspection PyUnusedLocal,PyShadowingNames
        # pylint: disable=invalid-name,unused-argument
        def on_connect(client, userdata, flags, rc):
            logging.info("MQTT connect: %s (%d)", mqtt.connack_string(rc), rc)
            self.connected = True

        # noinspection PyUnusedLocal,PyShadowingNames
        # pylint: disable=invalid-name,unused-argument
        def on_disconnect(client, userdata, rc):
            self.connected = False
            if rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info('MQTT disconnect: successful.')
            else:
                logging.warning("MQTT unexpected disconnection! %s (%d)", mqtt.error_string(rc), rc)

        ##
        # NOTE!
        # Creating a new Client() seems to be necessary.
        # Just using reconnect() or connect() again did not work.
        ##
        client = mqtt.Client("SmlTextMqttProcessor")

        # store as class variable to be accessible later
        self.client = client

        if self.config.has_option('Mqtt', 'username'):
            client.username_pw_set(self.config.get('Mqtt', 'username'),
                                   password=self.config.get('Mqtt', 'password'))
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect

        # try-to-connect loop
        client.connected = False
        wait_time = 1
        host = self.config.get('Mqtt', 'host', fallback='localhost')
        port = self.config.getint('Mqtt', 'port', fallback=1883)
        while not self.connected:
            try:
                client.connect(host, port=port)
                # loop_start() is necessary for on_* to work
                # (asynchronous handling starts)
                client.loop_start()
                break
            except Exception as ex:
                logging.error("MQTT connect exception! %s: %s", type(ex).__name__, ex)
                # increase waiting time
                wait_time *= 2
                # limit waiting time to max. 180 sec = 3 min
                wait_effective = min(wait_time, 180)
                logging.debug("waiting %d seconds before reconnect attempt...", wait_effective)
                time.sleep(wait_effective)

    def disconnect(self):
        """Disconnect from MQTT server."""
        self.client.disconnect()
        self.connected = False

    @staticmethod
    def construct_mqttdata(field2values):
        """Construct a 2-dimensional dictionary fieldname-->value-type-->value.

        Example:
           total --> mean --> value
           result['tptal']['mean'] := mean(collected-values)

        :param field2values: collected data, dictionary: fieldname --> [data points]
        :return: 2-dim dictionary fieldname --> value-type --> value
        """
        result = {}
        # special handling for time field
        if 'time' in field2values:
            result['time'] = {}
            result['time']['first'] = field2values['time'][0]
            result['time']['last'] = field2values['time'][-1]
        for name, values in field2values.items():
            if name == 'time':
                # do not output math statistics such as below for time field
                continue
            if not values:
                # could be empty, e.g. if no such data has been observed
                continue
            if name == "total":
                result[name] = {}
                result[name]['value'] = values[-1]
                result[name]['first'] = values[0]
                result[name]['last'] = values[-1]
                continue
            result[name] = {}
            result[name]['value'] = values[-1]
            result[name]['first'] = values[0]
            result[name]['last'] = values[-1]
            result[name]['median'] = round(statistics.median(values), 1)
            result[name]['mean'] = round(statistics.mean(values), 1)
            result[name]['min'] = min(values)
            result[name]['max'] = max(values)
            result[name]['stdev'] = round(statistics.stdev(values), 1)
        return result

    def send(self, field2values):
        """Publish (send) data to MQTT.

        :param field2values: collected data, dictionary: fieldname --> [data points]
        :return: Nothing
        """
        if not self.connected:
            self.connect()

        topic_prefix = self.config.get('Mqtt', 'topic_prefix', fallback='tele/smartmeter')
        single = self.config.getboolean('Mqtt', 'single_topic', fallback='false')

        # construct 2-dim dictionary fieldname --> value-type --> value
        mqttdata = self.construct_mqttdata(field2values)

        if single:
            # single-topic sending, i.e. everything as one single topic and JSON payload
            self.client.publish(topic_prefix, json.dumps(mqttdata))
        else:
            # multi-topic sending, i.e. each data entry as one unique topic, multiple messages
            for name, subname_value in mqttdata.items():
                for subname, value in subname_value.items():
                    topic = "%s/%s/%s" % (topic_prefix, name, subname)
                    self.client.publish(topic, value)


def convert_messages2records(messages):
    """Convert a list of message-dictionaries to a dictionary with value-lists.

    This is:
        [ {a:11, b:12}, {a:21, b:22}, ... ]  --> {a:[11,21], b:[12,22]}

    :param messages:
    :return:
    """
    records = {}
    for message in messages:
        for key, value in message.items():
            if key in records:
                records[key].append(value)
            else:
                records[key] = [value]  # start a new list
    return records


def check_stream_packet_begin(line):
    """Check if the given string line contains a SML header indicating a new message block.

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


def processing_loop(istream, window_size, callback, timeout=0, deltas=None):
    """Run the main processing loop on input stream.

    If size of rolling window is reached then call handler function mqtt_or_println.
    A timeout can be specified to stop after n seconds of no data (e.g. for STDIN).

    :param istream: input stream
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
        line = istream.readline().strip()
        if not line:
            n_nodata += 1
            if timeout and n_nodata >= timeout:
                logging.warning("#%d times no data observed, timeout hit, aborting!", n_nodata)
                messages.append(message)
                callback(messages)
                break
            logging.debug("No data observed...waiting 1 second...")
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
                logging.info("window (%d) filled, handling #%d messages...", window_size, n_msgs)
                callback(messages)  # handle all messages
                messages = []       # start a new collection
            elif deltas and n_msgs >= 2:
                # dynamic checking of all fields in message according to declared delta-thresholds
                for field_name, delta_value in deltas.items():
                    if field_name not in messages[-2] or field_name not in messages[-1]:
                        logging.warning("No such field with name '%s' in message!", field_name)
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
                        messages = []       # start a new collection
                        # stop delta stuff, i.e., only 1 handling when delta event happens
                        break

            # current header-line is done, proceed to next line
            continue

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
    arg_debug = arguments['--debug']
    arg_quiet = arguments['--quiet']
    arg_no_mqtt = arguments['--no-mqtt']

    # setup logging
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    if DEBUG or arg_debug:
        logging.getLogger('').setLevel(logging.DEBUG)
        logging.debug('---- ENABLING DEBUG OUTPUT!!! -------')
        logging.debug(arguments)
    elif arg_verbose:
        logging.getLogger('').setLevel(logging.INFO)
    elif arg_quiet:
        logging.getLogger('').setLevel(logging.ERROR)

    logging.info(version_string)
    logging.debug("arguments: %s", arguments)

    # Configuration
    config = configparser.ConfigParser()
    if arg_configfile:
        if not os.path.isabs(arg_configfile):
            # if not an absolute path then make it one based on this very script's folder
            arg_configfile = os.path.join(__SCRIPT_DIR, arg_configfile)
        arg_configfile = os.path.abspath(arg_configfile)
        logging.info("Config file: %s", arg_configfile)
        if not (os.path.isfile(arg_configfile) and os.access(arg_configfile, os.R_OK)):
            logging.error('Config file is not a file or not accessible! Aborting.')
            return ExitCodes.CONFIG_FAIL
        config.read(arg_configfile)
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
    logging.info('Aggregation/rolling window size: %d', window_size)

    # input stream
    if arg_input == '-':
        # pylint: disable=consider-using-with
        istream = sys.stdin
    else:
        istream = open(arg_input)
    logging.info("Input stream: %s", istream)

    # MQTT
    mymqtt = MyMqtt(config)

    def mqtt_or_println(messages):
        records = convert_messages2records(messages)
        if arg_no_mqtt:
            mqttdata = MyMqtt.construct_mqttdata(records)
            print('mqttdata:')
            pprint(mqttdata)
        else:
            mymqtt.send(records)

    # main processing loop on input stream
    # if size of rolling window is reached then call handler function mqtt_or_println
    processing_loop(istream, window_size, mqtt_or_println, deltas=deltas)

    return ExitCodes.OK


if __name__ == '__main__':
    if DEBUG:
        sys.argv.append('--verbose')
    if os.environ.get("PROFILE", "").lower() in ("true", "1", "yes"):
        # pylint: disable-next=ungrouped-imports
        from time import strftime
        import cProfile
        import pstats
        profile_filename = "%s_%s" % (__file__, strftime('%Y-%m-%d_%H%M%S')).profile
        cProfile.run('main()', profile_filename)
        with open("%s.txt" % profile_filename, "w", encoding="utf8") as statsfp:
            profile_stats = pstats.Stats(profile_filename, stream=statsfp)
            stats = profile_stats.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())
