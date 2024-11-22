#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MQTT publishing."""
import json
import logging
import statistics
import time

from paho.mqtt import client as mqtt_client


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
            logging.info("MQTT connect: %s (%d)", mqtt_client.connack_string(rc), rc)
            self.connected = True

        # noinspection PyUnusedLocal,PyShadowingNames
        # pylint: disable=invalid-name,unused-argument
        def on_disconnect(client, userdata, rc):
            self.connected = False
            if rc == mqtt_client.MQTT_ERR_SUCCESS:
                logging.info('MQTT disconnect: successful.')
            else:
                logging.warning("MQTT unexpected disconnection! %s (%d)",
                                mqtt_client.error_string(rc), rc)

        ##
        # NOTE!
        # Creating a new Client() seems to be necessary.
        # Just using reconnect() or connect() again did not work.
        ##
        client = mqtt_client.Client("SmlTextMqttProcessor")

        # store as class variable to be accessible later
        self.client = client

        if self.config.has_option('Mqtt', 'username'):
            client.username_pw_set(self.config.get('Mqtt', 'username'),
                                   password=self.config.get('Mqtt', 'password'))
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect

        host = self.config.get('Mqtt', 'host', fallback='localhost')
        port = self.config.getint('Mqtt', 'port', fallback=1883)

        # try-to-connect loop
        wait_time = 1
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
                logging.debug("waiting %d seconds before reconnect attempt...",
                              wait_effective)
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
            result['time']['value'] = field2values['time'][-1]
            result['time']['first'] = field2values['time'][0]
            result['time']['last'] = field2values['time'][-1]
        for name, values in field2values.items():
            if name == 'time':
                # do not output math statistics (mean, stddev etc.) for the time field
                continue
            if not values:
                # could be empty, e.g. if no such data has been observed
                continue
            if name == "total":
                # special handling for the "total" field (no math stats)
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
        retain = self.config.getboolean('Mqtt', 'retain', fallback='false')

        # construct 2-dim dictionary fieldname --> value-type --> value
        mqttdata = self.construct_mqttdata(field2values)

        if single:
            # single-topic sending, i.e. everything as one single topic and JSON payload
            self.client.publish(topic_prefix, json.dumps(mqttdata), retain=retain)
        else:
            # multi-topic sending, i.e. each data entry as one unique topic, multiple messages
            for name, subname_value in mqttdata.items():
                # name = e.g. total / actual
                # subname_value = dict e.g. {"first": 123) / {"mean": 56.5} / ...
                for subname, value in subname_value.items():
                    # name = e.g. total / actual
                    # subname = e.g. value / min / max / first / last / ...

                    # by default do not set the MQTT retain flag but only for specific fields
                    myretain = False
                    if retain and name in ('total', 'time') and subname == 'value':
                        # only retain for .../total/value and .../time/value
                        myretain = True

                    # construct topic, e.g., 'tele/smartmeter/time/value'
                    topic = "%s/%s/%s" % (topic_prefix, name, subname)  # pylint: disable=consider-using-f-string
                    # MQTT publish
                    self.client.publish(topic, value, retain=myretain)
