# Sekoia.io Event Exporter

[![CI](https://github.com/sekoia-io/sekoia-event-exporter/actions/workflows/ci.yml/badge.svg)](https://github.com/sekoia-io/sekoia-event-exporter/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/sekoia-event-exporter.svg)](https://pypi.org/project/sekoia-event-exporter/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python CLI tool to export search job results from the Sekoia.io API.

## Features

- **Secure by default**: All exports are automatically encrypted with SSE-C
- Export search job results with a single command
- Automatic file download when exports complete
- Monitor export progress with real-time updates and ETA
- Check status of existing export tasks
- Configurable polling intervals and timeouts
- Custom S3 bucket support with full encryption control

## Installation

### From PyPI

The easiest way to install is from PyPI:

```bash
pip install sekoia-event-exporter
```

Or using [uv](https://docs.astral.sh/uv/) for faster installation:

```bash
uv pip install sekoia-event-exporter
```

### From Source

If you want to install from source or contribute to the project:

```bash
# Clone the repository
git clone https://github.com/sekoia-io/sekoia-event-exporter.git
cd sekoia-event-exporter

# Install with uv (recommended)
uv sync

# Or with pip
pip install .
```

### For Development

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install with all development dependencies
uv sync --all-extras

# Or using pip
pip install -e ".[dev]"
```

## Configuration

### API Key

The tool requires a Sekoia.io API key to authenticate requests. Set it as an environment variable:

```bash
export API_KEY="your-sekoia-api-key-here"
```

Alternatively, you can create a `.env` file in your working directory:

```bash
API_KEY=your-sekoia-api-key-here
```

### Region Configuration

Sekoia.io operates multiple regional instances. By default, the tool uses the European region (`api.sekoia.io`). To use a different region, you can configure the API host in one of three ways:

**Option 1: Environment Variable**

```bash
export API_HOST="api.usa1.sekoia.io"  # For USA1 region
```

Or in your `.env` file:

```bash
API_HOST=api.usa1.sekoia.io
```

**Option 2: Command-Line Argument**

```bash
sekoia-event-export export <job_uuid> --api-host api.usa1.sekoia.io
sekoia-event-export status <task_uuid> --api-host api.usa1.sekoia.io
```

**Option 3: Default**

If neither is specified, the tool uses `api.sekoia.io` (European region).

For the complete list of available regions and their API endpoints, see the [Sekoia.io Regions Documentation](https://docs.sekoia.io/getting_started/regions/).

### Custom S3 Configuration and SSE-C Encryption

**⚠️ IMPORTANT: Exports are encrypted by default!**

All exports are automatically encrypted with SSE-C (Server-Side Encryption with Customer-Provided Keys) using an auto-generated encryption key. **You must save this key** to download your export later.

You can also configure custom S3 settings for your exports:

- Export to your own S3 bucket
- Use your own SSE-C encryption key
- Customize S3 endpoint, region, and credentials

**Default Behavior: Auto-Generated Encryption**

By default, the tool generates a random 256-bit encryption key for each export:

```bash
# Encryption is automatic - the tool will display the generated key
sekoia-event-export export <job_uuid>
```

Output:
```
================================================================================
⚠️  SSE-C ENCRYPTION KEY AUTO-GENERATED
================================================================================
Encryption Key: dGhpc2lzYW5leGFtcGxla2V5Zm9ydGVzdGluZzEyMzQ1Njc4

⚠️  IMPORTANT: Save this key securely!
   You will need it to download this export later.
   If you lose this key, you will NOT be able to decrypt your data.
================================================================================
```

**Using Your Own Encryption Key**

To use a specific key instead of auto-generation:

```bash
# Generate your own key
export S3_SSE_C_KEY=$(openssl rand -base64 32)
echo "Your encryption key (save this securely): $S3_SSE_C_KEY"

# Use it for export
sekoia-event-export export <job_uuid>

# Or provide it directly
sekoia-event-export export <job_uuid> --s3-sse-c-key "<your-base64-encoded-key>"
```

**Disabling Encryption**

To disable SSE-C encryption (not recommended):

```bash
sekoia-event-export export <job_uuid> --no-sse-c
```

**Full S3 Configuration**

For complete control over S3 settings, you can configure multiple parameters:

```bash
# Using environment variables
export S3_BUCKET="my-export-bucket"
export S3_PREFIX="exports/"
export S3_ACCESS_KEY_ID="<access-key>"
export S3_SECRET_ACCESS_KEY="<secret-key>"
export S3_ENDPOINT_URL="https://s3.amazonaws.com"
export S3_REGION_NAME="us-east-1"
export S3_SSE_C_KEY="<base64-key>"

sekoia-event-export export <job_uuid>
```

Or using command-line arguments:

```bash
sekoia-event-export export <job_uuid> \
  --s3-bucket my-export-bucket \
  --s3-prefix exports/ \
  --s3-access-key <access-key> \
  --s3-secret-key <secret-key> \
  --s3-endpoint https://s3.amazonaws.com \
  --s3-region us-east-1 \
  --s3-sse-c-key <base64-key>
```

**Automatic Download with SSE-C**

When using SSE-C encryption, the tool automatically includes the required encryption headers when downloading. The same key used for export is automatically applied to the download.

If you need to manually download later with `curl`:

```bash
curl "<download-url>" \
  -H "x-amz-server-side-encryption-customer-algorithm: AES256" \
  -H "x-amz-server-side-encryption-customer-key: <base64-key>" \
  -H "x-amz-server-side-encryption-customer-key-MD5: <base64-md5>" \
  -o export.json.gz
```

**Generating SSE-C Keys**

SSE-C requires a 256-bit (32-byte) encryption key encoded in base64. Here are several ways to generate one:

**Using OpenSSL (recommended):**
```bash
# Generate a random 256-bit key and encode to base64
openssl rand -base64 32
```

**Using Python:**
```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

**Using /dev/urandom (Linux/macOS):**
```bash
head -c 32 /dev/urandom | base64
```

**Example output:**
```
dGhpc2lzYW5leGFtcGxla2V5Zm9ydGVzdGluZzEyMzQ1Njc4
```

**Important:** Store this key securely! You'll need the same key to download encrypted exports. If you lose the key, you won't be able to decrypt your data.

## Usage

### Export Search Job Results

Trigger an export for a specific search job, monitor its progress, and automatically download the file:

```bash
sekoia-event-export export <job_uuid>
```

Example:

```bash
sekoia-event-export export 550e8400-e29b-41d4-a716-446655440000
```

**The export will be automatically downloaded when ready.** The file is saved as `export_YYYYMMDD_HHMMSS.json.gz` by default.

**Custom output filename:**

```bash
sekoia-event-export export <job_uuid> --output my-export.json.gz
# or using short form
sekoia-event-export export <job_uuid> -o my-export.json.gz
```

**Disable auto-download (just get the URL):**

```bash
sekoia-event-export export <job_uuid> --no-download
```

**With custom polling interval and timeout:**

```bash
sekoia-event-export export <job_uuid> --interval 5 --max-wait 3600
```

### Check Export Status

Check the status of an already-triggered export task and download when ready:

```bash
sekoia-event-export status <task_uuid>
```

Example:

```bash
sekoia-event-export status 660e8400-e29b-41d4-a716-446655440001
```

**The file will be automatically downloaded when the task completes.**

**Important:** If the export was encrypted (default behavior), you must provide the same encryption key used during export:

```bash
# Provide the key that was displayed when you created the export
sekoia-event-export status <task_uuid> --s3-sse-c-key "<base64-key>"
```

Or set it as an environment variable:

```bash
export S3_SSE_C_KEY="<base64-key-from-export>"
sekoia-event-export status <task_uuid>
```

**Note:** The status command does NOT auto-generate a key. You must provide the exact key that was used (or auto-generated) when the export was created.

### Command Options

#### `export` command

**Basic Options:**
- `job_uuid` (required): The UUID of the search job to export
- `--api-host`: API host to use (overrides API_HOST env var, default: api.sekoia.io)
- `--interval`: Polling interval in seconds (default: 2)
- `--max-wait`: Maximum wait time in seconds (default: no limit)
- `--no-download`: Don't download the file, just print the URL
- `--output`, `-o`: Output filename for the downloaded file (default: export_YYYYMMDD_HHMMSS.json.gz)

**S3 Configuration:**
- `--s3-bucket`: S3 bucket name (overrides S3_BUCKET env var)
- `--s3-prefix`: S3 key prefix (overrides S3_PREFIX env var)
- `--s3-access-key`: S3 access key ID (overrides S3_ACCESS_KEY_ID env var)
- `--s3-secret-key`: S3 secret access key (overrides S3_SECRET_ACCESS_KEY env var)
- `--s3-endpoint`: S3 endpoint URL (overrides S3_ENDPOINT_URL env var)
- `--s3-region`: S3 region name (overrides S3_REGION_NAME env var)

**SSE-C Encryption (enabled by default):**
- `--no-sse-c`: Disable SSE-C encryption (encryption is enabled by default)
- `--s3-sse-c-key`: SSE-C encryption key, base64 encoded (auto-generated if not provided, overrides S3_SSE_C_KEY env var)
- `--s3-sse-c-key-md5`: SSE-C key MD5, base64 encoded (auto-computed if not provided)
- `--s3-sse-c-algorithm`: SSE-C algorithm (default: AES256)

#### `status` command

**Basic Options:**
- `task_uuid` (required): The UUID of the export task to check
- `--api-host`: API host to use (overrides API_HOST env var, default: api.sekoia.io)
- `--interval`: Polling interval in seconds (default: 2)
- `--max-wait`: Maximum wait time in seconds (default: no limit)
- `--no-download`: Don't download the file, just print the URL
- `--output`, `-o`: Output filename for the downloaded file (default: export_YYYYMMDD_HHMMSS.json.gz)

**SSE-C Encryption (exports are encrypted by default):**
- `--no-sse-c`: Don't use SSE-C headers for download (use only if export was created with --no-sse-c)
- `--s3-sse-c-key`: SSE-C encryption key used during export, base64 encoded (required if export was encrypted, overrides S3_SSE_C_KEY env var)
- `--s3-sse-c-key-md5`: SSE-C key MD5, base64 encoded (auto-computed if not provided)
- `--s3-sse-c-algorithm`: SSE-C algorithm (default: AES256)

**Note:** Unlike the export command, status does NOT auto-generate keys. You must provide the same key that was used when creating the export.

### Progress Monitoring

The tool provides real-time progress updates when monitoring export tasks and automatically downloads when ready:

```
Export task triggered with UUID: 660e8400-e29b-41d4-a716-446655440001
14:32:15 25.50% (2550/10000) completed... ETA: 14:38:42 (status=RUNNING)
14:32:17 26.00% (2600/10000) completed... ETA: 14:38:40 (status=RUNNING)
...
Export ready! Download URL: https://api.sekoia.io/v1/files/abc123/download
Downloading to: export_20260214_143842.json.gz
Progress: 100.0% (15728640/15728640 bytes)
Download complete: export_20260214_143842.json.gz (15728640 bytes)
```

If SSE-C encryption is enabled, the download automatically includes the required encryption headers.

## Error Handling

The tool provides clear error messages for common issues:

- **Missing API Key**: `Config error: API_KEY environment variable not set.`
- **Failed Export**: `Failed to trigger export: 403 Forbidden`
- **Task Timeout**: `Timed out after 3600s waiting for task <uuid>`
- **Task Failed**: `Task ended with status=FAILED. Details: ...`

Exit codes:
- `0`: Success
- `1`: General error
- `2`: Configuration error
- `130`: Interrupted by user (Ctrl+C)

## Development

### Running Tests

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=sekoia_event_exporter --cov-report=html
```

### Code Formatting

```bash
# Format code with black
uv run black src/ tests/

# Check formatting without changes
uv run black --check src/ tests/

# Lint with ruff
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/

# Type check with mypy
uv run mypy src/
```

### Running All Quality Checks

```bash
# Run all checks at once
uv run black --check src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run mypy src/ && \
uv run pytest
```

### Project Structure

```
sekoia-event-exporter/
├── src/
│   └── sekoia_event_exporter/
│       ├── __init__.py       # Package metadata and exports
│       └── cli.py            # Main CLI implementation
├── tests/
│   └── __init__.py
├── examples/
│   └── .env.example          # Example environment configuration
├── pyproject.toml            # Project metadata and dependencies
├── README.md                 # This file
├── LICENSE                   # MIT License
└── .gitignore               # Git ignore patterns
```

## API Reference

### Core Functions

#### `create_http_session() -> requests.Session`

Creates an authenticated HTTP session using the `API_KEY` environment variable.

**Raises:**
- `ConfigError`: If `API_KEY` is not set

#### `trigger_export(job_uuid: str, session: requests.Session) -> str`

Triggers an export job for the specified search job UUID.

**Parameters:**
- `job_uuid`: UUID of the search job to export
- `session`: Authenticated requests session

**Returns:**
- Task UUID for the triggered export

**Raises:**
- `RuntimeError`: If the export fails to trigger

#### `poll_status(task_uuid: str, session: requests.Session, interval_s: int = 2, max_wait_s: Optional[int] = None) -> None`

Polls the export task status until completion or timeout.

**Parameters:**
- `task_uuid`: UUID of the export task
- `session`: Authenticated requests session
- `interval_s`: Polling interval in seconds (default: 2)
- `max_wait_s`: Maximum wait time in seconds (default: None)

**Raises:**
- `TimeoutError`: If max_wait_s is exceeded
- `RuntimeError`: If task fails or is cancelled

## Requirements

- Python 3.10 or higher
- requests >= 2.28.0

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please visit:
- **Issues**: https://github.com/sekoia-io/sekoia-event-exporter/issues
- **Documentation**: https://docs.sekoia.io

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes to this project.
