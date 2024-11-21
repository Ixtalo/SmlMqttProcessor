#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_d0_d1.py - Process MQTT messages to produce today (d0) & yesterday (d1).

The Python program listens to incoming MQTT messages from a 
smart meter, capturing real-time consumption data. It processes 
this data to compute the current consumption value for the 
day (d0) and the previous day (d1). These daily consumption 
metrics are then published back to a designated MQTT topic, 
allowing for continuous updates on today's and yesterday's 
power usage.

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
from pathlib import Path
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt

from smlmqttprocessor.utils.mylogging import setup_logging

MQTT_TOPIC_SMARTMETER_TOTAL = "tele/smartmeter/total/value"
MQTT_TOPIC_D0 = "tele/smartmeter/total/d0"
MQTT_TOPIC_D1 = "tele/smartmeter/total/d1"


LOGGING_STREAM = sys.stdout
DEBUG = bool(os.getenv("DEBUG", "").lower() in ("1", "true", "yes"))
__script_dir = Path(__file__).parent


class EnergyMonitor:
    d0_retained = None
    d1_retained = None

    def __init__(self, retain: bool = True):
        self.retain = retain
        self.data = []
        self.d0 = None  # today
        self.d1 = None  # yesterday
        self.current_date = datetime.now().date()  # start date

    def add_value(self, total_value: float):
        timestamp = datetime.now()
        self.data.append({'timestamp': timestamp, 'value': total_value})

        # calculate the difference (delta) aka consumption today so far (d_0)
        delta = self.calculate_daily_consumption()
        if not delta:
            logging.debug("d0 delta: not enough data yet")
        else:
            logging.debug("d0 delta since start: %.2f", delta)
            self.d0 = delta
            # if there has been a retained value, use it as offset from now on
            self.d0 += self.d0_retained if self.d0_retained else 0
            # tell/publish
            logging.info("d0: %.2f", self.d0)

        # check if there's a new day
        if timestamp.date() != self.current_date:
            # reset on new day
            self.d0_retained = 0
            self.current_date = timestamp.date()
            # calculate the difference (delta) aka consumption of yesterday (d_-1)
            delta = self.calculate_yesterday_consumption()
            if not delta:
                logging.debug("d1 delta: not enough data yet")
            else:
                logging.debug("d1 delta since start: %.2f", delta)
                self.d1 = delta
                # if there has been a retained value, use it as offset from now on
                self.d1 += self.d1_retained if self.d1_retained else 0
                # tell/publish
                logging.info("d1: %.2f", self.d1)

    def calculate_daily_consumption(self):
        """Calculate the consumption of today (d_0)."""
        today = datetime.now().date()
        # slice data to just today's subset
        today_data = [entry['value'] for entry in self.data if entry['timestamp'].date() == today]
        if len(today_data) > 1:
            return today_data[-1] - today_data[0]
        return None

    def calculate_yesterday_consumption(self):
        """Calculate the consumption of yesterday (d_-1)."""
        yesterday = datetime.now().date() - timedelta(days=1)
        # slice data to yesterday
        yesterday_data = [entry['value'] for entry in self.data if entry['timestamp'].date() == yesterday]
        if len(yesterday_data) > 1:
            return yesterday_data[-1] - yesterday_data[0]
        return None


def handle_smartmeter_message(client, userdata, msg):
    """Handle MQTT message for smartmeter total values."""
    value = float(msg.payload.decode())
    userdata.add_value(value)
    if userdata.d0 and not DEBUG:
        client.publish(MQTT_TOPIC_D0, round(userdata.d0, 2), retain=userdata.retain)
    if userdata.d1 and not DEBUG:
        client.publish(MQTT_TOPIC_D1, round(userdata.d1, 2), retain=userdata.retain)


def handle_retained_dx_message(client, userdata, msg):
    """Handle MQTT retained messages to use as initial offsets."""
    logging.debug("handle_last_dx_message: %s = %s", msg.topic, msg.payload)
    value = float(msg.payload.decode())
    if msg.topic == MQTT_TOPIC_D0:
        # store value to be used as initial offset
        userdata.d0_retained = value
        logging.info("d0 (retained): %.2f", userdata.d0_retained)
        # no further handling of this topic is required
        client.unsubscribe(msg.topic)
    elif msg.topic == MQTT_TOPIC_D1:
        # store value to be used as initial offset
        userdata.d1_retained = value
        logging.info("d1 (retained): %.2f", userdata.d1_retained)
        # no further handling of this topic is required
        client.unsubscribe(msg.topic)
    else:
        logging.warning("Unexpected message! (%s, %s)", msg.topic, msg.payload)


def get_config(configfile: Path):
    """Read configuration from confile file."""
    config = configparser.ConfigParser()
    if not configfile.is_absolute():
        configfile = __script_dir.joinpath(configfile)
    logging.info("Config file: %s", configfile.resolve())
    if not configfile.is_file():
        raise RuntimeError(f"No configfile! ({configfile.resolve()})")
    if not os.access(configfile, os.R_OK):
        raise RuntimeError(f"Configfile not readable! ({configfile.resolve()})")
    res = config.read(configfile)
    logging.debug("config read result: %s", res)
    return config


def main():
    # set up logging framework
    setup_logging(level=logging.INFO if not DEBUG else logging.DEBUG)

    # configuration
    config = get_config(Path('config.ini'))
    mqtt_username = config.get('Mqtt', 'username')
    mqtt_password = config.get('Mqtt', 'password')
    mqtt_host = config.get('Mqtt', 'host', fallback='localhost')
    mqtt_port = config.getint('Mqtt', 'port', fallback=1883)
    mqtt_retain = config.getboolean('Mqtt', 'retain', fallback='true')

    # MQTT initialization
    client = mqtt.Client(userdata=EnergyMonitor(retain=mqtt_retain))
    client.username_pw_set(username=mqtt_username, password=mqtt_password)
    client.enable_logger()

    # MQTT message callbacks
    client.message_callback_add(MQTT_TOPIC_D0, handle_retained_dx_message)
    client.message_callback_add(MQTT_TOPIC_D1, handle_retained_dx_message)
    client.message_callback_add(MQTT_TOPIC_SMARTMETER_TOTAL, handle_smartmeter_message)

    # initialize MQTT connection
    client.connect(mqtt_host, port=mqtt_port)
    # NOTE subscriptions must come *after* connect() !
    # subscribe to the retained messages
    client.subscribe(MQTT_TOPIC_D0)
    client.subscribe(MQTT_TOPIC_D1)
    # subscribe to the very topic which contains the source data
    client.subscribe(MQTT_TOPIC_SMARTMETER_TOTAL)

    client.loop_forever()


if __name__ == "__main__":
    main()
