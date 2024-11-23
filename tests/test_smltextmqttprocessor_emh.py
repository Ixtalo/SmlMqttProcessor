#!pytest
# -*- coding: utf-8 -*-
"""Unit tests for smltextmqttprocessor.py, specialized for EMH smart meter."""

import io
import pytest

import smlmqttprocessor.smltextmqttprocessor as stmp


# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring,  missing-class-docstring
# pylint: disable=line-too-long, too-few-public-methods
# noqa: D102


class TestLibsmlParsingEMH:
    """Tests for EMH smart meter SML."""

    # By declaring fixture with autouse=True, it will be automatically
    # invoked for each test function defined in the same module.
    @pytest.fixture(autouse=True)
    def run_around_tests(self):
        # before
        self.istream = io.StringIO()    # pylint: disable=attribute-defined-outside-init
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
