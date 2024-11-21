# -*- coding: utf-8 -*-
"""Unit Tests."""

from smlmqttprocessor.utils.message_utils import convert_messages2records


def test_convert_messages2records():
    """Test for converting message-dictionaries to a dictionary with value-lists"""
    messages = [{'a': 11, 'b': 12}, {'a': 21, 'b': 22}]
    expected = {'a': [11, 21], 'b': [12, 22]}
    actual = convert_messages2records(messages)
    assert actual == expected
