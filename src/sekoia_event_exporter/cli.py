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


class ConfigError(RuntimeError):
    """Configuration error exception."""

    pass


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

    print(f"Downloading to: {output_filename}")
    if headers:
        print("Using SSE-C encryption headers for download")

    try:
        resp = requests.get(download_url, headers=headers, stream=True, timeout=(5, 60))
        resp.raise_for_status()

        # Get total size if available
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(output_filename, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rProgress: {progress:.1f}% ({downloaded}/{total_size} bytes)", end="")

        if total_size > 0:
            print()  # New line after progress
        print(f"Download complete: {output_filename} ({downloaded} bytes)")
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
            return download_url

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
    s3_config = build_s3_config(args)

    print(f"Using API host: {api_host}")
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
                print(f"Using custom S3 configuration: {', '.join(display_keys)}")

        if has_sse_c:
            if generated_key:
                print("\n" + "=" * 80)
                print("⚠️  SSE-C ENCRYPTION KEY AUTO-GENERATED")
                print("=" * 80)
                print(f"Encryption Key: {generated_key}")
                print("\n⚠️  IMPORTANT: Save this key securely!")
                print("   You will need it to download this export later.")
                print("   If you lose this key, you will NOT be able to decrypt your data.")
                print("=" * 80 + "\n")
            else:
                print("SSE-C encryption enabled")

    task_uuid = trigger_export(args.job_uuid, session, api_host, s3_config=s3_config)
    print(f"Export task triggered with UUID: {task_uuid}")

    download_url = poll_status(task_uuid, session, api_host, interval_s=args.interval, max_wait_s=args.max_wait)

    # Download the file if URL is available and download is not disabled
    if download_url and not args.no_download:
        try:
            download_file(download_url, output_filename=args.output, s3_config=s3_config)
        except Exception as e:
            print(f"Warning: Download failed: {e}", file=sys.stderr)
            print(f"You can manually download from: {download_url}", file=sys.stderr)


def cmd_status(args) -> None:
    """Execute the status command."""
    api_host = get_api_host(args.api_host)
    session = create_http_session()
    # Don't auto-generate key for status - must use the key from the original export
    s3_config = build_s3_config(args, auto_generate_key=False)

    print(f"Using API host: {api_host}")
    if s3_config:
        # Check if encryption key was auto-generated
        generated_key = s3_config.pop("_generated_key", None)

        if "sse_customer_key" in s3_config:
            if generated_key:
                print("\n" + "=" * 80)
                print("⚠️  SSE-C ENCRYPTION KEY AUTO-GENERATED")
                print("=" * 80)
                print(f"Encryption Key: {generated_key}")
                print("\n⚠️  IMPORTANT: Save this key securely!")
                print("   This key was auto-generated for downloading the encrypted export.")
                print("   If the export was encrypted with a different key, provide it with --s3-sse-c-key")
                print("=" * 80 + "\n")
            else:
                print("SSE-C encryption headers configured for download")

    download_url = poll_status(args.task_uuid, session, api_host, interval_s=args.interval, max_wait_s=args.max_wait)

    # Download the file if URL is available and download is not disabled
    if download_url and not args.no_download:
        try:
            download_file(download_url, output_filename=args.output, s3_config=s3_config)
        except Exception as e:
            print(f"Warning: Download failed: {e}", file=sys.stderr)
            print(f"You can manually download from: {download_url}", file=sys.stderr)


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

    status_parser = subparsers.add_parser("status", help="Check export job status")
    status_parser.add_argument("task_uuid", help="The UUID of the export task")
    status_parser.add_argument("--api-host", type=str, default=None, help="API host (overrides API_HOST env var)")
    status_parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S, help="Polling interval in seconds")
    status_parser.add_argument("--max-wait", type=int, default=None, help="Max wait time in seconds (optional)")
    status_parser.add_argument("--no-download", action="store_true", help="Don't download the file, just print the URL")
    status_parser.add_argument("--output", "-o", type=str, default=None, help="Output filename for the downloaded file")

    # SSE-C Encryption for status command (needed for downloading encrypted exports)
    status_sse_group = status_parser.add_argument_group(
        "SSE-C Encryption", "Encryption headers for download (exports are encrypted by default)"
    )
    status_sse_group.add_argument(
        "--no-sse-c",
        action="store_true",
        help="Don't use SSE-C headers for download (use if export was created with --no-sse-c)",
    )
    status_sse_group.add_argument(
        "--s3-sse-c-key",
        type=str,
        help="SSE-C encryption key, base64 encoded (overrides S3_SSE_C_KEY env var, auto-generated if not provided)",
    )
    status_sse_group.add_argument(
        "--s3-sse-c-key-md5",
        type=str,
        help="SSE-C encryption key MD5, base64 encoded (auto-computed if not provided)",
    )
    status_sse_group.add_argument(
        "--s3-sse-c-algorithm",
        type=str,
        default=None,
        help="SSE-C algorithm (default: AES256)",
    )

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
