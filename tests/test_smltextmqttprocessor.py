#!pytest
# -*- coding: utf-8 -*-
"""Unit tests for smltextmqttprocessor.py, using pytest."""

import io
import json
from configparser import ConfigParser
import pytest
import smlmqttprocessor.smltextmqttprocessor as stmp


# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring, line-too-long
# noqa: D102


def test_convert_messages2records():
    """Test for converting message-dictionaries to a dictionary with value-lists"""
    messages = [{'a': 11, 'b': 12}, {'a': 21, 'b': 22}]
    expected = {'a': [11, 21], 'b': [12, 22]}
    actual = stmp.convert_messages2records(messages)
    assert actual == expected


class TestLibsmlParsing:
    """Tests for libSML-parsing."""

    def test_parse_line(self):
        assert isinstance(stmp.parse_line("act_sensor_time#1234#")[1], int)
        assert isinstance(stmp.parse_line("1-0:1.8.0*255#123.4#Wh")[1], float)

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
    """Tests for ISKRA smart meter SML."""

    TIMEOUT = 5

    # By declaring fixture with autouse=True, it will be automatically
    # invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        # before
        # pylint: disable=attribute-defined-outside-init
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

            1-0:96.50.1*1#ISK#
            1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
            1-0:1.8.0*255#110.1#Wh
            1-0:16.7.0*255#122.2#W
            act_sensor_time#3#

            1-0:96.50.1*1#ISK#
            1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
            1-0:1.8.0*255#120.1#Wh
            1-0:16.7.0*255#32.2#W
            act_sensor_time#4#

            1-0:96.50.1*1#ISK#
            1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
            1-0:1.8.0*255#125.1#Wh
            1-0:16.7.0*255#30.6#W
            act_sensor_time#5#
            """)
        self.istream.seek(0)

        # A test function will be run at this point
        yield

        # after
        # ...

    def test_processing_loop_window1(self):
        """Test main loop with a window size."""

        def messages_handler(messages):
            # this handler will be called n times for n messages in self.istream
            # because of window_size=1
            assert messages in ([{'actual': 1.1, 'time': 1, 'total': 10.1}],
                                [{'actual': 22.2, 'time': 2, 'total': 100.1}],
                                [{'actual': 122.2, 'time': 3, 'total': 110.1}],
                                [{'actual': 32.2, 'time': 4, 'total': 120.1}],
                                [{'actual': 30.6, 'time': 5, 'total': 125.1}])

        stmp.processing_loop(self.istream, 1, messages_handler, timeout=self.TIMEOUT)

    def test_processing_loop_window2(self):
        """Test main loop with a window size."""

        def messages_handler(messages):
            # this handler will be called 4/2+1=5 times for 5 messages in self.istream
            # because of window_size=2
            # pylint: disable=consider-using-in
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1},
                                {'actual': 22.2, 'time': 2, 'total': 100.1}] or \
                messages == [{'actual': 122.2, 'time': 3, 'total': 110.1},
                             {'actual': 32.2, 'time': 4, 'total': 120.1}] or \
                messages == [{'actual': 30.6, 'time': 5, 'total': 125.1}]

        stmp.processing_loop(self.istream, 2, messages_handler, timeout=self.TIMEOUT)

    def test_processing_loop_window99(self):
        """Test main loop with a window size."""

        def messages_handler(messages):
            # all messages are being accumulated because of big window size
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1},
                                {'actual': 22.2, 'time': 2, 'total': 100.1},
                                {'actual': 122.2, 'time': 3, 'total': 110.1},
                                {'actual': 32.2, 'time': 4, 'total': 120.1},
                                {'actual': 30.6, 'time': 5, 'total': 125.1}]

        stmp.processing_loop(self.istream, 99, messages_handler, timeout=self.TIMEOUT)

    def test_processing_loop_window2_delta50(self):
        """Test main loop with a window size and threshold-delta."""

        def messages_handler(messages):
            # 3 messages because of delta-threshold 122 >= 50, then the rest
            # => immediate threshold-based reaction
            # pylint: disable=consider-using-in
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1},
                                {'actual': 22.2, 'time': 2, 'total': 100.1},
                                {'actual': 122.2, 'time': 3, 'total': 110.1}] or \
                messages == [{'actual': 32.2, 'time': 4, 'total': 120.1},
                             {'actual': 30.6, 'time': 5, 'total': 125.1}]

        deltas = {"actual": 50}
        stmp.processing_loop(self.istream, 99, messages_handler,
                             timeout=self.TIMEOUT, deltas=deltas)

    def test_processing_loop_window2_delta200(self):
        """Test main loop with a window size and threshold-delta."""

        def messages_handler(messages):
            # all messages because of high delta-threshold
            # => no immediate (threshold-based) reaction
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1},
                                {'actual': 22.2, 'time': 2, 'total': 100.1},
                                {'actual': 122.2, 'time': 3, 'total': 110.1},
                                {'actual': 32.2, 'time': 4, 'total': 120.1},
                                {'actual': 30.6, 'time': 5, 'total': 125.1}]

        deltas = {"actual": 200}
        stmp.processing_loop(self.istream, 99, messages_handler,
                             timeout=self.TIMEOUT, deltas=deltas)

    def test_processing_loop_window2_delta10percent(self):
        """Test main loop with a window size and threshold-delta."""

        def messages_handler(messages):
            # this handler will be called 3 times because of 10 % delta and 2 changes
            # pylint: disable=consider-using-in
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1},
                                {'actual': 22.2, 'time': 2, 'total': 100.1}] or \
                messages == [{'actual': 122.2, 'time': 3, 'total': 110.1},
                             {'actual': 32.2, 'time': 4, 'total': 120.1}] or \
                messages == [{'actual': 30.6, 'time': 5, 'total': 125.1}]

        deltas = {"actual": 0.1}
        stmp.processing_loop(self.istream, 99, messages_handler,
                             timeout=self.TIMEOUT, deltas=deltas)

    def test_processing_invalid_delta_field_name(self):
        """Test main loop with a window size and threshold-delta."""

        def messages_handler(messages):
            # invalid delta field-name => no filtering based on delta
            # => return all messages (because of big window size)
            assert messages == [{'actual': 1.1, 'time': 1, 'total': 10.1},
                                {'actual': 22.2, 'time': 2, 'total': 100.1},
                                {'actual': 122.2, 'time': 3, 'total': 110.1},
                                {'actual': 32.2, 'time': 4, 'total': 120.1},
                                {'actual': 30.6, 'time': 5, 'total': 125.1}]

        deltas = {"ISINVALID": 1}
        stmp.processing_loop(self.istream, 99, messages_handler,
                             timeout=self.TIMEOUT, deltas=deltas)

    def test_processing_loop_invalid(self):
        """Test main loop with invalid data."""
        # before
        istream = io.StringIO()
        istream.write("""1-0:96.50.1*1#ISK#
            1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
            1-0:1.8.0*255#10Wh
            1-0:16.7.0*255#1.1#W
            act_sensor_time#1#
            """)
        istream.seek(0)

        def messages_handler(messages):
            assert len(messages) == 1
            assert messages == [{'actual': 1.1, 'time': 1}]

        stmp.processing_loop(istream, 2, messages_handler, timeout=2)


class TestLibsmlParsingEMH:
    """Tests for EMH smart meter SML."""

    # By declaring fixture with autouse=True, it will be automatically
    # invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        # before
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

        # A test function will be run at this point
        yield

        # after
        # ...

    def test_processing_loop_window2(self):
        def messages_handler(messages):
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
            # pylint: disable=consider-using-in
            assert messages == [{'time': 118137421,
                                 'total': 5378499.0,
                                 'total_tariff1': 5378499.0,
                                 'total_tariff2': 0.0}] or \
                messages == [{'time': 118137423, 'total': 5378499.1,
                              'total_tariff1': 5378499.1, 'total_tariff2': 0.0}]

        stmp.processing_loop(self.istream, 1, messages_handler, timeout=2)

    def test_processing_loop_invalid(self):
        # before
        istream = io.StringIO()
        istream.write("""129-129:199.130.3*255#EMH#
            1-0:1.8.0*255#5378499.0Wh
            1-0:16.7.0*255#1.1#W
            act_sensor_time#1#
            """)
        istream.seek(0)

        def messages_handler(messages):
            assert len(messages) == 1
            assert messages == [{'actual': 1.1, 'time': 1}]

        stmp.processing_loop(istream, 2, messages_handler, timeout=2)


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

        # monkey patching
        monkeypatch.setattr(stmp.mqtt.Client, "connect", connect_dummy)
        monkeypatch.setattr(stmp.mqtt.Client, "publish", publish_dummy)

        # test data
        data = {
            'total': [1, 2, 3],
            'actual': [-11, -22, 11, 22, 33, 99],
            'act_sensor_time': [111, 222, 333]
        }
        config = ConfigParser()

        # run / test
        mymqtt = stmp.MyMqtt(config)
        mymqtt.connected = True
        mymqtt.client = stmp.mqtt.Client()
        mymqtt.send(data)

    def test_construct_data(self):
        data = {
            'total': [1.111, 2.222, 3.333],
            'actual': [-11.1, -22.2, 11.1, 22.2, 33.3, 99.9],
            'time': [111.1, 222.2, 333.3]
        }
        config = ConfigParser()

        # run / test
        mymqtt = stmp.MyMqtt(config)
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

        # monkey patching
        monkeypatch.setattr(stmp.mqtt.Client, "connect", connect_dummy)
        monkeypatch.setattr(stmp.mqtt.Client, "publish", publish_dummy)

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
        mymqtt = stmp.MyMqtt(config)
        mymqtt.connected = True
        mymqtt.client = stmp.mqtt.Client()
        mymqtt.send(data)
