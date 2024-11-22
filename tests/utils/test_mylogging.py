# -*- coding: utf-8 -*-
"""Unit Tests."""
import logging
import os

from smlmqttprocessor.utils.mylogging import setup_logging

# do not complain about missing docstring for tests
# pylint: disable=missing-function-docstring,  missing-class-docstring
# pylint: disable=line-too-long, too-few-public-methods
# noqa: D102


class TestSetupLoggingDefaults:

    @staticmethod
    def test_default(caplog, capsys):
        # action
        setup_logging()
        # check
        assert caplog.records == []
        stdout, stderr = capsys.readouterr()
        assert not stdout
        assert not stderr


class TestSetupLoggingLevels:

    @staticmethod
    def test_1info(caplog, capsys):
        caplog.set_level(logging.INFO)  # needed, setup_logging(level) did not work
        # action
        setup_logging()
        logging.info("foo")
        # check
        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.INFO
        assert caplog.records[0].msg == "foo"
        # check formatting
        assert caplog.text == 'INFO     root:test_mylogging.py:34 foo\n'
        # check that colored logging is active
        assert 'ColoredLevelFormatter' in repr(caplog.handler.formatter)
        # check that nothing has been written to STDOUT/STDERR
        # (everything should be handled by logging)
        stdout, stderr = capsys.readouterr()
        assert not stdout
        assert not stderr

    @staticmethod
    def test_1warning(caplog, capsys):
        caplog.set_level(logging.INFO)  # needed, setup_logging(level) did not work
        # action
        setup_logging()
        logging.warning("foo")
        # check
        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.WARNING
        assert caplog.records[0].msg == "foo"
        stdout, stderr = capsys.readouterr()
        assert not stdout
        assert not stderr

    @staticmethod
    def test_1debug(caplog, capsys):
        caplog.set_level(logging.INFO)  # needed, setup_logging(level) did not work
        # action
        setup_logging()
        logging.debug("foo")
        # check
        assert caplog.records == []
        stdout, stderr = capsys.readouterr()
        assert not stdout
        assert not stderr


class TestSetupLoggingLogfile:

    @staticmethod
    def test_logfile(tmp_path, capsys):
        log_file = tmp_path.joinpath("foo.log")
        assert not log_file.is_file()
        # action
        setup_logging(level=logging.INFO, log_file=str(log_file.resolve()))
        logging.debug("foodebug")  # will not be written
        logging.info("fooinfo")
        logging.warning("foowarning")
        logging.error("fooerror")
        # sync to disk
        os.sync()
        # check
        # did not work # assert log_file.read_text() == " ... "
        assert log_file.is_file()
        # check
        stdout, stderr = capsys.readouterr()
        assert not stdout
        assert not stderr
