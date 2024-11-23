#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Handling of message types."""


def convert_messages2records(messages):
    """Convert a list of message-dictionaries to a dictionary with value-lists.

    This is:
        [ {a:11, b:12}, {a:21, b:22}, ... ]  --> {a:[11,21], b:[12,22]}

    :param messages:
    :return:
    """
    records = {}
    for message in messages:
        for key, value in message.items():
            if key in records:
                records[key].append(value)
            else:
                records[key] = [value]  # start a new list
    return records
