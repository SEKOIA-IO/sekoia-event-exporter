"""
Sekoia.io Export Script

This script exports search job results from Sekoia.io API.
Usage:
  sekoia-event-export export <job_uuid>   # Trigger and monitor export
  sekoia-event-export status <task_uuid>  # Check task status
  sekoia-event-export download <task_uuid>  # Download completed export

Environment:
  API_KEY: Sekoia API token
  API_HOST: Sekoia API host (optional, defaults to api.sekoia.io)
"""

import argparse
import base64
import binascii
import hashlib
import os
import sys
import time
from datetime import datetime, timedelta

import requests

from . import __version__

DEFAULT_API_HOST = "api.sekoia.io"
DEFAULT_INTERVAL_S = 2
DEFAULT_TIMEOUT = (5, 30)  # (connect, read)
DEFAULT_EXPORT_FIELDS = ["message", "timestamp"]  # Default fields to export


class ConfigError(RuntimeError):
    """Configuration error exception."""

    pass


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for styled terminal output."""

    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @staticmethod
    def is_tty() -> bool:
        """Check if stdout is a TTY (terminal)."""
        return sys.stdout.isatty()

    @classmethod
    def disable_if_not_tty(cls):
        """Disable colors if not running in a terminal."""
        if not cls.is_tty():
            cls.BLUE = cls.GREEN = cls.YELLOW = cls.RED = cls.BOLD = cls.DIM = cls.RESET = ""


# Disable colors if not in a TTY
Colors.disable_if_not_tty()


def format_bytes(bytes_count: int | float) -> str:
    """Format bytes into human-readable format.

    Args:
        bytes_count: Number of bytes to format.

    Returns:
        str: Human-readable size string (e.g., "1.5 MB", "750 KB").

    Example:
        >>> format_bytes(1536)
        '1.5 KB'
        >>> format_bytes(1048576)
        '1.0 MB'
    """
    size = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def create_progress_bar(percentage: float, width: int = 40) -> str:
    """Create a visual progress bar using Unicode box-drawing characters.

    Args:
        percentage: Progress percentage (0-100).
        width: Width of the progress bar in characters.

    Returns:
        str: A colored progress bar string.

    Example:
        >>> create_progress_bar(50, 20)
        '██████████░░░░░░░░░░'
    """
    filled = int((percentage / 100) * width)
    bar = "█" * filled + "░" * (width - filled)

    # Color the bar based on progress
    if percentage < 33:
        color = Colors.RED
    elif percentage < 66:
        color = Colors.YELLOW
    else:
        color = Colors.GREEN

    return f"{color}{bar}{Colors.RESET}"


def format_time_delta(seconds: float) -> str:
    """Format a time delta in seconds to human-readable format.

    Args:
        seconds: Number of seconds.

    Returns:
        str: Formatted time string (e.g., "2m 30s", "1h 15m").

    Example:
        >>> format_time_delta(150)
        '2m 30s'
        >>> format_time_delta(3665)
        '1h 1m'
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def generate_random_b64_sse_key() -> str:
    """Generate a random 256-bit (32-byte) SSE-C encryption key.

    Creates a cryptographically secure random key suitable for S3 Server-Side
    Encryption with Customer-Provided Keys (SSE-C). The key is base64-encoded
    for safe transmission and storage.

    Returns:
        str: A base64-encoded 256-bit (32-byte) random key.

    Example:
        >>> key = generate_random_b64_sse_key()
        >>> len(base64.b64decode(key))
        32

    Note:
        This function uses os.urandom() which provides cryptographically
        acceptable random bytes suitable for encryption keys.
    """
    random_bytes = os.urandom(32)  # 32 bytes = 256 bits
    return base64.b64encode(random_bytes).decode("utf-8")


def get_export_fields(fields_arg: str | None = None) -> list[str]:
    """Get the list of fields to export.

    Args:
        fields_arg: Optional comma-separated fields value from command-line argument.

    Returns:
        list[str]: List of field names to export.

    Priority:
        1. Command-line argument (--fields)
        2. Environment variable (EXPORT_FIELDS)
        3. Default fields (message, timestamp)

    Example:
        >>> get_export_fields("message,timestamp,source.ip")
        ['message', 'timestamp', 'source.ip']
        >>> get_export_fields()  # Uses defaults
        ['message', 'timestamp']
    """
    # Check command-line argument first
    if fields_arg:
        # Split by comma and strip whitespace
        return [field.strip() for field in fields_arg.split(",") if field.strip()]

    # Check environment variable
    env_value = os.getenv("EXPORT_FIELDS")
    if env_value:
        # Split by comma and strip whitespace
        return [field.strip() for field in env_value.split(",") if field.strip()]

    # Return default fields
    return DEFAULT_EXPORT_FIELDS.copy()


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


def build_s3_config(args, auto_generate_key: bool = True) -> dict | None:
    """Build S3 configuration from CLI arguments and environment variables.

    Priority: CLI arguments > environment variables

    Args:
        args: Parsed CLI arguments containing S3 configuration options.
        auto_generate_key: Whether to auto-generate an SSE-C key if none is provided.
                          Should be True for export, False for status.

    Returns:
        dict | None: S3 configuration dict, or None if no S3 settings are provided.
    """
    s3_config = {}

    # Get values from args (CLI) or environment variables
    def get_value(arg_name: str, env_name: str) -> str | None:
        """Get value from CLI arg or env var, with CLI taking priority."""
        arg_value = getattr(args, arg_name, None)
        if arg_value is not None:
            return arg_value
        return os.getenv(env_name)

    # S3 bucket and prefix
    bucket = get_value("s3_bucket", "S3_BUCKET")
    if bucket:
        s3_config["bucket_name"] = bucket

    prefix = get_value("s3_prefix", "S3_PREFIX")
    if prefix:
        s3_config["prefix"] = prefix

    # S3 credentials
    access_key = get_value("s3_access_key", "S3_ACCESS_KEY_ID")
    if access_key:
        s3_config["access_key_id"] = access_key

    secret_key = get_value("s3_secret_key", "S3_SECRET_ACCESS_KEY")
    if secret_key:
        s3_config["secret_access_key"] = secret_key

    # S3 endpoint and region
    endpoint = get_value("s3_endpoint", "S3_ENDPOINT_URL")
    if endpoint:
        s3_config["endpoint_url"] = endpoint

    region = get_value("s3_region", "S3_REGION_NAME")
    if region:
        s3_config["region_name"] = region

    # SSE-C encryption settings
    # Check if SSE-C is explicitly disabled
    no_sse_c = getattr(args, "no_sse_c", False)

    if not no_sse_c:
        sse_key = get_value("s3_sse_c_key", "S3_SSE_C_KEY")

        # Auto-generate key if none provided (encryption by default for export only)
        if not sse_key and auto_generate_key:
            sse_key = generate_random_b64_sse_key()
            # Mark that this key was auto-generated
            s3_config["_generated_key"] = sse_key
    else:
        sse_key = None

    if sse_key:
        # Validate and process the SSE-C key
        try:
            key_bytes = base64.b64decode(sse_key)

            # Validate key is exactly 32 bytes (256 bits)
            if len(key_bytes) != 32:
                raise ConfigError(
                    f"SSE-C key must be exactly 32 bytes (256 bits). "
                    f"Got {len(key_bytes)} bytes after base64 decoding. "
                    f"Generate a valid key with: openssl rand -base64 32"
                )
        except binascii.Error as e:
            raise ConfigError(f"SSE-C key is not valid base64: {e}") from e

        s3_config["sse_customer_key"] = sse_key
        # Set algorithm to AES256 by default if a key is provided
        s3_config["sse_customer_algorithm"] = get_value("s3_sse_c_algorithm", "S3_SSE_C_ALGORITHM") or "AES256"

        # Automatically compute MD5 if not provided
        sse_key_md5 = get_value("s3_sse_c_key_md5", "S3_SSE_C_KEY_MD5")
        if not sse_key_md5:
            # Compute MD5 of the key bytes and encode to base64
            md5_hash = hashlib.md5(key_bytes).digest()
            sse_key_md5 = base64.b64encode(md5_hash).decode("utf-8")

        s3_config["sse_customer_key_md5"] = sse_key_md5

    # Return None if no configuration was provided
    return s3_config if s3_config else None


def trigger_export(
    job_uuid: str,
    session: requests.Session,
    api_host: str,
    timeout=DEFAULT_TIMEOUT,
    s3_config: dict | None = None,
    fields: list[str] | None = None,
) -> str:
    """Trigger an export job for the given search job UUID.

    Args:
        job_uuid: The UUID of the search job to export.
        session: Authenticated requests session.
        api_host: The API host to use.
        timeout: Request timeout tuple (connect, read).
        s3_config: Optional custom S3 configuration including SSE-C settings.
        fields: Optional list of fields to include in the export.

    Returns:
        str: The task UUID for the triggered export job.

    Raises:
        RuntimeError: If the export trigger fails or returns no task UUID.
    """
    url = f"https://{api_host}/v1/sic/conf/events/search/jobs/{job_uuid}/export"

    # Build request body
    body: dict = {}
    if s3_config:
        body["s3"] = s3_config
    if fields:
        body["fields"] = fields

    # Send POST request with JSON body if we have config, otherwise empty body
    resp = session.post(url, json=body if body else None, timeout=timeout)

    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"Failed to trigger export: {resp.status_code} {resp.text}")

    task_uuid = resp.json().get("task_uuid")
    if not task_uuid:
        raise RuntimeError("No task UUID returned from export trigger.")
    return task_uuid


def download_file(
    download_url: str,
    output_filename: str | None = None,
    s3_config: dict | None = None,
) -> str:
    """Download the exported file from the given URL.

    Args:
        download_url: The pre-signed URL to download from.
        session: Authenticated requests session.
        output_filename: Optional custom filename. If not provided, generates one.
        s3_config: Optional S3 configuration containing SSE-C settings.

    Returns:
        str: The path to the downloaded file.

    Raises:
        RuntimeError: If the download fails.
    """
    # Generate filename if not provided
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"export_{timestamp}.json.gz"

    # Add SSE-C headers if encryption was used
    headers = {}
    if s3_config and "sse_customer_key" in s3_config:
        headers["x-amz-server-side-encryption-customer-algorithm"] = s3_config.get("sse_customer_algorithm", "AES256")
        headers["x-amz-server-side-encryption-customer-key"] = s3_config["sse_customer_key"]
        headers["x-amz-server-side-encryption-customer-key-MD5"] = s3_config["sse_customer_key_md5"]

    print(f"\n{Colors.BOLD}Downloading:{Colors.RESET} {output_filename}")
    if headers:
        print(f"{Colors.DIM}Using SSE-C encryption headers{Colors.RESET}")

    try:
        resp = requests.get(download_url, headers=headers, stream=True, timeout=(5, 60))
        resp.raise_for_status()

        # Get total size if available
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.time()
        last_update = start_time

        with open(output_filename, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    current_time = time.time()

                    # Update progress every 0.1 seconds to avoid flickering
                    if total_size > 0 and (current_time - last_update) >= 0.1:
                        progress = (downloaded / total_size) * 100
                        elapsed = current_time - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0

                        # Create progress bar
                        bar = create_progress_bar(progress, width=30)

                        # Format the progress line
                        progress_line = (
                            f"\r{bar} {Colors.BOLD}{progress:5.1f}%{Colors.RESET} | "
                            f"{Colors.BLUE}{format_bytes(downloaded)}{Colors.RESET} / "
                            f"{format_bytes(total_size)} | "
                            f"{Colors.GREEN}{format_bytes(int(speed))}/s{Colors.RESET}"
                        )
                        print(progress_line, end="", flush=True)
                        last_update = current_time

        # Final newline and completion message
        if total_size > 0:
            elapsed = time.time() - start_time
            print(
                f"\n{Colors.GREEN}✓{Colors.RESET} {Colors.BOLD}Download complete{Colors.RESET} "
                f"({format_bytes(downloaded)} in {format_time_delta(elapsed)})"
            )
        else:
            print(f"\n{Colors.GREEN}✓{Colors.RESET} {Colors.BOLD}Download complete{Colors.RESET}")
            print(f"({format_bytes(downloaded)})")
        return output_filename

    except Exception as e:
        raise RuntimeError(f"Failed to download file: {e}") from e


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
) -> str | None:
    """Poll the export task status until completion or timeout.

    Args:
        task_uuid: The UUID of the export task to poll.
        session: Authenticated requests session.
        api_host: The API host to use.
        interval_s: Polling interval in seconds.
        max_wait_s: Maximum wait time in seconds (None for no limit).

    Returns:
        str | None: Download URL if available, None otherwise.

    Raises:
        TimeoutError: If max_wait_s is exceeded.
        RuntimeError: If the task fails or is cancelled.
    """
    start_time = datetime.now()
    deadline = (start_time + timedelta(seconds=max_wait_s)) if max_wait_s else None

    # Track progress between polls to calculate accurate rate
    last_progress_count = None
    last_poll_time = None

    while True:
        if deadline and datetime.now() >= deadline:
            raise TimeoutError(f"Timed out after {max_wait_s}s waiting for task {task_uuid}")

        current_poll_time = datetime.now()
        data = fetch_task(task_uuid, session, api_host)

        task_status = data.get("status")
        if task_status == "FINISHED":
            download_url = data.get("attributes", {}).get("download_url")
            # Clear the progress line
            print(f"\r{' ' * 100}\r", end="")
            if download_url:
                print(f"{Colors.GREEN}✓{Colors.RESET} {Colors.BOLD}Export ready!{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}⚠{Colors.RESET} Export finished but no download URL found.")
            return download_url

        if task_status in ("FAILED", "CANCELED", "CANCELLED"):
            # Clear the progress line
            print(f"\r{' ' * 100}\r", end="")
            # Some APIs include error info in attributes or a message field
            err = data.get("message") or data.get("attributes", {}).get("error") or data
            raise RuntimeError(f"Task ended with status={task_status}. Details: {err}")

        total = data.get("total", 0) or 0
        progress_count = data.get("progress", 0) or 0

        if total > 0:
            progress = 100 * progress_count / total

            # Calculate remaining time based on observed progress rate between polls
            if last_progress_count is not None and last_poll_time is not None and progress_count > last_progress_count:
                time_diff = (current_poll_time - last_poll_time).total_seconds()
                progress_diff = progress_count - last_progress_count

                if time_diff > 0 and progress_diff > 0:
                    # Calculate items per second based on observed rate
                    items_per_second = progress_diff / time_diff
                    remaining_items = total - progress_count
                    remaining_seconds = remaining_items / items_per_second
                    eta_str = format_time_delta(remaining_seconds)
                else:
                    eta_str = "calculating..."
            else:
                eta_str = "calculating..."

            # Update tracking variables for next iteration
            last_progress_count = progress_count
            last_poll_time = current_poll_time

            # Create progress bar
            bar = create_progress_bar(progress, width=30)

            # Format progress count with thousand separators
            progress_str = f"{progress_count:,} / {total:,}"

            # Build the progress line
            progress_line = (
                f"\r{Colors.BLUE}Exporting:{Colors.RESET} {bar} "
                f"{Colors.BOLD}{progress:5.1f}%{Colors.RESET} | "
                f"{progress_str} events | "
                f"{Colors.YELLOW}⏱  {eta_str} remaining{Colors.RESET}"
            )
            print(progress_line, end="", flush=True)
        else:
            # When total is unknown, show a spinner
            spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            elapsed_seconds = (datetime.now() - start_time).total_seconds()
            spinner_char = spinner[int(elapsed_seconds / 0.2) % len(spinner)]

            progress_line = (
                f"\r{Colors.BLUE}{spinner_char} Exporting:{Colors.RESET} "
                f"{Colors.DIM}status={task_status} (progress unavailable){Colors.RESET}"
            )
            print(progress_line, end="", flush=True)

        time.sleep(interval_s)


def cmd_export(args) -> None:
    """Execute the export command."""
    api_host = get_api_host(args.api_host)
    session = create_http_session()
    s3_config = build_s3_config(args)
    fields = get_export_fields(getattr(args, "fields", None))

    # Header
    print(f"\n{Colors.BOLD}Sekoia Event Exporter{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")
    print(f"{Colors.BLUE}API Host:{Colors.RESET} {api_host}")
    print(f"{Colors.BLUE}Export Fields:{Colors.RESET} {', '.join(fields)}")

    if s3_config:
        # Check if encryption key was auto-generated
        generated_key = s3_config.pop("_generated_key", None)

        # Check what type of S3 configuration is being used
        has_sse_c = "sse_customer_key" in s3_config
        # S3 config keys excluding SSE-C related ones
        s3_bucket_keys = [
            k
            for k in s3_config.keys()
            if k not in ("sse_customer_key", "sse_customer_key_md5", "sse_customer_algorithm")
        ]

        if s3_bucket_keys:
            # Show non-sensitive S3 bucket configuration
            display_keys = [k for k in s3_bucket_keys if "key" not in k.lower() and "secret" not in k.lower()]
            if display_keys:
                print(f"{Colors.BLUE}S3 Config:{Colors.RESET} {', '.join(display_keys)}")

        if has_sse_c:
            if generated_key:
                print(f"\n{Colors.YELLOW}{'═' * 80}{Colors.RESET}")
                print(f"{Colors.YELLOW}⚠  SSE-C ENCRYPTION KEY AUTO-GENERATED{Colors.RESET}")
                print(f"{Colors.YELLOW}{'═' * 80}{Colors.RESET}")
                print(f"{Colors.BOLD}Encryption Key:{Colors.RESET} {Colors.GREEN}{generated_key}{Colors.RESET}")
                print(
                    f"\n{Colors.YELLOW}⚠  IMPORTANT:{Colors.RESET} {Colors.BOLD}Save this key securely!{Colors.RESET}"
                )
                print(f"{Colors.DIM}   • You will need it to download this export later{Colors.RESET}")
                print(f"{Colors.DIM}   • If you lose this key, you will NOT be able to decrypt your data{Colors.RESET}")
                print(f"{Colors.YELLOW}{'═' * 80}{Colors.RESET}\n")
            else:
                print(f"{Colors.GREEN}🔒 SSE-C encryption enabled{Colors.RESET}")

    task_uuid = trigger_export(args.job_uuid, session, api_host, s3_config=s3_config, fields=fields)
    print(f"\n{Colors.GREEN}✓{Colors.RESET} {Colors.BOLD}Export triggered{Colors.RESET}")
    print(f"{Colors.DIM}Task UUID: {task_uuid}{Colors.RESET}\n")

    download_url = poll_status(task_uuid, session, api_host, interval_s=args.interval, max_wait_s=args.max_wait)

    # Download the file if URL is available and download is not disabled
    if download_url and not args.no_download:
        try:
            download_file(download_url, output_filename=args.output, s3_config=s3_config)
        except Exception as e:
            print(f"\n{Colors.RED}✗ Download failed:{Colors.RESET} {e}", file=sys.stderr)
            print(f"{Colors.YELLOW}→{Colors.RESET} Manual download: {download_url}", file=sys.stderr)


def cmd_status(args) -> None:
    """Execute the status command - shows task status without downloading."""
    api_host = get_api_host(args.api_host)
    session = create_http_session()

    # Header
    print(f"\n{Colors.BOLD}Sekoia Event Exporter - Status{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")
    print(f"{Colors.BLUE}API Host:{Colors.RESET} {api_host}")
    print(f"{Colors.BLUE}Task UUID:{Colors.RESET} {args.task_uuid}\n")

    # Fetch current task status (single check, no polling)
    try:
        data = fetch_task(args.task_uuid, session, api_host)
        task_status = data.get("status")
        total = data.get("total", 0) or 0
        progress_count = data.get("progress", 0) or 0

        # Display status
        print(f"{Colors.BOLD}Status:{Colors.RESET} {task_status}")

        if total > 0:
            progress = 100 * progress_count / total
            bar = create_progress_bar(progress, width=30)
            progress_str = f"{progress_count:,} / {total:,}"
            print(f"{Colors.BOLD}Progress:{Colors.RESET} {bar} {progress:5.1f}%")
            print(f"{Colors.BOLD}Events:{Colors.RESET} {progress_str}")

        # Show download URL if available
        if task_status == "FINISHED":
            download_url = data.get("attributes", {}).get("download_url")
            if download_url:
                print(f"\n{Colors.GREEN}✓{Colors.RESET} {Colors.BOLD}Export complete!{Colors.RESET}")
                print(f"{Colors.BLUE}Download URL:{Colors.RESET}")
                print(f"{Colors.DIM}{download_url}{Colors.RESET}")
                print(
                    f"\n{Colors.YELLOW}→{Colors.RESET} Use the {Colors.BOLD}download{Colors.RESET} command to download:"
                )
                print(f"  {Colors.DIM}sekoia-event-export download {args.task_uuid}{Colors.RESET}")
            else:
                print(f"\n{Colors.YELLOW}⚠{Colors.RESET} Export finished but no download URL found.")
        elif task_status in ("FAILED", "CANCELED", "CANCELLED"):
            err = data.get("message") or data.get("attributes", {}).get("error") or "No error details available"
            print(f"\n{Colors.RED}✗{Colors.RESET} {Colors.BOLD}Task {task_status.lower()}{Colors.RESET}")
            print(f"{Colors.RED}Error:{Colors.RESET} {err}")
        else:
            print(f"\n{Colors.YELLOW}⏱{Colors.RESET} Export still in progress")
            print(f"{Colors.DIM}Use the status command again to check progress{Colors.RESET}")

    except Exception as e:
        print(f"\n{Colors.RED}✗ Failed to fetch task status:{Colors.RESET} {e}", file=sys.stderr)
        sys.exit(1)


def cmd_download(args) -> None:
    """Execute the download command - downloads a completed export."""
    api_host = get_api_host(args.api_host)
    session = create_http_session()
    # Don't auto-generate key for download - must use the key from the original export
    s3_config = build_s3_config(args, auto_generate_key=False)

    # Header
    print(f"\n{Colors.BOLD}Sekoia Event Exporter - Download{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")
    print(f"{Colors.BLUE}API Host:{Colors.RESET} {api_host}")
    print(f"{Colors.BLUE}Task UUID:{Colors.RESET} {args.task_uuid}\n")

    # Fetch task to get download URL
    try:
        data = fetch_task(args.task_uuid, session, api_host)
        task_status = data.get("status")

        if task_status != "FINISHED":
            print(f"{Colors.YELLOW}⚠{Colors.RESET} {Colors.BOLD}Export not ready yet{Colors.RESET}")
            print(f"{Colors.BOLD}Status:{Colors.RESET} {task_status}")

            total = data.get("total", 0) or 0
            progress_count = data.get("progress", 0) or 0
            if total > 0:
                progress = 100 * progress_count / total
                print(f"{Colors.BOLD}Progress:{Colors.RESET} {progress:.1f}% ({progress_count:,} / {total:,} events)")

            print(f"\n{Colors.DIM}Use 'sekoia-event-export status {args.task_uuid}' to monitor progress{Colors.RESET}")
            sys.exit(1)

        download_url = data.get("attributes", {}).get("download_url")
        if not download_url:
            print(f"{Colors.RED}✗{Colors.RESET} Export finished but no download URL found.")
            sys.exit(1)

        # Download the file
        try:
            download_file(download_url, output_filename=args.output, s3_config=s3_config)
        except Exception as e:
            print(f"\n{Colors.RED}✗ Download failed:{Colors.RESET} {e}", file=sys.stderr)
            print(f"{Colors.YELLOW}→{Colors.RESET} Manual download: {download_url}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"\n{Colors.RED}✗ Failed to fetch task:{Colors.RESET} {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Sekoia.io Event Exporter - Export search job results")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export search job results")
    export_parser.add_argument("job_uuid", help="The UUID of the search job to export")
    export_parser.add_argument("--api-host", type=str, default=None, help="API host (overrides API_HOST env var)")
    export_parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S, help="Polling interval in seconds")
    export_parser.add_argument("--max-wait", type=int, default=None, help="Max wait time in seconds (optional)")
    export_parser.add_argument("--no-download", action="store_true", help="Don't download the file, just print the URL")
    export_parser.add_argument("--output", "-o", type=str, default=None, help="Output filename for the downloaded file")
    export_parser.add_argument(
        "--fields",
        type=str,
        default=None,
        help="Comma-separated list of fields to export (default: message,timestamp, overrides EXPORT_FIELDS env var)",
    )

    # S3 Configuration
    s3_group = export_parser.add_argument_group("S3 Configuration", "Custom S3 settings for the export")
    s3_group.add_argument("--s3-bucket", type=str, help="S3 bucket name (overrides S3_BUCKET env var)")
    s3_group.add_argument("--s3-prefix", type=str, help="S3 key prefix (overrides S3_PREFIX env var)")
    s3_group.add_argument("--s3-access-key", type=str, help="S3 access key ID (overrides S3_ACCESS_KEY_ID env var)")
    s3_group.add_argument(
        "--s3-secret-key", type=str, help="S3 secret access key (overrides S3_SECRET_ACCESS_KEY env var)"
    )
    s3_group.add_argument("--s3-endpoint", type=str, help="S3 endpoint URL (overrides S3_ENDPOINT_URL env var)")
    s3_group.add_argument("--s3-region", type=str, help="S3 region name (overrides S3_REGION_NAME env var)")

    # SSE-C Encryption
    sse_group = export_parser.add_argument_group(
        "SSE-C Encryption", "Server-side encryption (enabled by default with auto-generated key)"
    )
    sse_group.add_argument(
        "--no-sse-c",
        action="store_true",
        help="Disable SSE-C encryption (encryption is enabled by default)",
    )
    sse_group.add_argument(
        "--s3-sse-c-key",
        type=str,
        help="SSE-C encryption key, base64 encoded (overrides S3_SSE_C_KEY env var, auto-generated if not provided)",
    )
    sse_group.add_argument(
        "--s3-sse-c-key-md5",
        type=str,
        help="SSE-C encryption key MD5, base64 encoded (auto-computed if not provided)",
    )
    sse_group.add_argument(
        "--s3-sse-c-algorithm",
        type=str,
        default=None,
        help="SSE-C algorithm (default: AES256)",
    )

    export_parser.set_defaults(func=cmd_export)

    status_parser = subparsers.add_parser("status", help="Check export task status (without downloading)")
    status_parser.add_argument("task_uuid", help="The UUID of the export task")
    status_parser.add_argument("--api-host", type=str, default=None, help="API host (overrides API_HOST env var)")

    status_parser.set_defaults(func=cmd_status)

    download_parser = subparsers.add_parser("download", help="Download a completed export")
    download_parser.add_argument("task_uuid", help="The UUID of the export task to download")
    download_parser.add_argument("--api-host", type=str, default=None, help="API host (overrides API_HOST env var)")
    download_parser.add_argument(
        "--output", "-o", type=str, default=None, help="Output filename for the downloaded file"
    )

    # SSE-C Encryption for download command (needed for downloading encrypted exports)
    download_sse_group = download_parser.add_argument_group(
        "SSE-C Encryption", "Encryption headers for download (exports are encrypted by default)"
    )
    download_sse_group.add_argument(
        "--no-sse-c",
        action="store_true",
        help="Don't use SSE-C headers for download (use if export was created with --no-sse-c)",
    )
    download_sse_group.add_argument(
        "--s3-sse-c-key",
        type=str,
        help="SSE-C encryption key used during export, base64 encoded (overrides S3_SSE_C_KEY env var)",
    )
    download_sse_group.add_argument(
        "--s3-sse-c-key-md5",
        type=str,
        help="SSE-C encryption key MD5, base64 encoded (auto-computed if not provided)",
    )
    download_sse_group.add_argument(
        "--s3-sse-c-algorithm",
        type=str,
        default=None,
        help="SSE-C algorithm (default: AES256)",
    )

    download_parser.set_defaults(func=cmd_download)

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
