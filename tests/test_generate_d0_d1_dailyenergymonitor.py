#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests."""
import logging
from datetime import datetime, timedelta

import generate_d0_d1
from generate_d0_d1 import (
    DailyEnergyMonitor,
    handle_smartmeter_message,
    handle_retained_dx_message,
    MQTT_TOPIC_D0,
    MQTT_TOPIC_D1
)


# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring,  missing-class-docstring
# pylint: disable=line-too-long, too-few-public-methods
# noqa: D102


class TestDailyEnergyMonitorConstructor:
    """Tests for constructor."""

    @staticmethod
    def test_constructor():
        instance = DailyEnergyMonitor()
        assert instance.retain
        assert not instance.data  # it is []
        assert instance.d0 is None
        assert instance.d1 is None
        assert instance.current_date == datetime.now().date()

    @staticmethod
    def test_constructor_retain_false():
        instance = DailyEnergyMonitor(retain=False)
        assert not instance.retain


class TestDailyEnergyMonitorAddValue:
    """Tests for add_value."""

    @staticmethod
    def test_today():
        # action
        instance = DailyEnergyMonitor()
        instance.add_value(100)
        instance.add_value(200)
        instance.add_value(300)
        # check
        assert len(instance.data) == 3
        assert instance.d0 == 300 - 100
        assert not instance.d1
        instance.add_value(330)
        assert instance.d0 == 330 - 100
        instance.add_value(350)
        assert instance.d0 == 350 - 100

    @staticmethod
    def test_only1entry(caplog):
        # action
        with caplog.at_level(logging.DEBUG):
            instance = DailyEnergyMonitor()
            instance.add_value(1111)
        # check
        assert len(instance.data) == 1
        assert instance.d0 is None
        assert instance.d1 is None
        assert caplog.text == ('DEBUG    root:generate_d0_d1.py:74 new size of data[] is 1\n'
                               'DEBUG    root:generate_d0_d1.py:86 d0 delta: not enough data yet\n')

    @staticmethod
    def test_retain(caplog):
        # action
        with caplog.at_level(logging.DEBUG):
            instance = DailyEnergyMonitor()
            instance.d0_retained = 444
            instance.add_value(100)
            instance.add_value(200)
            instance.add_value(300)
        # check
        assert len(instance.data) == 3
        assert instance.d0 == 300 - 100 + 444
        assert not instance.d1
        instance.add_value(330)
        assert instance.d0 == 330 - 100 + 444
        instance.add_value(350)
        assert instance.d0 == 350 - 100 + 444

    @staticmethod
    def test_yesterday(monkeypatch, caplog):
        caplog.set_level(logging.DEBUG)
        # action
        instance = DailyEnergyMonitor()
        instance.add_value(100)
        instance.add_value(500)
        # check
        assert instance.d0 == 400  # difference 500-100=400
        assert instance.d1 is None
        assert instance.d0_retained is None
        assert instance.d1_retained is None
        # now mock the new day
        monkeypatch.setattr(DailyEnergyMonitor, "_check_is_new_day", lambda _, __: True)
        # also need to mock the calculation methods because mocking of datetime.now() did not work for me
        monkeypatch.setattr(DailyEnergyMonitor, "calculate_consumption_today", lambda _: 888)
        monkeypatch.setattr(DailyEnergyMonitor, "calculate_consumption_yesterday", lambda _: 1234)
        # add further data (now in new day)
        instance.add_value(3000)
        assert instance.d0 == 888
        assert instance.d0_retained == 0  # this is being reset
        assert instance.d1 == 1234
        assert instance.d1_retained == 1234
        assert caplog.text == ('DEBUG    root:generate_d0_d1.py:74 new size of data[] is 1\n'
                               'DEBUG    root:generate_d0_d1.py:86 d0 delta: not enough data yet\n'
                               'DEBUG    root:generate_d0_d1.py:74 new size of data[] is 2\n'
                               'DEBUG    root:generate_d0_d1.py:79 d0 delta since start: 400.00\n'
                               'INFO     root:generate_d0_d1.py:84 d0: 400.00\n'
                               'DEBUG    root:generate_d0_d1.py:74 new size of data[] is 3\n'
                               'DEBUG    root:generate_d0_d1.py:79 d0 delta since start: 888.00\n'
                               'INFO     root:generate_d0_d1.py:84 d0: 888.00\n'
                               'DEBUG    root:generate_d0_d1.py:98 d1 delta since start: 1234.00\n'
                               'INFO     root:generate_d0_d1.py:104 d1: 1234.00\n')

    @staticmethod
    def test_yesterday_noyesterdaydata(monkeypatch):
        # action
        instance = DailyEnergyMonitor()
        # now mock the new day
        monkeypatch.setattr(DailyEnergyMonitor, "_check_is_new_day", lambda _, __: True)
        # also need to mock the calculation methods because mocking of datetime.now() did not work for me
        monkeypatch.setattr(DailyEnergyMonitor, "calculate_consumption_today", lambda _: 888)
        # tell that there's no data for yesterday
        monkeypatch.setattr(DailyEnergyMonitor, "calculate_consumption_yesterday", lambda _: None)
        # add further data (now in new day)
        instance.add_value(3000)
        assert instance.d0 == 888
        assert instance.d0_retained == 0  # this is being reset
        assert instance.d1 is None
        assert instance.d1_retained is None


class TestDailyEnergyMonitorToday:
    """Tests for calculate_consumption_today (d_0)."""

    @staticmethod
    def test_simple():
        now = datetime.now()
        instance = DailyEnergyMonitor()
        instance.data = [
            {'timestamp': now + timedelta(minutes=0), 'value': 111},
            {'timestamp': now + timedelta(minutes=1), 'value': 222},
            {'timestamp': now + timedelta(minutes=2), 'value': 333},
        ]
        assert len(instance.data) == 3
        actual = instance.calculate_consumption_today()
        assert actual == 333 - 111

    @staticmethod
    def test_toolittledata():
        instance = DailyEnergyMonitor()
        instance.add_value(11)  # only 1 value
        assert len(instance.data) == 1
        actual = instance.calculate_consumption_today()
        assert actual is None


class TestDailyEnergyMonitorYesterday:
    """calculate_consumption_yesterday (d_-1)."""

    @staticmethod
    def test_simple():
        yesterday = datetime.now() - timedelta(days=1)
        instance = DailyEnergyMonitor()
        instance.data = [
            {'timestamp': yesterday, 'value': 111},
            {'timestamp': yesterday + timedelta(minutes=1), 'value': 222},
            {'timestamp': yesterday + timedelta(minutes=2), 'value': 333},
        ]
        assert len(instance.data) == 3
        actual = instance.calculate_consumption_yesterday()
        assert actual == 333 - 111

    @staticmethod
    def test_only1entry():
        yesterday = datetime.now() - timedelta(days=1)
        instance = DailyEnergyMonitor()
        instance.data = [
            {'timestamp': yesterday, 'value': 111},
        ]
        assert len(instance.data) == 1
        actual = instance.calculate_consumption_yesterday()
        assert actual is None


class TestHandleSmartmeterMessage:

    @staticmethod
    def test_handle_smartmeter_message(monkeypatch):
        # ----------------------------------------------------
        # mocking part
        class MockClient:
            def __init__(self):
                self.published_messages = []

            def publish(self, topic, payload, retain=False):
                self.published_messages.append((topic, payload, retain))

        class MockUserdata:
            def __init__(self):
                self.d0 = 100.1234
                self.d1 = 200.5678
                self.retain = True
                self.last_value = None

            def add_value(self, value):
                self.last_value = value

        class MockMessage:
            def __init__(self, payload):
                self.payload = payload

        mock_client = MockClient()
        mock_userdata = MockUserdata()
        mock_msg = MockMessage(b"50.5")

        # ----------------------------------------------------
        # action
        handle_smartmeter_message(mock_client, mock_userdata, mock_msg)

        # ----------------------------------------------------
        # checks
        assert mock_userdata.last_value == 50.5
        assert mock_client.published_messages == [('tele/smartmeter/total/d0', 100.12, True),
                                                  ('tele/smartmeter/total/d1', 200.57, True)]

        # -------------------------------------------------
        # with DEBUG=True -> do not publish
        monkeypatch.setattr(generate_d0_d1, "DEBUG", True)
        mock_client.published_messages.clear()
        handle_smartmeter_message(mock_client, mock_userdata, mock_msg)
        assert not mock_client.published_messages


class TestHandleRetainedMessage:
    class MockClient:
        def __init__(self):
            self.unsubscribed_topics = []

        def unsubscribe(self, topic):
            self.unsubscribed_topics.append(topic)

    class MockUserdata:
        def __init__(self):
            self.d0_retained = None
            self.d1_retained = None

    class MockMessage:
        def __init__(self, topic, payload):
            self.topic = topic
            self.payload = payload

    @staticmethod
    def test_d0(caplog):
        # prepare
        mock_client = TestHandleRetainedMessage.MockClient()
        mock_userdata = TestHandleRetainedMessage.MockUserdata()
        mock_msg = TestHandleRetainedMessage.MockMessage(MQTT_TOPIC_D0, b"123.45")
        # action
        with caplog.at_level(logging.INFO):
            handle_retained_dx_message(mock_client, mock_userdata, mock_msg)
        # check
        assert mock_userdata.d0_retained == 123.45
        assert mock_userdata.d1_retained is None
        assert mock_client.unsubscribed_topics == [MQTT_TOPIC_D0]
        assert "d0 (retained): 123.45" in caplog.text

    @staticmethod
    def test_d1(caplog):
        # prepare
        mock_client = TestHandleRetainedMessage.MockClient()
        mock_userdata = TestHandleRetainedMessage.MockUserdata()
        mock_msg = TestHandleRetainedMessage.MockMessage(MQTT_TOPIC_D1, b"456.78")
        # action
        with caplog.at_level(logging.INFO):
            handle_retained_dx_message(mock_client, mock_userdata, mock_msg)
        # check
        assert mock_userdata.d0_retained is None
        assert mock_userdata.d1_retained == 456.78
        assert mock_client.unsubscribed_topics == [MQTT_TOPIC_D1]
        assert "d1 (retained): 456.78" in caplog.text

    @staticmethod
    def test_unexpected_topic(caplog):
        # prepare
        mock_client = TestHandleRetainedMessage.MockClient()
        mock_userdata = TestHandleRetainedMessage.MockUserdata()
        mock_msg = TestHandleRetainedMessage.MockMessage("footopic", b"999.99")
        # action
        with caplog.at_level(logging.INFO):
            handle_retained_dx_message(mock_client, mock_userdata, mock_msg)
        # check
        assert mock_userdata.d0_retained is None
        assert mock_userdata.d1_retained is None
        assert not mock_client.unsubscribed_topics
        assert caplog.records[0].levelno == logging.WARNING
        assert caplog.records[0].message == "Unexpected message! (footopic, b'999.99')"
        assert len(caplog.records) == 1
