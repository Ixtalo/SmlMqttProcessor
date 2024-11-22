#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests."""
import configparser
import logging
import os
from pathlib import Path

import pytest

import generate_d0_d1
from generate_d0_d1 import get_config


# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring,  missing-class-docstring
# pylint: disable=line-too-long, too-few-public-methods
# noqa: D102

@pytest.fixture
def mock_config_file(tmp_path) -> Path:
    """Generate a temporary config file in the tests' TMPDIR."""
    config_file = tmp_path.joinpath("test_config.ini")
    config_file.write_text("[DEFAULT]\nkey=value\n")
    return config_file


@pytest.fixture
def non_readable_file(tmp_path) -> Path:
    """Use a temporary config file but with missing read access."""
    config_file = tmp_path.joinpath("unreadable_config.ini")
    config_file.write_text("[DEFAULT]\nkey=value\n")
    os.chmod(config_file, 0o000)  # Entfernt Leserechte
    return config_file


def test_get_config_valid_file(mock_config_file, caplog):   # pylint: disable=redefined-outer-name
    # action
    with caplog.at_level(logging.INFO):
        config = get_config(mock_config_file)
    # check
    assert "Config file:" in caplog.text
    assert "test_config.ini" in caplog.text
    assert isinstance(config, configparser.ConfigParser)
    assert config["DEFAULT"]["key"] == "value"


def test_get_config_relative_path(mock_config_file, monkeypatch, caplog):   # pylint: disable=redefined-outer-name
    # prepare
    only_filename = mock_config_file.name
    monkeypatch.setattr(generate_d0_d1, "__script_dir", mock_config_file.parent)
    # action
    with caplog.at_level(logging.INFO):
        config = get_config(Path(only_filename))
    # check
    assert "Config file:" in caplog.text
    assert "test_config.ini" in caplog.text
    assert isinstance(config, configparser.ConfigParser)


def test_get_config_file_not_found(tmp_path):
    non_existent_file = tmp_path.joinpath("non_existent_config.ini")
    with pytest.raises(FileNotFoundError,
                       match=rf"No configfile! \({non_existent_file.resolve()}\)"):
        get_config(non_existent_file)


def test_get_config_file_not_readable(non_readable_file):   # pylint: disable=redefined-outer-name
    with pytest.raises(RuntimeError,
                       match=rf"Configfile not readable! \({non_readable_file.resolve()}\)"):
        get_config(non_readable_file)
