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

__script_dir = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(name)-10s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

n = 0


def __processfile(filepath, window_size):
    global n

    ## call external binary and capture STDOUT
    cmd = "%s %s" % (os.path.join(__script_dir, './sml_server_time/sml_server_time'), filepath)
    proc = Popen(shlex.split(cmd), stdout=PIPE)

    ## reset counter
    n = 0

    ## aggregation callback
    def data_handler(data):
        ## just count how often this has been called
        global n
        n += 1

    stmp.processing_loop(proc.stdout, window_size, data_handler, timeout=1)

    return n


def test_processing_loop_exampledatafiles_window1():
    """
    Test all *.bin files for window_size=1
    """
    files2n = {
        'EMH_eHZ-GW8E2A500AK2.bin': 16,
        'EMH_eHZ-HW8E2AWL0EK2P.bin': 13,
        'EMH_eHZ-IW8E2AWL0EK2P.bin': 12,
        'ISKRA_MT175_eHZ.bin': 10,
        'ISKRA_MT691_eHZ-MS2020.bin': 18
    }
    for filepath in iglob(os.path.join(__script_dir, 'example_data/*.bin')):
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
        'EMH_eHZ-GW8E2A500AK2.bin': 8,
        'EMH_eHZ-HW8E2AWL0EK2P.bin': 7,
        'EMH_eHZ-IW8E2AWL0EK2P.bin': 6,
        'ISKRA_MT175_eHZ.bin': 5,
        'ISKRA_MT691_eHZ-MS2020.bin': 9
    }
    for filepath in iglob(os.path.join(__script_dir, 'example_data/*.bin')):
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
        'EMH_eHZ-GW8E2A500AK2.bin': 2,
        'EMH_eHZ-HW8E2AWL0EK2P.bin': 1,
        'EMH_eHZ-IW8E2AWL0EK2P.bin': 1,
        'ISKRA_MT175_eHZ.bin': 1,
        'ISKRA_MT691_eHZ-MS2020.bin': 2
    }
    for filepath in iglob(os.path.join(__script_dir, 'example_data/*.bin')):
        print(filepath)
        filename = os.path.basename(filepath)
        actual = __processfile(filepath, window_size=15)
        expected = files2n[filename]
        assert actual == expected, "Number mismatch for %s" % filename


if __name__ == '__main__':
    pytest.main()
