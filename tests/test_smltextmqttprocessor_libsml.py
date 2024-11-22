#!pytest
# -*- coding: utf-8 -*-
"""
Run-time tests for smltextmqttprocessor.py,
using pytest and libsml's sml_server_time.
"""

import logging
import shlex
from pathlib import Path
from subprocess import Popen, PIPE

import pytest

import smlmqttprocessor.smltextmqttprocessor as stmp

# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring,  missing-class-docstring
# pylint: disable=line-too-long, too-few-public-methods
# noqa: D102

script_dir = Path(__file__).parent

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(name)-10s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# counter how often processfile() has been called
counter_processfile = 0


@pytest.fixture
def testdata_files():
    # find all binary testdata files
    return list(script_dir.joinpath('testdata').glob("*.bin"))


def __processfile(filepath, window_size):
    global counter_processfile

    # reset counter
    counter_processfile = 0

    # aggregation callback
    def data_handler(_):
        # just count how often this has been called
        global counter_processfile
        counter_processfile += 1

    # call external binary and capture STDOUT
    # the binary (sml_server_time) parses the binary files and produces text output
    cmd = "%s %s" % (script_dir.joinpath('../sml_server_time/sml_server_time'), filepath)
    with Popen(shlex.split(cmd), stdout=PIPE) as proc:
        stmp.processing_loop(proc.stdout, window_size, data_handler, timeout=1)

    return counter_processfile


@pytest.mark.parametrize(
    "input_value,expected_numbers",
    [
        (1, {
            'EMH_eHZ-GW8E2A500AK2.bin': 16,
            'EMH_eHZ-HW8E2AWL0EK2P.bin': 13,
            'EMH_eHZ-IW8E2AWL0EK2P.bin': 12,
            'ISKRA_MT175_eHZ.bin': 10,
            'ISKRA_MT691_eHZ-MS2020.bin': 18
        }),
        (2, {
            'EMH_eHZ-GW8E2A500AK2.bin': 8,
            'EMH_eHZ-HW8E2AWL0EK2P.bin': 7,
            'EMH_eHZ-IW8E2AWL0EK2P.bin': 6,
            'ISKRA_MT175_eHZ.bin': 5,
            'ISKRA_MT691_eHZ-MS2020.bin': 9
        }),
        (15, {
            'EMH_eHZ-GW8E2A500AK2.bin': 2,
            'EMH_eHZ-HW8E2AWL0EK2P.bin': 1,
            'EMH_eHZ-IW8E2AWL0EK2P.bin': 1,
            'ISKRA_MT175_eHZ.bin': 1,
            'ISKRA_MT691_eHZ-MS2020.bin': 2
        }),
    ]
)
def test_processing_loop(testdata_files, input_value, expected_numbers):
    """
    Test all *.bin files for window_size=15
    """
    # make sure this test actually runs with all files
    assert len(testdata_files) == 5
    # action
    for filepath in testdata_files:
        print(filepath)
        # action
        actual = __processfile(filepath, window_size=input_value)
        # check
        expected = expected_numbers[filepath.name]
        assert actual == expected, "Number mismatch for %s" % filepath.resolve()
