#!pytest
# -*- coding: utf-8 -*-
"""
Unit tests for smltextmqttprocessor.py, using pytest.
"""

import io
import pytest
import smltextmqttprocessor as stmp
from configparser import ConfigParser


class TestInputStreamISK:

    ## By declaring fixture with autouse=True, it will be automatically
    ## invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        ## before
        self.istream = io.StringIO()
        self.istream.write("""1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#1000.1#Wh
1-0:16.7.0*255#1.1#W
act_sensor_time#1#

1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#1000.2#Wh
1-0:16.7.0*255#2.2#W
act_sensor_time#2#
""")
        self.istream.seek(0)

        ## A test function will be run at this point
        yield

        ## after
        # ...

    def test_check_stream_packet_begin(self):
        assert stmp.check_stream_packet_begin(self.istream)

    def test_check_stream_packet_begin_empty(self):
        assert not stmp.check_stream_packet_begin(io.StringIO())

    def test_check_stream_packet_begin_noheader(self):
        istream = io.StringIO()
        istream.write("""1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#12345
1-0:16.7.0*255#26#W""")
        istream.seek(0)
        assert not stmp.check_stream_packet_begin(istream)

    def test_parse_stream(self):
        result = stmp.parse_stream(self.istream)
        assert result is not None and type(result) is dict, "Dict return value expected!"
        assert result['total'] == 1000.1
        assert result['actual'] == 1.1
        assert result['time'] == 1

        result = stmp.parse_stream(self.istream)
        assert result is not None and type(result) is dict, "Dict return value expected!"
        assert result['total'] == 1000.2
        assert result['actual'] == 2.2
        assert result['time'] == 2


    def test_parse_stream_nototal(self):
        istream = io.StringIO()
        istream.write("""1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:16.7.0*255#987#W
act_sensor_time#123#""")
        istream.seek(0)
        result = stmp.parse_stream(istream)
        assert result is not None and type(result) is dict, "Dict return value expected!"
        assert 'total' not in result
        assert result['actual'] == 987
        assert result['time'] == 123

    def test_parse_stream_noactual(self):
        istream = io.StringIO()
        istream.write("""1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#12345#Wh
act_sensor_time#123#""")
        istream.seek(0)
        result = stmp.parse_stream(istream)
        assert result['total'] == 12345.0
        assert 'actual' not in result
        assert result['time'] == 123

    def test_parse_stream_notime(self):
        istream = io.StringIO()
        istream.write("""1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#12345#Wh
1-0:16.7.0*255#987#W""")
        istream.seek(0)
        result = stmp.parse_stream(istream)
        assert result['total'] == 12345.0
        assert result['actual'] == 987
        assert 'time' not in result


class TestInputStreamEMH:

    ## By declaring fixture with autouse=True, it will be automatically
    ## invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        ## before
        self.istream = io.StringIO()
        self.istream.write("""129-129:199.130.3*255#EMH#
1-0:0.0.9*255#12 34 45 56 67 78 90 12 34 45 #
1-0:1.8.0*255#1000.1#Wh
1-0:1.8.1*255#1111.1#Wh
1-0:1.8.2*255#1222.1#Wh
1-0:16.7.0*255#1.1#W
act_sensor_time#1#
129-129:199.130.3*255#EMH#
1-0:0.0.9*255#12 34 45 56 67 78 90 12 34 45 #
1-0:1.8.0*255#1000.2#Wh
1-0:1.8.1*255#1111.2#Wh
1-0:1.8.2*255#1222.2#Wh
1-0:16.7.0*255#2.2#W
act_sensor_time#2#
""")
        self.istream.seek(0)

        ## A test function will be run at this point
        yield

        ## after
        # ...

    def test_check_stream_packet_begin(self):
        assert stmp.check_stream_packet_begin(self.istream)

    def test_parse_stream(self):
        result = stmp.parse_stream(self.istream)
        assert result is not None and type(result) is dict, "Dict return value expected!"
        assert result['total'] == 1000.1
        assert result['actual'] == 1.1
        assert result['time'] == 1

        result = stmp.parse_stream(self.istream)
        assert result is not None and type(result) is dict, "Dict return value expected!"
        assert result['total'] == 1000.2
        assert result['actual'] == 2.2
        assert result['time'] == 2


class TestMqtt:

    def test_send_mqtt(self, monkeypatch):

        def connect_dummy(client, host, port=1883, keepalive=60, bind_address=""):
            print("CONNECT DUMMY", host, port)

        def publish_dummy(client, topic, payload=None, qos=0, retain=False):
            print(topic, payload)
            assert topic.startswith(stmp.MQTT_TOPIC_PREFIX)
            if topic == 'tele/smartmeter/time/first':
                assert payload == 111
            elif topic == 'tele/smartmeter/time/last':
                assert payload == 333
            elif topic == 'tele/smartmeter/total/value':
                assert payload == 3
            elif topic == 'tele/smartmeter/total/first':
                assert payload == 1
            elif topic == 'tele/smartmeter/total/last':
                assert payload == 3
            elif topic == 'tele/smartmeter/actual/first':
                assert payload == -11
            elif topic == 'tele/smartmeter/actual/last':
                assert payload == 99
            elif topic == 'tele/smartmeter/actual/median':
                assert payload == 16.5
            elif topic == 'tele/smartmeter/actual/mean':
                assert payload == 22
            elif topic == 'tele/smartmeter/actual/min':
                assert payload == -22
            elif topic == 'tele/smartmeter/actual/max':
                assert payload == 99

        ## monkey patching
        monkeypatch.setattr(stmp.mqtt.Client, "connect", connect_dummy)
        monkeypatch.setattr(stmp.mqtt.Client, "publish", publish_dummy)

        ## test data
        data = {
            'total': [1, 2, 3],
            'actual': [-11, -22, 11, 22, 33, 99],
            'act_sensor_time': [111, 222, 333]
        }
        config = ConfigParser()

        ## run / test
        mymqtt = stmp.MyMqtt(config)
        mymqtt.connected = True
        mymqtt.client = stmp.mqtt.Client()
        mymqtt.send_data(data)

    def test_construct_data(self):
        data = {
            'total': [1, 2, 3],
            'actual': [-11, -22, 11, 22, 33, 99],
            'time': [111, 222, 333]
        }
        config = ConfigParser()

        ## run / test
        mymqtt = stmp.MyMqtt(config)
        actual = mymqtt.construct_mqttdata(data)
        expected = {'time': {'first': 111, 'last': 333},
                    'total': {'value': 3, 'first': 1, 'last': 3, 'median': 2, 'mean': 2, 'min': 1, 'max': 3},
                    'actual': {'value': 99, 'first': -11, 'last': 99, 'median': 16.5, 'mean': 22, 'min': -22,
                               'max': 99}}
        assert actual == expected
