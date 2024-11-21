#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests."""

import datetime as dt
from datetime import date, datetime, timedelta
import pytest

from generate_d0_d1 import EnergyMonitor

# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring, line-too-long
# noqa: D102


class TestEnergyMonitor:
    """Tests for userdata class."""

    @staticmethod
    def test_constructor():
        instance = EnergyMonitor()
        assert instance.retain
        assert not instance.data    # it is []
        assert instance.d0 is None
        assert instance.d1 is None
        assert instance.current_date == datetime.now().date()

    @staticmethod
    def test_constructor_retain_false():
        instance = EnergyMonitor(retain=False)
        assert not instance.retain

    @staticmethod
    def test_calculate_daily_consumption():
        now = datetime.now()
        instance = EnergyMonitor()
        instance.data = [
            {'timestamp': now + timedelta(minutes=0), 'value': 111},
            {'timestamp': now + timedelta(minutes=1), 'value': 222},
            {'timestamp': now + timedelta(minutes=2), 'value': 333},
        ]
        assert len(instance.data) == 3
        actual = instance.calculate_daily_consumption()
        assert actual == 333-111

    @staticmethod
    def test_calculate_daily_consumption_toolittledata():
        instance = EnergyMonitor()
        instance.add_value(11)  # only 1 value
        assert len(instance.data) == 1
        actual = instance.calculate_daily_consumption()
        assert actual is None

    @staticmethod
    def test_calculate_yesterday_consumption():
        yesterday = datetime.now() - timedelta(days=1)
        instance = EnergyMonitor()
        instance.data = [
            {'timestamp': yesterday, 'value': 111},
            {'timestamp': yesterday + timedelta(minutes=1), 'value': 222},
            {'timestamp': yesterday + timedelta(minutes=2), 'value': 333},
        ]
        assert len(instance.data) == 3
        actual = instance.calculate_yesterday_consumption()
        assert actual == 333-111

    @staticmethod
    def test_calculate_yesterday_consumption_only1entry():
        yesterday = datetime.now() - timedelta(days=1)
        instance = EnergyMonitor()
        instance.data = [
            {'timestamp': yesterday, 'value': 111},
        ]
        assert len(instance.data) == 1
        actual = instance.calculate_yesterday_consumption()
        assert actual is None

    @staticmethod
    def test_add_value_only1entry():
        instance = EnergyMonitor()
        instance.add_value(1111)
        assert len(instance.data) == 1
        assert instance.d0 is None
        assert instance.d1 is None

    @staticmethod
    def test_add_value():
        instance = EnergyMonitor()
        instance.add_value(100)
        instance.add_value(200)
        instance.add_value(300)
        assert len(instance.data) == 3
        assert instance.d0 == 300-100
        assert not instance.d1
        instance.add_value(330)
        assert instance.d0 == 330-100
        instance.add_value(350)
        assert instance.d0 == 350-100

    @staticmethod
    def test_add_value_with_retain():
        instance = EnergyMonitor()
        instance.d0_retained = 444
        instance.add_value(100)
        instance.add_value(200)
        instance.add_value(300)
        assert len(instance.data) == 3
        assert instance.d0 == 300-100+444
        assert not instance.d1
        instance.add_value(330)
        assert instance.d0 == 330-100+444
        instance.add_value(350)
        assert instance.d0 == 350-100+444

    @staticmethod
    def test_add_value_yesterday(monkeypatch):
        instance = EnergyMonitor()
        instance.add_value(100)
        instance.add_value(200)
        instance.add_value(300)
        assert instance.current_date == datetime.now().date()