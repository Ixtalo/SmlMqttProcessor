#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests."""

from datetime import datetime, timedelta

from generate_d0_d1 import DailyEnergyMonitor


# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring, line-too-long
# noqa: D102


class TestConstructor:
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


class TestAddValue:
    """Tests for add_value."""

    @staticmethod
    def test_add_value():
        instance = DailyEnergyMonitor()
        instance.add_value(100)
        instance.add_value(200)
        instance.add_value(300)
        assert len(instance.data) == 3
        assert instance.d0 == 300 - 100
        assert not instance.d1
        instance.add_value(330)
        assert instance.d0 == 330 - 100
        instance.add_value(350)
        assert instance.d0 == 350 - 100

    @staticmethod
    def test_only1entry():
        instance = DailyEnergyMonitor()
        instance.add_value(1111)
        assert len(instance.data) == 1
        assert instance.d0 is None
        assert instance.d1 is None

    @staticmethod
    def test_add_value_with_retain():
        instance = DailyEnergyMonitor()
        instance.d0_retained = 444
        instance.add_value(100)
        instance.add_value(200)
        instance.add_value(300)
        assert len(instance.data) == 3
        assert instance.d0 == 300 - 100 + 444
        assert not instance.d1
        instance.add_value(330)
        assert instance.d0 == 330 - 100 + 444
        instance.add_value(350)
        assert instance.d0 == 350 - 100 + 444

    @staticmethod
    def test_add_value_yesterday(monkeypatch):
        instance = DailyEnergyMonitor()
        instance.add_value(100)
        instance.add_value(200)
        instance.add_value(300)
        assert instance.current_date == datetime.now().date()


class TestToday:
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


class TestYesterday:
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
