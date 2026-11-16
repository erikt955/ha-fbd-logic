"""Test fixtures."""

import sys

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def norwegian_by_default(hass):
    """The texts are written in Norwegian; tests that check English set hass.config.language themselves."""
    from custom_components.fbd_logic import i18n  # pylint: disable=import-outside-toplevel

    hass.config.language = "nb"
    i18n.set_language("nb")
    yield
    i18n.set_language("nb")


if sys.platform == "win32":
    # On Windows asyncio's self-pipe is a localhost TCP socket pair, which
    # pytest-socket (enabled by the HA test plugin) blocks, so socket blocking
    # is turned off here. Requires PYTHONPATH=tests/winstubs too (stubs for the
    # POSIX-only fcntl/resource modules), see tests/run_tests.ps1.
    import pytest_socket  # pylint: disable=import-outside-toplevel

    pytest_socket.disable_socket = lambda *a, **kw: None
    pytest_socket.socket_allow_hosts = lambda *a, **kw: None
