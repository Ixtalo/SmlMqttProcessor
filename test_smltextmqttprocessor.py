#!pytest
# -*- coding: utf-8 -*-

import io
import pytest
import smltextmqttprocessor as stmp


class TestInputStream:

    ## By declaring fixture with autouse=True, it will be automatically
    ## invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        ## before
        self.istream = io.StringIO()
        self.istream.write("""1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#12345#Wh
1-0:16.7.0*255#987#W
act_sensor_time#1234567#
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

    def test_sml_getvalue_heuristic_powertotal(self):
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        assert '12345' == stmp.sml_getvalue_heuristic(self.istream, stmp.SML_POWER_TOTAL)

    def test_sml_getvalue_heuristic_powertotal_wrongpos(self):
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        ## ONE MOVEMENT MISSING FOR TESTING...
        assert not stmp.sml_getvalue_heuristic(self.istream, stmp.SML_POWER_TOTAL)

    def test_sml_getvalue_heuristic_powertotal_wrongDelimiters(self):
        istream = io.StringIO()
        istream.write("""1-0:96.50.1*1#ISK#
1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#12345
1-0:16.7.0*255#26#W""")
        istream.seek(0)
        istream.readline()  ## nothing to be done with, just for moving forward in stream
        istream.readline()  ## nothing to be done with, just for moving forward in stream
        with pytest.raises(ValueError) as ex:
            stmp.sml_getvalue_heuristic(istream, stmp.SML_POWER_TOTAL)
        assert "not enough values to unpack (expected 3, got 2)" in str(ex)

    def test_sml_getvalue_heuristic_poweractual(self):
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        assert '987' == stmp.sml_getvalue_heuristic(self.istream, stmp.SML_POWER_ACTUAL)

    def test_sml_getvalue_heuristic_poweractual_wrongpos(self):
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        ## ONE MOVEMENT MISSING FOR TESTING...
        assert not stmp.sml_getvalue_heuristic(self.istream, stmp.SML_POWER_ACTUAL)

    def test_sml_getvalue_heuristic_sensortime(self):
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        assert '1234567' == stmp.sml_getvalue_heuristic(self.istream, stmp.SML_SENSOR_TIME)

    def test_sml_getvalue_heuristic_sensortime_wrongpos(self):
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        ## ONE MOVEMENT MISSING FOR TESTING...
        assert not stmp.sml_getvalue_heuristic(self.istream, stmp.SML_SENSOR_TIME)

    def test_parse_stream(self):
        a_total = []
        a_actual = []
        a_times = []
        self.istream.readline()  ## nothing to be done with, just for moving forward in stream
        res = stmp.parse_stream(self.istream, a_times, a_total, a_actual)
        assert "No return value expected!", res is None
        assert [12345.0] == a_total
        assert [987.0] == a_actual
        assert [1234567] == a_times

    def test_parse_stream_nopowertotal(self):
        istream = io.StringIO()
        istream.write("""1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:16.7.0*255#987#W
act_sensor_time#1234567#""")
        istream.seek(0)
        a_total = []
        a_actual = []
        a_times = []
        stmp.parse_stream(istream, a_times, a_total, a_actual)
        assert [] == a_total
        assert [987.0] == a_actual
        assert [1234567] == a_times

    def test_parse_stream_nopoweractual(self):
        istream = io.StringIO()
        istream.write("""1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#12345#Wh
act_sensor_time#1234567#""")
        istream.seek(0)
        a_total = []
        a_actual = []
        a_times = []
        stmp.parse_stream(istream, a_times, a_total, a_actual)
        assert [12345.0] == a_total
        assert [] == a_actual
        assert [1234567] == a_times

    def test_parse_stream_notime(self):
        istream = io.StringIO()
        istream.write("""1-0:96.1.0*255#0a 01 49 53 4b 00 04 32 5e c5 #
1-0:1.8.0*255#12345#Wh
1-0:16.7.0*255#987#W""")
        istream.seek(0)
        a_total = []
        a_actual = []
        a_times = []
        stmp.parse_stream(istream, a_times, a_total, a_actual)
        assert [12345.0] == a_total
        assert [987.0] == a_actual
        assert [] == a_times


class TestMqtt:

    def test_send_mqtt(self, monkeypatch):
        client = stmp.mqtt.Client()

        def publish_dummy(_, topic, payload=None, qos=0, retain=False):
            print(topic, payload)
            assert topic.startswith(stmp.MQTT_TOPIC_PREFIX)
            if topic == 'tele/smartmeter/time/first':
                assert payload == 111
            elif topic == 'tele/smartmeter/time/last':
                assert payload == 333
            elif topic == 'tele/smartmeter/power/total/value':
                assert payload == 3
            elif topic == 'tele/smartmeter/power/actual/first':
                assert payload == -11
            elif topic == 'tele/smartmeter/power/actual/last':
                assert payload == 99
            elif topic == 'tele/smartmeter/power/actual/median':
                assert payload == 16.5
            elif topic == 'tele/smartmeter/power/actual/mean':
                assert payload == 22
            elif topic == 'tele/smartmeter/power/actual/min':
                assert payload == -22
            elif topic == 'tele/smartmeter/power/actual/max':
                assert payload == 99

        monkeypatch.setattr(stmp.mqtt.Client, "publish", publish_dummy)

        a_total = [1, 2, 3]
        a_actual = [-11, -22, 11, 22, 33, 99]
        a_times = [111, 222, 333]
        stmp.send_mqtt(client, a_times, a_total, a_actual)