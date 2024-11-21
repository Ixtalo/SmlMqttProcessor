import json
from configparser import ConfigParser

import smlmqttprocessor.mqtt as mqtt


class TestMqtt:
    """Tests for "sending" of data via (virtual/mocked) MQTT."""

    def test_send(self, monkeypatch):

        def connect_dummy(_, host, port=1883):
            print("CONNECT DUMMY", host, port)

        def publish_dummy(_, topic, payload=None, retain=False):
            print(topic, payload, retain)
            # we expect multiple messages, multiple topics
            assert topic.startswith('tele/smartmeter')
            # one check for each topic...
            if topic == 'tele/smartmeter/time/first':
                assert payload == 111
                assert not retain
            elif topic == 'tele/smartmeter/time/last':
                assert payload == 333
                assert not retain
            elif topic == 'tele/smartmeter/time/value':
                assert payload == 333
                assert retain   # yes, retain this field!
            elif topic == 'tele/smartmeter/total/value':
                assert payload == 3
                assert retain   # yes, retain this field!
            elif topic == 'tele/smartmeter/total/first':
                assert payload == 1
                assert not retain
            elif topic == 'tele/smartmeter/total/last':
                assert payload == 3
                assert not retain
            elif topic == 'tele/smartmeter/actual/first':
                assert payload == -11
                assert not retain
            elif topic == 'tele/smartmeter/actual/last':
                assert payload == 99
                assert not retain
            elif topic == 'tele/smartmeter/actual/median':
                assert payload == 16.5
                assert not retain
            elif topic == 'tele/smartmeter/actual/mean':
                assert payload == 22
                assert not retain
            elif topic == 'tele/smartmeter/actual/min':
                assert payload == -22
                assert not retain
            elif topic == 'tele/smartmeter/actual/max':
                assert payload == 99
                assert not retain

        # mock the MQTT client to not do the actual MQTT publishing
        monkeypatch.setattr(mqtt.mqtt_client.Client, "connect", connect_dummy)
        monkeypatch.setattr(mqtt.mqtt_client.Client, "publish", publish_dummy)

        # test data
        data = {
            'total': [1, 2, 3],
            'actual': [-11, -22, 11, 22, 33, 99],
            'act_sensor_time': [111, 222, 333]
        }
        config = ConfigParser()

        # run / test
        mymqtt = mqtt.MyMqtt(config)
        mymqtt.connected = True
        mymqtt.client = mqtt.mqtt_client.Client()
        mymqtt.send(data)

    def test_construct_data(self):
        data = {
            'total': [1.111, 2.222, 3.333],
            'actual': [-11.1, -22.2, 11.1, 22.2, 33.3, 99.9],
            'time': [111.1, 222.2, 333.3]
        }
        config = ConfigParser()

        # run / test
        mymqtt = mqtt.MyMqtt(config)
        actual = mymqtt.construct_mqttdata(data)
        expected = {'actual': {'first': -11.1,
                               'last': 99.9,
                               'max': 99.9,
                               'mean': 22.2,
                               'median': 16.6,
                               'min': -22.2,
                               'stdev': 43.3,
                               'value': 99.9},
                    'time': {'first': 111.1, 'last': 333.3, 'value': 333.3},
                    'total': {'first': 1.111,
                              'last': 3.333,
                              'value': 3.333}
                    }
        assert actual == expected


class TestMqttSingleTopic:
    """Tests for "sending" of data via (mocked) MQTT as one single topic as JSON.
    (Instead of multiple MQTT messages just send one JSON formatted message.)
    """

    def test_send(self, monkeypatch):
        def connect_dummy(_, host, port=1883):
            print("CONNECT DUMMY", host, port)

        def publish_dummy(_, topic, payload=None, retain=False):
            print(topic, payload, retain)
            assert topic == 'tele/smartmeter'
            # everything as just one single topic, payload as JSON
            # use json.dumps to compare the two dictionaries
            # (NOTE: dictionary sorting varies between Python versions and platforms!)
            actual = json.loads(payload)
            expected = {
                "time": {"first": 111.1, "last": 333.3, "value": 333.3},
                "actual": {
                    "first": -11.1,
                    "last": 99.9,
                    "max": 99.9,
                    "mean": 22.2,
                    "median": 16.6,
                    "min": -22.2,
                    "stdev": 43.3,
                    "value": 99.9
                },
                "total": {
                    "first": 1.111,
                    "last": 3.333,
                    "value": 3.333
                }
            }
            assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)

        # mock the MQTT client to not do the actual MQTT publishing
        monkeypatch.setattr(mqtt.mqtt_client.Client, "connect", connect_dummy)
        monkeypatch.setattr(mqtt.mqtt_client.Client, "publish", publish_dummy)

        # test data
        data = {
            'total': [1.111, 2.222, 3.333],
            'actual': [-11.1, -22.2, 11.1, 22.2, 33.3, 99.9],
            'time': [111.1, 222.2, 333.3]
        }
        config = ConfigParser()
        config.add_section('Mqtt')
        config.set('Mqtt', 'single_topic', 'true')

        # run / test
        mymqtt = mqtt.MyMqtt(config)
        mymqtt.connected = True
        mymqtt.client = mqtt.mqtt_client.Client()
        mymqtt.send(data)
