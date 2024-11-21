#!pytest
# -*- coding: utf-8 -*-
"""Unit tests for smltextmqttprocessor.py, using pytest."""

import pytest

import smlmqttprocessor.smltextmqttprocessor as stmp


# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring, line-too-long
# noqa: D102


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
