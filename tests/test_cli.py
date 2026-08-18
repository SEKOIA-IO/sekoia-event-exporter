"""Tests for the CLI module."""

from unittest.mock import MagicMock, patch

import pytest

from sekoia_event_exporter.cli import (
    DEFAULT_API_HOST,
    ConfigError,
    create_http_session,
    get_api_host,
    main,
    trigger_export,
)


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


def _make_response(status_code: int, json_data: dict) -> MagicMock:
    """Build a mock requests.Response with the given status code and JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def _sse_c_config() -> dict:
    """Return an S3 config carrying SSE-C settings."""
    return {
        "sse_customer_key": "a-key",
        "sse_customer_key_md5": "a-md5",
        "sse_customer_algorithm": "AES256",
    }


def test_trigger_export_retries_without_sse_c_on_es110(capsys):
    """When the server returns ES110, retry the export without any SSE-C key."""
    session = MagicMock()
    es110 = _make_response(
        400,
        {
            "message": "SSE-C encryption is not supported on the region's default export bucket.",
            "code": "ES110",
        },
    )
    success = _make_response(200, {"task_uuid": "task-123"})
    session.post.side_effect = [es110, success]

    s3_config = _sse_c_config()
    task_uuid = trigger_export("job-1", session, "api.sekoia.io", s3_config=s3_config)

    assert task_uuid == "task-123"
    assert session.post.call_count == 2

    # SSE-C settings were stripped in place so the download won't try to decrypt.
    assert "sse_customer_key" not in s3_config
    assert "sse_customer_key_md5" not in s3_config
    assert "sse_customer_algorithm" not in s3_config

    # The retry request must not carry an SSE-C key.
    retry_body = session.post.call_args_list[1].kwargs["json"]
    assert retry_body is None or "sse_customer_key" not in retry_body.get("s3", {})

    assert "SSE-C encryption is not supported" in capsys.readouterr().err


def test_trigger_export_keeps_other_s3_config_on_es110():
    """The ES110 retry keeps non-SSE-C S3 settings intact."""
    session = MagicMock()
    session.post.side_effect = [
        _make_response(400, {"code": "ES110"}),
        _make_response(201, {"task_uuid": "task-xyz"}),
    ]

    s3_config = {"bucket_name": "my-bucket", **_sse_c_config()}
    trigger_export("job-2", session, "api.sekoia.io", s3_config=s3_config)

    retry_body = session.post.call_args_list[1].kwargs["json"]
    assert retry_body["s3"] == {"bucket_name": "my-bucket"}


def test_trigger_export_does_not_retry_on_other_errors():
    """A non-ES110 error is raised without retrying."""
    session = MagicMock()
    session.post.return_value = _make_response(500, {"code": "ES999"})

    with pytest.raises(RuntimeError, match="Failed to trigger export"):
        trigger_export("job-3", session, "api.sekoia.io", s3_config=_sse_c_config())

    assert session.post.call_count == 1


# Additional tests can be added here for fetch_task and poll_status
# using mocked HTTP responses
