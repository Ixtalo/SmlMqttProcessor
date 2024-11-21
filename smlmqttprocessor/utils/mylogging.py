#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Utility functions for logging."""
import logging
import sys

import colorlog


def setup_logging(log_file: str = None, level: int = logging.INFO, color=True):
    """Set up the logging framework."""
    # logging.basicConfig(level=logging.WARNING if not DEBUG else logging.DEBUG,
    #                    stream=LOGGING_STREAM,
    #                    format="%(asctime)s %(levelname)-8s %(message)s",
    #                    datefmt="%Y-%m-%d %H:%M:%S")
    if log_file:
        # pylint: disable=consider-using-with
        stream = open(log_file, "a", encoding="utf8")
        color = False
    else:
        stream = sys.stdout
    handler = colorlog.StreamHandler(stream=stream)
    format_string = "%(log_color)s%(asctime)s %(levelname)-8s %(message)s"
    formatter = colorlog.ColoredFormatter(format_string,
                                          datefmt="%Y-%m-%d %H:%M:%S",
                                          no_color=not color)
    handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[handler])
