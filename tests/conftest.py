# -*- coding: utf-8 -*-
"""Local conftest.py plugins contain directory-specific hook implementations.

https://docs.pytest.org/en/7.1.x/how-to/writing_plugins.html#localplugin
"""

# pylint: disable=missing-function-docstring, unused-argument, import-outside-toplevel

import os
from pathlib import Path

# make sure messages are given in English
os.environ["LANG"] = "en"
# unset any http proxies, direct connections are wished
os.unsetenv("HTTP_PROXY")
os.unsetenv("HTTPS_PROXY")
os.environ["NO_PROXY"] = "*"


def pytest_runtest_setup(item):    # pylint: disable=unused-argument
    """Pytest calls this to perform the setup phase for a test item.

    https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_runtest_setup

    The default implementation runs setup() on item and all of its parents
    (which haven’t been setup yet).
    This includes obtaining the values of fixtures required by the item
    (which haven’t been obtained yet).
    """
    # check if we are actually in the test-file's sub-directory
    if os.getcwd() != Path(__file__).parent.resolve():
        # change (CWD) to PROJECTDIR/tests/
        os.chdir(Path(__file__).parent)
