#!/usr/bin/env python3
"""
Example script showing how to use sekoia-event-exporter programmatically.

This example demonstrates how to use the library functions directly
instead of using the CLI, including region configuration.
"""

import os
from sekoia_event_exporter.cli import (
    create_http_session,
    trigger_export,
    poll_status,
    get_api_host,
    ConfigError
)


def main():
    """Main example function."""
    # Make sure API_KEY is set
    if not os.getenv("API_KEY"):
        print("Error: Please set the API_KEY environment variable")
        print("export API_KEY='your-api-key-here'")
        return

    # Example job UUID (replace with your actual job UUID)
    job_uuid = "550e8400-e29b-41d4-a716-446655440000"

    # Configure the API host (region)
    # Option 1: Use environment variable (API_HOST) - recommended
    # Option 2: Pass it directly to get_api_host()
    # Option 3: Use default (api.sekoia.io)

    # Example: Override to use US region
    # api_host = get_api_host("api.us.sekoia.io")

    # Example: Use environment variable or default
    api_host = get_api_host()
    print(f"Using API host: {api_host}")

    try:
        # Create an authenticated session
        print("Creating HTTP session...")
        session = create_http_session()

        # Trigger the export
        print(f"Triggering export for job {job_uuid}...")
        task_uuid = trigger_export(job_uuid, session, api_host)
        print(f"Export triggered! Task UUID: {task_uuid}")

        # Poll for completion
        print("Waiting for export to complete...")
        poll_status(
            task_uuid,
            session,
            api_host,
            interval_s=2,  # Check every 2 seconds
            max_wait_s=600  # Wait up to 10 minutes
        )

        print("Export complete!")

    except ConfigError as e:
        print(f"Configuration error: {e}")
    except TimeoutError as e:
        print(f"Timeout: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
