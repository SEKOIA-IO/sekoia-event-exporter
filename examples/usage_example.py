#!/usr/bin/env python3
"""
Example script showing how to use sekoia-event-exporter programmatically.

This example demonstrates how to use the library functions directly
instead of using the CLI, including region configuration and S3 settings.
"""

import os

from sekoia_event_exporter.cli import ConfigError, create_http_session, get_api_host, poll_status, trigger_export


def basic_export_example():
    """Example: Basic export without custom S3 settings.

    Note: This shows the low-level API. When using the CLI, downloads happen automatically.
    """
    print("\n=== Basic Export Example ===\n")

    job_uuid = "550e8400-e29b-41d4-a716-446655440000"
    api_host = get_api_host()

    print(f"Using API host: {api_host}")

    session = create_http_session()
    task_uuid = trigger_export(job_uuid, session, api_host)
    print(f"Export triggered! Task UUID: {task_uuid}")

    download_url = poll_status(task_uuid, session, api_host, interval_s=2, max_wait_s=600)
    if download_url:
        print(f"\nExport complete! Download URL: {download_url}")
        print("\nNote: The CLI automatically downloads the file.")
        print("      This example just shows the low-level API.")


def sse_c_export_example():
    """Example: Export with SSE-C encryption.

    Note: The CLI automatically handles SSE-C headers when downloading.
    """
    print("\n=== SSE-C Encrypted Export Example ===\n")

    job_uuid = "550e8400-e29b-41d4-a716-446655440000"
    api_host = get_api_host()

    # Configure SSE-C encryption
    # Generate a key with: openssl rand -base64 32
    s3_config = {
        "sse_customer_key": "<your-base64-encoded-256-bit-key>",
        "sse_customer_algorithm": "AES256",
        # MD5 is optional - it will be auto-computed if not provided
        "sse_customer_key_md5": "<base64-encoded-md5-of-key>",
    }

    print(f"Using API host: {api_host}")
    print("SSE-C encryption enabled")

    session = create_http_session()
    task_uuid = trigger_export(job_uuid, session, api_host, s3_config=s3_config)
    print(f"Export triggered! Task UUID: {task_uuid}")

    download_url = poll_status(task_uuid, session, api_host, interval_s=2, max_wait_s=600)
    if download_url:
        print(f"\nExport complete! Download URL: {download_url}")
        print("\nNote: The CLI automatically downloads with SSE-C headers.")
        print("      If you need to manually download, use these headers:")
        print('  -H "x-amz-server-side-encryption-customer-algorithm: AES256"')
        print('  -H "x-amz-server-side-encryption-customer-key: <base64-key>"')
        print('  -H "x-amz-server-side-encryption-customer-key-MD5: <base64-md5>"')


def custom_s3_export_example():
    """Example: Export to custom S3 bucket with SSE-C.

    Note: The CLI automatically handles downloads with custom S3 settings.
    """
    print("\n=== Custom S3 Bucket with SSE-C Example ===\n")

    job_uuid = "550e8400-e29b-41d4-a716-446655440000"
    api_host = get_api_host()

    # Full S3 configuration with SSE-C
    s3_config = {
        "bucket_name": "my-export-bucket",
        "prefix": "exports/",
        "access_key_id": os.getenv("S3_ACCESS_KEY_ID"),
        "secret_access_key": os.getenv("S3_SECRET_ACCESS_KEY"),
        "endpoint_url": "https://s3.amazonaws.com",
        "region_name": "us-east-1",
        "sse_customer_key": os.getenv("S3_SSE_C_KEY"),
        "sse_customer_algorithm": "AES256",
    }

    print(f"Using API host: {api_host}")
    print(f"Custom S3 bucket: {s3_config['bucket_name']}")
    print("SSE-C encryption enabled")

    session = create_http_session()
    task_uuid = trigger_export(job_uuid, session, api_host, s3_config=s3_config)
    print(f"Export triggered! Task UUID: {task_uuid}")

    download_url = poll_status(task_uuid, session, api_host, interval_s=2, max_wait_s=600)
    if download_url:
        print(f"\nExport complete! Download URL: {download_url}")
        print("\nNote: The CLI automatically downloads with the proper S3 configuration.")


def main():
    """Main example function."""
    # Make sure API_KEY is set
    if not os.getenv("API_KEY"):
        print("Error: Please set the API_KEY environment variable")
        print("export API_KEY='your-api-key-here'")
        return

    try:
        # Run different examples based on what you want to demonstrate
        # Uncomment the example you want to run:

        # Example 1: Basic export
        basic_export_example()

        # Example 2: Export with SSE-C encryption (uncomment to use)
        # sse_c_export_example()

        # Example 3: Export to custom S3 bucket with SSE-C (uncomment to use)
        # custom_s3_export_example()

    except ConfigError as e:
        print(f"Configuration error: {e}")
    except TimeoutError as e:
        print(f"Timeout: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
