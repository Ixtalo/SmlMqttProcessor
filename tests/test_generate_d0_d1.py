#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests."""
import logging
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest

import generate_d0_d1
from generate_d0_d1 import main


# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring, line-too-long
# noqa: D102

@pytest.fixture
def mock_config_file(tmp_path) -> Path:
    """Generate a temporary config file in the tests' TMPDIR."""
    config_file = tmp_path.joinpath("config.ini")
    config_template = Path(__file__).parent.parent.joinpath("config.template.ini").read_text()
    config_file.write_text(config_template)
    return config_file.absolute()


class TestMain:

    @staticmethod
    def test_no_config(monkeypatch, tmp_path):
        # prepare
        monkeypatch.setattr(generate_d0_d1, "__script_dir", tmp_path)   # TMPDIR/config.ini
        monkeypatch.setattr(mqtt.Client, "loop_forever", lambda _: None)
        # action + check
        with pytest.raises(FileNotFoundError,
                           match=rf"No configfile! \({tmp_path.joinpath('config.ini').resolve()}\)"):
            # action
            main()

    @staticmethod
    def test_main(mock_config_file, monkeypatch, caplog, capsys):
        # prepare
        monkeypatch.setattr(generate_d0_d1, "CONFIG_FILENAME", mock_config_file.absolute())
        monkeypatch.setattr(mqtt.Client, "connect", lambda *_, **__: None)
        monkeypatch.setattr(mqtt.Client, "loop_forever", lambda _: None)
        # action
        with caplog.at_level(logging.DEBUG):
            main()
        # check
        assert caplog.records[0].levelno == logging.INFO
        assert caplog.records[0].message == f"Config file: {mock_config_file.resolve()}"
        assert caplog.records[1].levelno == logging.DEBUG
        assert caplog.records[1].message == f"config read result: ['{mock_config_file.resolve()}']"
        assert len(caplog.records) == 2
        stdout, stderr = capsys.readouterr()
        assert stdout == ''
        assert stderr == ''
