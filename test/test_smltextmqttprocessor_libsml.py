#!pytest
# -*- coding: utf-8 -*-
"""
Run-time tests for smltextmqttprocessor.py,
using pytest and libsml's sml_server_time.
"""

import logging
import os
import shlex
from glob import iglob
from subprocess import Popen, PIPE
import pytest
import smltextmqttprocessor as stmp

# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

# no docstring for tests
# pylint: disable=missing-function-docstring
# noqa: D102

__script_dir = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(name)-10s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

N = 0


def __processfile(filepath, window_size):
    global N

    # reset counter
    N = 0

    # aggregation callback
    def data_handler(_):
        # just count how often this has been called
        global N
        N += 1

    # call external binary and capture STDOUT
    cmd = "%s %s" % (os.path.join(__script_dir, '../sml_server_time/sml_server_time'), filepath)
    with Popen(shlex.split(cmd), stdout=PIPE) as proc:
        stmp.processing_loop(proc.stdout, window_size, data_handler, timeout=1)

    return N


def test_processing_loop_exampledatafiles_window1():
    """
    Test all *.bin files for window_size=1
    """
    files2n = {
        './testdata/EMH_eHZ-GW8E2A500AK2.bin': 16,
        './testdata/EMH_eHZ-HW8E2AWL0EK2P.bin': 13,
        './testdata/EMH_eHZ-IW8E2AWL0EK2P.bin': 12,
        './testdata/ISKRA_MT175_eHZ.bin': 10,
        './testdata/ISKRA_MT691_eHZ-MS2020.bin': 18
    }
    for filepath in iglob(os.path.join(__script_dir, '*.bin')):
        print(filepath)
        filename = os.path.basename(filepath)
        actual = __processfile(filepath, window_size=1)
        expected = files2n[filename]
        assert actual == expected, "Number mismatch for %s" % filename


def test_processing_loop_exampledatafiles_window2():
    """
    Test all *.bin files for window_size=2
    """
    files2n = {
        './testdata/EMH_eHZ-GW8E2A500AK2.bin': 8,
        './testdata/EMH_eHZ-HW8E2AWL0EK2P.bin': 7,
        './testdata/EMH_eHZ-IW8E2AWL0EK2P.bin': 6,
        './testdata/ISKRA_MT175_eHZ.bin': 5,
        './testdata/ISKRA_MT691_eHZ-MS2020.bin': 9
    }
    for filepath in iglob(os.path.join(__script_dir, '*.bin')):
        print(filepath)
        filename = os.path.basename(filepath)
        actual = __processfile(filepath, window_size=2)
        expected = files2n[filename]
        assert actual == expected, "Number mismatch for %s" % filename


def test_processing_loop_exampledatafiles_window15():
    """
    Test all *.bin files for window_size=15
    """
    files2n = {
        './testdata/EMH_eHZ-GW8E2A500AK2.bin': 2,
        './testdata/EMH_eHZ-HW8E2AWL0EK2P.bin': 1,
        './testdata/EMH_eHZ-IW8E2AWL0EK2P.bin': 1,
        './testdata/ISKRA_MT175_eHZ.bin': 1,
        './testdata/ISKRA_MT691_eHZ-MS2020.bin': 2
    }
    for filepath in iglob(os.path.join(__script_dir, '*.bin')):
        print(filepath)
        filename = os.path.basename(filepath)
        actual = __processfile(filepath, window_size=15)
        expected = files2n[filename]
        assert actual == expected, "Number mismatch for %s" % filename


if __name__ == '__main__':
    pytest.main()
