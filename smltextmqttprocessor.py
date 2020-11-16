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
import configparser
import logging
import os
import statistics
import sys
import time
import json
from codecs import open
from pprint import pprint

from docopt import docopt

## https://pypi.org/project/paho-mqtt/#usage-and-api
import paho.mqtt.client as mqtt
## PySML, https://pypi.org/project/pysml/
# noinspection PyUnresolvedReferences,PyPackageRequirements
import sml

__version__ = "1.6.2"
__date__ = "2020-04-21"
__updated__ = "2020-09-27"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"


########################################################################
## Configure the following to suit your actual smart meter configuration
##

## SML OBIS fields
## dictionary: MQTT-topic --> OBIS-code
## for OBIS codes see e.g. https://wiki.volkszaehler.org/software/obis
SML_FIELDS = {
    'total': '1-0:1.8.0*255',           ## Zählerstand Bezug
    'total_tariff1': '1-0:1.8.1*255',   ## Zählerstand Bezug Tarif 1
    'total_tariff2': '1-0:1.8.2*255',   ## Zählerstand Bezug Tarif 2
    'total_tariff3': '1-0:1.8.3*255',   ## Zählerstand Bezug Tarif 3
    'total_tariff4': '1-0:1.8.4*255',   ## Zählerstand Bezug Tarif 4

    'total_export': '1-0:2.8.0*255',           ## Zählerstand Lieferung
    'total_export_tariff1': '1-0:2.8.1*255',   ## Zählerstand Lieferung Tarif 1
    'total_export_tariff2': '1-0:2.8.2*255',   ## Zählerstand Lieferung Tarif 2
    'total_export_tariff3': '1-0:2.8.3*255',   ## Zählerstand Lieferung Tarif 3
    'total_export_tariff4': '1-0:2.8.4*255',   ## Zählerstand Lieferung Tarif 4

    'actual': '1-0:16.7.0*255',         ## Leistung (Momentan)
    'actual_l1': '1-0:36.7.0*255',      ## Leistung L1 (Momentan)
    'actual_l2': '1-0:56.7.0*255',      ## Leistung L2 (Momentan)
    'actual_l3': '1-0:76.7.0*255',      ## Leistung L3 (Momentan)
    'actual_170': '1-0:1.7.0*255',      ## Wirkleistung

    'time': 'act_sensor_time'
}

## SML headers as list/tuple for header-detection heuristic
## (OBIS code for manufacturer identification)
SML_HEADERS = ('1-0:96.50.1*1#', '129-129:199.130.3*255#')

##
########################################################################

DEBUG = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)


class MyMqtt:
    """
    MQTT publishing.
    """

    def __init__(self, config):
        """
        MQTT publishing
        :param config: ConfigParser object, e.g. from config.ini
        """
        self.client = None
        self.config = config
        self.connected = False

    def connect(self):

        # noinspection PyUnusedLocal,PyShadowingNames
        def on_connect(client, userdata, flags, rc):
            logging.info("MQTT connected: %s (%d)", mqtt.connack_string(rc), rc)
            self.connected = True

        # noinspection PyUnusedLocal,PyShadowingNames
        def on_disconnect(client, userdata, rc):
            self.connected = False
            if rc == mqtt.MQTT_ERR_SUCCESS:
                logging.debug('MQTT: disconnect successful.')
            else:
                logging.warning("MQTT unexpected disconnection! %s (%d)", mqtt.error_string(rc), rc)

        ##
        ## NOTE!
        ## Creating a new Client() seems to be necessary.
        ## Just using reconnect() or connect() again did not work.
        ##
        client = mqtt.Client("SmlTextMqttProcessor")

        ## store as class variable to be accessible later
        self.client = client

        if self.config.has_option('Mqtt', 'username'):
            client.username_pw_set(self.config.get('Mqtt', 'username'),
                                   password=self.config.get('Mqtt', 'password'))
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect

        ## try-to-connect loop
        client.connected = False
        wait_time = 1
        host = self.config.get('Mqtt', 'host', fallback='localhost')
        port = self.config.getint('Mqtt', 'port', fallback=1883)
        while not self.connected:
            try:
                client.connect(host, port=port)
                ## loop_start() is necessary for on_* to work
                ## (asynchronous handling starts)
                client.loop_start()
                break
            except Exception as ex:
                logging.error("MQTT connect exception! %s: %s", type(ex).__name__, ex)
                ## increase waiting time
                wait_time *= 2
                ## limit waiting time to max. 180 sec = 3 min
                wait_effective = min(wait_time, 180)
                logging.debug("waiting %d seconds before reconnect attempt...", wait_effective)
                time.sleep(wait_effective)

    def disconnect(self):
        self.client.disconnect()
        self.connected = False

    @staticmethod
    def construct_mqttdata(field2values):
        """
        Construct a 2-dimensinal dictionary:
           fieldname --> value-type --> value

        Example:
           total --> mean --> value
           result['tptal']['mean'] := mean(collected-values)

        :param field2values: collected data, dictionary: fieldname --> [data points]
        :return: 2-dim dictionary fieldname --> value-type --> value
        """
        result = {}
        ## special handling for time field
        if 'time' in field2values:
            result['time'] = {}
            result['time']['first'] = field2values['time'][0]
            result['time']['last'] = field2values['time'][-1]
        for name, values in field2values.items():
            if name == 'time':
                ## do not output math statistics such as below for time field
                continue
            if not values:
                ## could be empty, e.g. if no such data has been observed
                continue
            result[name] = {}
            result[name]['value'] = values[-1]
            result[name]['first'] = values[0]
            result[name]['last'] = values[-1]
            result[name]['median'] = statistics.median(values)
            result[name]['mean'] = round(statistics.mean(values))
            result[name]['min'] = min(values)
            result[name]['max'] = max(values)
        return result

    def send(self, field2values):
        """
        Sends (publish) data to MQTT.
        :param field2values: collected data, dictionary: fieldname --> [data points]
        :return: Nothing
        """
        if not self.connected:
            self.connect()

        topic_prefix = self.config.get('Mqtt', 'topic_prefix', fallback='tele/smartmeter')
        single = self.config.getboolean('Mqtt', 'single_topic', fallback='false')

        ## construct 2-dim dictionary fieldname --> value-type --> value
        mqttdata = self.construct_mqttdata(field2values)

        if single:
            ## single-topic sending, i.e. everything as one single topic and JSON payload
            self.client.publish(topic_prefix, json.dumps(mqttdata))
        else:
            ## multi-topic sending, i.e. each data entry as one unique topic, multiple messages
            for name, subname_value in mqttdata.items():
                for subname, value in subname_value.items():
                    topic = "%s/%s/%s" % (topic_prefix, name, subname)
                    self.client.publish(topic, value)

        self.disconnect()


def convert_messages2records(messages):
    """
    Convert a list of message-dictionaries to a dictionary with value-lists.
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
                records[key] = [value]  ## start a new list
    return records


def check_stream_packet_begin(line):
    """
    Check if the given string line contains a SML header indicating
    a new message block.
    :param line: line (string)
    :return: True if begin of new message
    """
    for header in SML_HEADERS:
        if line.startswith(header):
            ## yes, this is the starting line
            return True
    return False


def parse_line(line):
    """
    Parse a single SML line.
    :param line: SML message line
    :return: (fieldname, value) tuple according to SML_FIELDS
    """
    if not line:
        return None
    for name, pattern in SML_FIELDS.items():
        if line.startswith(pattern):
            ## found a matching line, take the value from this line
            _, value, _ = line.split('#', 2)  ## (OBIS code, value, unit)

            ## detect int/float values
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            return name, value
    return None


def processing_loop(istream, window_size, callback, timeout=0):
    """
    Main processing loop on input stream.
    If size of rolling window is reached then call handler function mqtt_or_println.
    A timeout can be specified to stop after n seconds of no data (e.g. for STDIN).
    
    :param istream: input stream
    :param window_size: rolling window size, size of aggregation window
    :param callback: reference to messages handling callback function
    :param timeout: timeout in seconds, 0 for no timeout
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

        if type(line) is bytes:
            ## make sure line is a string, not bytes
            line = line.decode()

        ## check if this is a header line, i.e. beginning of new message block
        if check_stream_packet_begin(line):
            if message:     ## initial loops have empty message...
                ## record current message
                messages.append(message)
                logging.debug("message: %s", message)

            ## new header line, new message
            message = {}

            ## check if we filled the window
            if len(messages) >= window_size:
                logging.debug("window filled (#%d), handling...", window_size)
                ## handle all messages
                callback(messages)
                ## start a new collection
                messages = []

            ## current header-line is done, proceed to next line
            continue

        ## parse line and add it to current message
        try:
            result = parse_line(line)
            if result:
                fieldname, value = result
                ## NOTE: duplicate lines of same type would overwrite old values
                ## until a new header line occurs (i.e., next SML message block)
                message[fieldname] = value
        except ValueError as ex:
            logging.error("Invalid message '%s': %s", line, ex)

        time.sleep(0.01)


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
    mymqtt = MyMqtt(config)

    ## rolling window period
    window_size = config.getint(configparser.DEFAULTSECT, 'block_size')
    logging.info('Aggregation/rolling window size: %d', window_size)

    ## input stream
    if arg_input == '-':
        istream = sys.stdin
    else:
        istream = open(arg_input)
    logging.info("Input stream: %s", istream)

    def mqtt_or_println(messages):
        records = convert_messages2records(messages)
        if arg_no_mqtt:
            mqttdata = MyMqtt.construct_mqttdata(records)
            print('mqttdata:')
            pprint(mqttdata)
        else:
            mymqtt.send(records)

    ## main processing loop on input stream
    ## if size of rolling window is reached then call handler function mqtt_or_println
    processing_loop(istream, window_size, mqtt_or_println)

    return 0


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("--debug")
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = __file__ + '.profile.bin'
        cProfile.run('main()', profile_filename)
        with open("%s.txt" % profile_filename, "w") as statsfp:
            p = pstats.Stats(profile_filename, stream=statsfp)
            stats = p.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())
