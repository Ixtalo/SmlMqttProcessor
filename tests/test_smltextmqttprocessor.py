#!pytest
# -*- coding: utf-8 -*-
"""Unit tests for smltextmqttprocessor.py, using pytest."""
import sys
import types
from pathlib import Path

import docopt
import pytest

import smlmqttprocessor.smltextmqttprocessor as stmp
from smlmqttprocessor.smltextmqttprocessor import main


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


class TestMain:

    @staticmethod
    def test_noargs(monkeypatch):
        monkeypatch.setattr(sys, "argv", ["_"])
        with pytest.raises(docopt.DocoptExit):
            main()

    @staticmethod
    def test_noinputfile(monkeypatch):
        monkeypatch.setattr(sys, "argv", ["_", "doesnotexistfile"])
        with pytest.raises(FileNotFoundError):
            main()

    @staticmethod
    def test_testdataIskra(monkeypatch, capsys):
        testdata_filepath = Path(__file__).parent.parent.joinpath("tests/testdata/ISKRA_MT175_eHZ.txt")
        monkeypatch.setattr(sys, "argv",
                            [
                                "_",
                                "--no-mqtt",
                                "--timeout=1",
                                "--window=5",
                                str(testdata_filepath.resolve())
                            ])
        # action
        main()
        # check
        stdout, stderr = capsys.readouterr()
        assert stderr == ""
        assert stdout == ('mqttdata:\n'
                          "{'actual': {'first': 168,\n"
                          "            'last': 168,\n"
                          "            'max': 173,\n"
                          "            'mean': 169.6,\n"
                          "            'median': 168,\n"
                          "            'min': 168,\n"
                          "            'stdev': 2.3,\n"
                          "            'value': 168},\n"
                          " 'actual_l1': {'first': 117,\n"
                          "               'last': 117,\n"
                          "               'max': 119,\n"
                          "               'mean': 117.6,\n"
                          "               'median': 117,\n"
                          "               'min': 117,\n"
                          "               'stdev': 0.9,\n"
                          "               'value': 117},\n"
                          " 'actual_l2': {'first': 22,\n"
                          "               'last': 22,\n"
                          "               'max': 22,\n"
                          "               'mean': 21.8,\n"
                          "               'median': 22,\n"
                          "               'min': 21,\n"
                          "               'stdev': 0.4,\n"
                          "               'value': 22},\n"
                          " 'actual_l3': {'first': 29,\n"
                          "               'last': 28,\n"
                          "               'max': 32,\n"
                          "               'mean': 29.4,\n"
                          "               'median': 29,\n"
                          "               'min': 28,\n"
                          "               'stdev': 1.5,\n"
                          "               'value': 28},\n"
                          " 'time': {'first': 128972252, 'last': 128972260, 'value': 128972260},\n"
                          " 'total': {'first': 22462413.6, 'last': 22462414.0, 'value': 22462414.0},\n"
                          " 'total_tariff1': {'first': 22462413.6,\n"
                          "                   'last': 22462414.0,\n"
                          "                   'max': 22462414.0,\n"
                          "                   'mean': 22462413.8,\n"
                          "                   'median': 22462413.8,\n"
                          "                   'min': 22462413.6,\n"
                          "                   'stdev': 0.2,\n"
                          "                   'value': 22462414.0},\n"
                          " 'total_tariff2': {'first': 0.0,\n"
                          "                   'last': 0.0,\n"
                          "                   'max': 0.0,\n"
                          "                   'mean': 0.0,\n"
                          "                   'median': 0.0,\n"
                          "                   'min': 0.0,\n"
                          "                   'stdev': 0.0,\n"
                          "                   'value': 0.0}}\n"
                          'mqttdata:\n'
                          "{'actual': {'first': 170,\n"
                          "            'last': 169,\n"
                          "            'max': 171,\n"
                          "            'mean': 170.2,\n"
                          "            'median': 170,\n"
                          "            'min': 169,\n"
                          "            'stdev': 0.8,\n"
                          "            'value': 169},\n"
                          " 'actual_l1': {'first': 117,\n"
                          "               'last': 118,\n"
                          "               'max': 119,\n"
                          "               'mean': 118.2,\n"
                          "               'median': 118,\n"
                          "               'min': 117,\n"
                          "               'stdev': 0.8,\n"
                          "               'value': 118},\n"
                          " 'actual_l2': {'first': 23,\n"
                          "               'last': 22,\n"
                          "               'max': 23,\n"
                          "               'mean': 22.2,\n"
                          "               'median': 22,\n"
                          "               'min': 21,\n"
                          "               'stdev': 0.8,\n"
                          "               'value': 22},\n"
                          " 'actual_l3': {'first': 29,\n"
                          "               'last': 28,\n"
                          "               'max': 30,\n"
                          "               'mean': 29,\n"
                          "               'median': 29,\n"
                          "               'min': 28,\n"
                          "               'stdev': 0.7,\n"
                          "               'value': 28},\n"
                          " 'time': {'first': 128972262, 'last': 128972270, 'value': 128972270},\n"
                          " 'total': {'first': 22462414.1, 'last': 22462414.5, 'value': 22462414.5},\n"
                          " 'total_tariff1': {'first': 22462414.1,\n"
                          "                   'last': 22462414.5,\n"
                          "                   'max': 22462414.5,\n"
                          "                   'mean': 22462414.3,\n"
                          "                   'median': 22462414.3,\n"
                          "                   'min': 22462414.1,\n"
                          "                   'stdev': 0.2,\n"
                          "                   'value': 22462414.5},\n"
                          " 'total_tariff2': {'first': 0.0,\n"
                          "                   'last': 0.0,\n"
                          "                   'max': 0.0,\n"
                          "                   'mean': 0.0,\n"
                          "                   'median': 0.0,\n"
                          "                   'min': 0.0,\n"
                          "                   'stdev': 0.0,\n"
                          "                   'value': 0.0}}\n")
