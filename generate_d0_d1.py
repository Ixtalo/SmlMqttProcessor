#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_d0_d1.py - Process MQTT messages to produce today (d0) & yesterday (d1).

The Python program listens to incoming MQTT messages from a smart meter, capturing real-time consumption data. It processes this data to compute the current consumption value for the day (d0) and the previous day (d1). These daily consumption metrics are then published back to a designated MQTT topic, allowing for continuous updates on today's and yesterday's power usage.

Usage:
  generate_d0_d1.py

"""
#
# LICENSE:
#
# Copyright (C) 2024 Ixtalo, ixtalo@gmail.com
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
from datetime import datetime

import colorlog
import paho.mqtt.client as mqtt
import pandas as pd


LOGGING_STREAM = sys.stdout
DEBUG = bool(os.getenv("DEBUG", "").lower() in ("1", "true", "yes"))
__script_dir = os.path.dirname(os.path.realpath(__file__))


def setup_logging(level: int = logging.INFO, log_file: str = None, no_color=False):
    """Set up the logging framework."""
    # logging.basicConfig(level=logging.WARNING if not DEBUG else logging.DEBUG,
    #                    stream=LOGGING_STREAM,
    #                    format="%(asctime)s %(levelname)-8s %(message)s",
    #                    datefmt="%Y-%m-%d %H:%M:%S")
    if log_file:
        # pylint: disable=consider-using-with
        stream = open(log_file, "a", encoding="utf8")
        no_color = True
    else:
        stream = LOGGING_STREAM
    handler = colorlog.StreamHandler(stream=stream)
    format_string = "%(log_color)s%(asctime)s %(levelname)-8s %(message)s"
    formatter = colorlog.ColoredFormatter(format_string,
                                          datefmt="%Y-%m-%d %H:%M:%S",
                                          no_color=no_color)
    handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[handler])


setup_logging(level=logging.INFO if not DEBUG else logging.DEBUG)


# Configuration
config = configparser.ConfigParser()
configfile = 'config.ini'
if not os.path.isabs(configfile):
    # if not an absolute path then make it one based on this very script's folder
    arg_configfile = os.path.join(__script_dir, configfile)
configfile = os.path.abspath(arg_configfile)
logging.info("Config file: %s", arg_configfile)
if not (os.path.isfile(arg_configfile) and os.access(arg_configfile, os.R_OK)):
    logging.error('Config file is not a file or not accessible! Aborting.')
    sys.exit(3)
config.read(arg_configfile)


mqtt_username = config.get('Mqtt', 'username')
mqtt_password = config.get('Mqtt', 'password')
mqtt_host = config.get('Mqtt', 'host', fallback='localhost')
mqtt_port = config.getint('Mqtt', 'port', fallback=1883)

data = pd.DataFrame(columns=['timestamp', 'value'])
d0_retained = None
d1_retained = None

#client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client = mqtt.Client()
client.username_pw_set(username=mqtt_username, password=mqtt_password)
client.enable_logger()


def handle_smartmeter_message(client, _, msg):
    global data, d0_retained, d1_retained
    logging.debug("handle_smartmeter_message: %s", msg.payload)

    value = float(msg.payload.decode())
    timestamp = datetime.now()
    
    # Neuen Eintrag in das DataFrame hinzufügen
    new_row = pd.DataFrame({'timestamp': [timestamp], 'value': [value]})
    data = pd.concat([data, new_row], ignore_index=True)
 
    # Tagesverbrauch (d_0) berechnen
    data['date'] = data['timestamp'].dt.date
    today = datetime.now().date()

    # Verbrauch für den aktuellen Tag berechnen
    today_data = data[data['date'] == today]
    if len(today_data) > 1:
        # value difference (delta) between today's last and first value
        d0 = today_data['value'].iloc[-1] - today_data['value'].iloc[0]
        logging.debug("d0: %.2f", d0)
        # if there has been a retained value, use it as offset from now on
        d0 += d0_retained if d0_retained else 0
        logging.debug("d0: %.2f", d0)
        # tell/publish
        logging.info("d0: %.2f", d0)
        if not DEBUG:
            client.publish("tele/smartmeter/total/d0", d0, retain=True)

    # Verbrauch des Vortags (d_-1) berechnen, wenn ein neuer Tag beginnt
    if timestamp.hour == 0 and timestamp.minute == 0:
        yesterday = today - pd.Timedelta(days=1)
        yesterday_data = data[data['date'] == yesterday]
        if len(yesterday_data) > 1:
            d1 = yesterday_data['value'].iloc[-1] - yesterday_data['value'].iloc[0]
            logging.debug("d1: %.2f", d1)
            # if there has been a retained value, use it as offset from now on
            d1 += d1_retained if d1_retained else 0
            logging.debug("d1: %.2f", d1)
            # tell/publish
            logging.info("d1: %.2f", d1)
            if not DEBUG:
                client.publish("tele/smartmeter/total/d1", d1, retain=True)
            # reset
            d0_retained = 0


def handle_retained_dx_message(client, userdata, msg):
    """Handle the last retained message to use that as initial offset."""
    global d0_retained, d1_retained
    logging.debug("handle_last_dx_message: %s = %s", msg.topic, msg.payload)
    value = float(msg.payload.decode())
    if msg.topic == "tele/smartmeter/total/d0":
        # store value to be used as initial offset
        d0_retained = value
        logging.info("d0 (retained): %.2f", d0_retained)
        # no further handling of this topic is required
        client.unsubscribe(msg.topic)
    elif msg.topic == "tele/smartmeter/total/d1":
        # store value to be used as initial offset
        d1_retained = value
        logging.info("d1 (retained): %.2f", d1_retained)
        # no further handling of this topic is required
        client.unsubscribe(msg.topic)
    else:
        logging.warning("Unexpected message! (%s, %s)", msg.topic, msg.payload)


# define the message handlers
client.message_callback_add("tele/smartmeter/total/d0", handle_retained_dx_message)
client.message_callback_add("tele/smartmeter/total/d1", handle_retained_dx_message)
client.message_callback_add("tele/smartmeter/total/value", handle_smartmeter_message)

# initialize MQTT connection
client.connect(mqtt_host, port=mqtt_port)
# NOTE subscriptions must come *after* connect() !
# subscribe to our retained messages
client.subscribe("tele/smartmeter/total/d0")
client.subscribe("tele/smartmeter/total/d1")
# subscribe to the very data source
client.subscribe("tele/smartmeter/total/value")

client.loop_forever()
