"""
Sekoia.io Export Script

This script exports search job results from Sekoia.io API.
Usage:
  sekoia-event-export export <job_uuid>
  sekoia-event-export status <task_uuid>

Environment:
  API_KEY: Sekoia API token
  API_HOST: Sekoia API host (optional, defaults to api.sekoia.io)
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

import requests

DEFAULT_API_HOST = "api.sekoia.io"
DEFAULT_INTERVAL_S = 2
DEFAULT_TIMEOUT = (5, 30)  # (connect, read)


class ConfigError(RuntimeError):
    """Configuration error exception."""

    pass


def get_api_host(api_host: str | None = None) -> str:
    """Get the API host from argument, environment variable, or default.

    Priority:
    1. Argument (if provided)
    2. API_HOST environment variable
    3. Default (api.sekoia.io)

    Args:
        api_host: Optional API host override.

    Returns:
        str: The API host to use.
    """
    if api_host:
        return api_host
    return os.getenv("API_HOST", DEFAULT_API_HOST)


def create_http_session() -> requests.Session:
    """Create an HTTP session with API key authentication.

    Returns:
        requests.Session: Configured session with authorization header.

    Raises:
        ConfigError: If API_KEY environment variable is not set.
    """
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ConfigError("API_KEY environment variable not set.")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {api_key}"})
    return session


def trigger_export(job_uuid: str, session: requests.Session, api_host: str, timeout=DEFAULT_TIMEOUT) -> str:
    """Trigger an export job for the given search job UUID.

    Args:
        job_uuid: The UUID of the search job to export.
        session: Authenticated requests session.
        api_host: The API host to use.
        timeout: Request timeout tuple (connect, read).

    Returns:
        str: The task UUID for the triggered export job.

    Raises:
        RuntimeError: If the export trigger fails or returns no task UUID.
    """
    url = f"https://{api_host}/v1/sic/conf/events/search/jobs/{job_uuid}/export"
    resp = session.post(url, timeout=timeout)

    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"Failed to trigger export: {resp.status_code} {resp.text}")

    task_uuid = resp.json().get("task_uuid")
    if not task_uuid:
        raise RuntimeError("No task UUID returned from export trigger.")
    return task_uuid


def fetch_task(task_uuid: str, session: requests.Session, api_host: str, timeout=DEFAULT_TIMEOUT) -> dict:
    """Fetch the current status of an export task.

    Args:
        task_uuid: The UUID of the export task.
        session: Authenticated requests session.
        api_host: The API host to use.
        timeout: Request timeout tuple (connect, read).

    Returns:
        dict: Task status information from the API.

    Raises:
        RuntimeError: If fetching the task status fails.
    """
    url = f"https://{api_host}/v1/tasks/{task_uuid}"
    resp = session.get(url, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to get export status: {resp.status_code} {resp.text}")
    return resp.json()


def poll_status(
    task_uuid: str,
    session: requests.Session,
    api_host: str,
    interval_s: int = DEFAULT_INTERVAL_S,
    max_wait_s: int | None = None,
) -> None:
    """Poll the export task status until completion or timeout.

    Args:
        task_uuid: The UUID of the export task to poll.
        session: Authenticated requests session.
        api_host: The API host to use.
        interval_s: Polling interval in seconds.
        max_wait_s: Maximum wait time in seconds (None for no limit).

    Raises:
        TimeoutError: If max_wait_s is exceeded.
        RuntimeError: If the task fails or is cancelled.
    """
    start_time = datetime.now()
    deadline = (start_time + timedelta(seconds=max_wait_s)) if max_wait_s else None

    while True:
        if deadline and datetime.now() >= deadline:
            raise TimeoutError(f"Timed out after {max_wait_s}s waiting for task {task_uuid}")

        data = fetch_task(task_uuid, session, api_host)

        task_status = data.get("status")
        if task_status == "FINISHED":
            download_url = data.get("attributes", {}).get("download_url")
            if download_url:
                print(f"Export ready! Download URL: {download_url}")
            else:
                print("Export finished but no download URL found.")
            return

        if task_status in ("FAILED", "CANCELED", "CANCELLED"):
            # Some APIs include error info in attributes or a message field
            err = data.get("message") or data.get("attributes", {}).get("error") or data
            raise RuntimeError(f"Task ended with status={task_status}. Details: {err}")

        total = data.get("total", 0) or 0
        progress_count = data.get("progress", 0) or 0

        if total > 0:
            progress = 100 * progress_count / total
            elapsed = datetime.now() - start_time

            if progress_count > 0:
                estimated_total_time = elapsed * (total / progress_count)
                eta = start_time + estimated_total_time
                eta_str = eta.strftime("%H:%M:%S")
            else:
                eta_str = f"calculating... ({task_status})"

            current_time = datetime.now().strftime("%H:%M:%S")
            print(
                f"{current_time} {progress:.2f}% ({progress_count}/{total}) "
                f"completed... ETA: {eta_str} (status={task_status})"
            )
        else:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"{current_time} status={task_status} (progress unavailable)")

        time.sleep(interval_s)


def cmd_export(args) -> None:
    """Execute the export command."""
    api_host = get_api_host(args.api_host)
    session = create_http_session()
    print(f"Using API host: {api_host}")
    task_uuid = trigger_export(args.job_uuid, session, api_host)
    print(f"Export task triggered with UUID: {task_uuid}")
    poll_status(task_uuid, session, api_host, interval_s=args.interval, max_wait_s=args.max_wait)


def cmd_status(args) -> None:
    """Execute the status command."""
    api_host = get_api_host(args.api_host)
    session = create_http_session()
    print(f"Using API host: {api_host}")
    poll_status(args.task_uuid, session, api_host, interval_s=args.interval, max_wait_s=args.max_wait)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Sekoia.io Event Exporter - Export search job results", prog="sekoia-event-export"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export search job results")
    export_parser.add_argument("job_uuid", help="The UUID of the search job to export")
    export_parser.add_argument("--api-host", type=str, default=None, help="API host (overrides API_HOST env var)")
    export_parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S, help="Polling interval in seconds")
    export_parser.add_argument("--max-wait", type=int, default=None, help="Max wait time in seconds (optional)")
    export_parser.set_defaults(func=cmd_export)

    status_parser = subparsers.add_parser("status", help="Check export job status")
    status_parser.add_argument("task_uuid", help="The UUID of the export task")
    status_parser.add_argument("--api-host", type=str, default=None, help="API host (overrides API_HOST env var)")
    status_parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S, help="Polling interval in seconds")
    status_parser.add_argument("--max-wait", type=int, default=None, help="Max wait time in seconds (optional)")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.", file=sys.stderr)
        sys.exit(130)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
