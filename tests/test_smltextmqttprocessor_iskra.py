#!pytest
# -*- coding: utf-8 -*-
"""Unit tests for smltextmqttprocessor.py, specialized for ISKRA smart meter."""

import io
import pytest

import smlmqttprocessor.smltextmqttprocessor as stmp


# f-string does not work with Python 3.5
# pylint: disable=consider-using-f-string

# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring, line-too-long
# noqa: D102


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
