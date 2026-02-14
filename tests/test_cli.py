"""Tests for the CLI module."""

from unittest.mock import patch

import pytest

from sekoia_event_exporter.cli import DEFAULT_API_HOST, ConfigError, create_http_session, get_api_host, main


def test_create_http_session_missing_api_key():
    """Test that create_http_session raises ConfigError when API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ConfigError, match="API_KEY environment variable not set"):
            create_http_session()


def test_create_http_session_success():
    """Test that create_http_session creates a session with proper authorization."""
    test_api_key = "test-api-key-123"
    with patch.dict("os.environ", {"API_KEY": test_api_key}):
        session = create_http_session()
        assert "Authorization" in session.headers
        assert session.headers["Authorization"] == f"Bearer {test_api_key}"


def test_get_api_host_with_argument():
    """Test that get_api_host returns the provided argument."""
    test_host = "api.us.sekoia.io"
    result = get_api_host(test_host)
    assert result == test_host


def test_get_api_host_with_env_var():
    """Test that get_api_host returns the API_HOST environment variable."""
    test_host = "api.eu.sekoia.io"
    with patch.dict("os.environ", {"API_HOST": test_host}):
        result = get_api_host()
        assert result == test_host


def test_get_api_host_default():
    """Test that get_api_host returns the default when no argument or env var."""
    with patch.dict("os.environ", {}, clear=True):
        result = get_api_host()
        assert result == DEFAULT_API_HOST


def test_get_api_host_argument_overrides_env():
    """Test that argument takes precedence over environment variable."""
    arg_host = "api.us.sekoia.io"
    env_host = "api.eu.sekoia.io"
    with patch.dict("os.environ", {"API_HOST": env_host}):
        result = get_api_host(arg_host)
        assert result == arg_host


def test_version_flag():
    """Test that --version flag displays the correct version."""
    with patch("sys.argv", ["sekoia-event-export", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        # argparse exits with code 0 when --version is used
        assert exc_info.value.code == 0


# Additional tests can be added here for trigger_export, fetch_task, and poll_status
# using mocked HTTP responses
