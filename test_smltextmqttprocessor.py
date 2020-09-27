#!pytest
# -*- coding: utf-8 -*-
"""
Unit tests for smltextmqttprocessor.py, using pytest.
"""

import io
import pytest
import smltextmqttprocessor as stmp
from configparser import ConfigParser


def test_convert_messages2records():
    messages = [{'a': 11, 'b': 12}, {'a': 21, 'b': 22}]
    expected = {'a': [11, 21], 'b': [12, 22]}
    actual = stmp.convert_messages2records(messages)
    assert actual == expected


class TestLibsmlParsing:

    def test_parse_line(self):
        assert type(stmp.parse_line("act_sensor_time#1234#")[1]) is int
        assert type(stmp.parse_line("1-0:1.8.0*255#123.4#Wh")[1]) is float

        assert stmp.parse_line("1-0:1.8.0*255#123.4#Wh") == ('total', 123.4)
        assert stmp.parse_line("1-0:1.8.1*255#123.4#Wh") == ('total_tariff1', 123.4)
        assert stmp.parse_line("1-0:1.8.2*255#123.4#Wh") == ('total_tariff2', 123.4)
        assert stmp.parse_line("1-0:1.8.3*255#123.4#Wh") == ('total_tariff3', 123.4)
        assert stmp.parse_line("1-0:1.8.4*255#123.4#Wh") == ('total_tariff4', 123.4)

        assert stmp.parse_line("1-0:2.8.0*255#123.4#Wh") == ('total_export', 123.4)
        assert stmp.parse_line("1-0:2.8.1*255#123.4#Wh") == ('total_export_tariff1', 123.4)
        assert stmp.parse_line("1-0:2.8.2*255#123.4#Wh") == ('total_export_tariff2', 123.4)
        assert stmp.parse_line("1-0:2.8.3*255#123.4#Wh") == ('total_export_tariff3', 123.4)
        assert stmp.parse_line("1-0:2.8.4*255#123.4#Wh") == ('total_export_tariff4', 123.4)

        assert stmp.parse_line("1-0:1.7.0*255#123.4#Wh") == ('actual_170', 123.4)
        assert stmp.parse_line("1-0:16.7.0*255#123.4#Wh") == ('actual', 123.4)
        assert stmp.parse_line("1-0:36.7.0*255#123.4#Wh") == ('actual_l1', 123.4)
        assert stmp.parse_line("1-0:56.7.0*255#123.4#Wh") == ('actual_l2', 123.4)
        assert stmp.parse_line("1-0:76.7.0*255#123.4#Wh") == ('actual_l3', 123.4)

        assert stmp.parse_line("act_sensor_time#1234#") == ('time', 1234)

        assert stmp.parse_line("act_sensor_time#foobar#") == ('time', 'foobar')
        assert stmp.parse_line("x#1234#") is None
        assert stmp.parse_line("") is None
        assert stmp.parse_line(None) is None

    def test_parse_line_invalid(self):
        with pytest.raises(ValueError):
            stmp.parse_line('1-0:2.8.0*255')
        with pytest.raises(ValueError):
            stmp.parse_line('1-0:2.8.0*255#1')
        with pytest.raises(ValueError):
            stmp.parse_line('1-0:2.8.0*255#foo')

    def test_check_stream_packet_begin(self):
        assert stmp.check_stream_packet_begin('1-0:96.50.1*1#ISK#')
        assert stmp.check_stream_packet_begin('129-129:199.130.3*255#')

    def test_check_stream_packet_begin_empty(self):
        assert not stmp.check_stream_packet_begin('')

    def test_check_stream_packet_begin_noheader(self):
        assert not stmp.check_stream_packet_begin('foobar')


class TestLibsmlParsingISKRA:

    ## By declaring fixture with autouse=True, it will be automatically
    ## invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        ## before
        self.istream = io.StringIO()
        self.istream.write("""1-0:96.50.1*1#ISK#
            1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
            1-0:1.8.0*255#10.1#Wh
            1-0:16.7.0*255#1.1#W
            act_sensor_time#1#
        
            1-0:96.50.1*1#ISK#
            1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
            1-0:1.8.0*255#100.1#Wh
            1-0:16.7.0*255#22.2#W
            act_sensor_time#2#
            """)
        self.istream.seek(0)

        ## A test function will be run at this point
        yield

        ## after
        # ...

    def test_processing_loop_window2(self):
        def messages_handler(messages):
            print(messages)
            assert len(messages) == 2
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1}, {'actual': 22.2, 'time': 2, 'total': 100.1}]

        stmp.processing_loop(self.istream, 2, messages_handler, timeout=2)

    def test_processing_loop_window1(self):
        def messages_handler(messages):
            print(messages)
            assert len(messages) == 1
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1}] or \
                   messages == [{'actual': 22.2, 'time': 2, 'total': 100.1}]

        stmp.processing_loop(self.istream, 1, messages_handler, timeout=2)

    def test_processing_loop_invalid(self):
        ## before
        istream = io.StringIO()
        istream.write("""1-0:96.50.1*1#ISK#
            1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
            1-0:1.8.0*255#10Wh
            1-0:16.7.0*255#1.1#W
            act_sensor_time#1#
            """)
        istream.seek(0)

        def messages_handler(messages):
            print(messages)
            assert len(messages) == 1
            assert messages == [{'actual': 1.1, 'time': 1}]

        stmp.processing_loop(istream, 2, messages_handler, timeout=2)


class TestLibsmlParsingEMH:

    ## By declaring fixture with autouse=True, it will be automatically
    ## invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        ## before
        self.istream = io.StringIO()
        self.istream.write("""129-129:199.130.3*255#EMH#
            1-0:0.0.9*255#01 a8 15 98 64 80 02 01 02 #
            1-0:1.8.0*255#5378499.0#Wh
            1-0:1.8.1*255#5378499.0#Wh
            1-0:1.8.2*255#0.0#Wh
            1-0:15.7.0*255#191.9#W
            129-129:199.130.5*255#c2 fb 28 83 40 2a d8 7c 9e a2 7a cc fd 04 28 20 6f bd 06 56 6b a7 95 7c 5e b0 de 50 54 a4 40 ab d5 5a 6d 94 d6 77 17 6f dd f8 05 c2 3f 8d ef 1e #
            act_sensor_time#118137421#
            129-129:199.130.3*255#EMH#
            1-0:0.0.9*255#01 a8 15 98 64 80 02 01 02 #
            1-0:1.8.0*255#5378499.1#Wh
            1-0:1.8.1*255#5378499.1#Wh
            1-0:1.8.2*255#0.0#Wh
            1-0:15.7.0*255#190.2#W
            129-129:199.130.5*255#c2 fb 28 83 40 2a d8 7c 9e a2 7a cc fd 04 28 20 6f bd 06 56 6b a7 95 7c 5e b0 de 50 54 a4 40 ab d5 5a 6d 94 d6 77 17 6f dd f8 05 c2 3f 8d ef 1e #
            act_sensor_time#118137423#
            """)
        self.istream.seek(0)

        ## A test function will be run at this point
        yield

        ## after
        # ...

    def test_processing_loop_window2(self):
        def messages_handler(messages):
            print(messages)
            assert len(messages) == 2
            assert messages == [{'time': 118137421,
                                 'total': 5378499.0,
                                 'total_tariff1': 5378499.0,
                                 'total_tariff2': 0.0},
                                {'time': 118137423,
                                 'total': 5378499.1,
                                 'total_tariff1': 5378499.1,
                                 'total_tariff2': 0.0}]

        stmp.processing_loop(self.istream, 2, messages_handler, timeout=2)

    def test_processing_loop_window1(self):
        def messages_handler(messages):
            print(messages)
            assert len(messages) == 1
            assert messages == [{'time': 118137421,
                                 'total': 5378499.0,
                                 'total_tariff1': 5378499.0,
                                 'total_tariff2': 0.0}] \
                   or messages == [{'time': 118137423,
                                    'total': 5378499.1,
                                    'total_tariff1': 5378499.1,
                                    'total_tariff2': 0.0}]

        stmp.processing_loop(self.istream, 1, messages_handler, timeout=2)

    def test_processing_loop_invalid(self):
        ## before
        istream = io.StringIO()
        istream.write("""129-129:199.130.3*255#EMH#
            1-0:1.8.0*255#5378499.0Wh
            1-0:16.7.0*255#1.1#W
            act_sensor_time#1#
            """)
        istream.seek(0)

        def messages_handler(messages):
            print(messages)
            assert len(messages) == 1
            assert messages == [{'actual': 1.1, 'time': 1}]

        stmp.processing_loop(istream, 2, messages_handler, timeout=2)


class TestMqtt:

    def test_send_mqtt(self, monkeypatch):

        def connect_dummy(client, host, port=1883, keepalive=60, bind_address=""):
            print("CONNECT DUMMY", host, port)

        def publish_dummy(client, topic, payload=None, qos=0, retain=False):
            print(topic, payload)
            assert topic.startswith('tele/smartmeter')
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
