# Sekoia.io Event Exporter

[![CI](https://github.com/sekoia-io/sekoia-event-exporter/actions/workflows/ci.yml/badge.svg)](https://github.com/sekoia-io/sekoia-event-exporter/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python CLI tool to export search job results from the Sekoia.io API.

## Features

- Export search job results with a single command
- Monitor export progress with real-time updates and ETA
- Check status of existing export tasks
- Configurable polling intervals and timeouts
- Clean, modern Python package with full type hints

## Installation

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management. Install uv first:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### From Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/sekoia-io/sekoia-event-exporter.git
cd sekoia-event-exporter

# Install the package with uv
uv sync
```

### For Development

```bash
# Install with all development dependencies
uv sync --all-extras

# Run commands with uv
uv run sekoia-event-export --help
```

### Alternative: Using pip

```bash
# Install from source
pip install .

# Or in editable mode with development dependencies
pip install -e ".[dev]"
```

### From PyPI (once published)

```bash
uv pip install sekoia-event-exporter
# or with pip
pip install sekoia-event-exporter
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
export API_HOST="api.us.sekoia.io"  # For US region
```

Or in your `.env` file:

```bash
API_HOST=api.us.sekoia.io
```

**Option 2: Command-Line Argument**

```bash
sekoia-event-export export <job_uuid> --api-host api.us.sekoia.io
sekoia-event-export status <task_uuid> --api-host api.us.sekoia.io
```

**Option 3: Default**

If neither is specified, the tool uses `api.sekoia.io` (European region).

For the complete list of available regions and their API endpoints, see the [Sekoia.io Regions Documentation](https://docs.sekoia.io/getting_started/regions/).

## Usage

### Export Search Job Results

Trigger an export for a specific search job and monitor its progress:

```bash
sekoia-event-export export <job_uuid>
```

Example:

```bash
sekoia-event-export export 550e8400-e29b-41d4-a716-446655440000
```

With custom polling interval and timeout:

```bash
sekoia-event-export export <job_uuid> --interval 5 --max-wait 3600
```

### Check Export Status

Check the status of an already-triggered export task:

```bash
sekoia-event-export status <task_uuid>
```

Example:

```bash
sekoia-event-export status 660e8400-e29b-41d4-a716-446655440001
```

### Command Options

#### `export` command

- `job_uuid` (required): The UUID of the search job to export
- `--api-host`: API host to use (overrides API_HOST env var, default: api.sekoia.io)
- `--interval`: Polling interval in seconds (default: 2)
- `--max-wait`: Maximum wait time in seconds (default: no limit)

#### `status` command

- `task_uuid` (required): The UUID of the export task to check
- `--api-host`: API host to use (overrides API_HOST env var, default: api.sekoia.io)
- `--interval`: Polling interval in seconds (default: 2)
- `--max-wait`: Maximum wait time in seconds (default: no limit)

### Progress Monitoring

The tool provides real-time progress updates when monitoring export tasks:

```
Export task triggered with UUID: 660e8400-e29b-41d4-a716-446655440001
14:32:15 25.50% (2550/10000) completed... ETA: 14:38:42 (status=RUNNING)
14:32:17 26.00% (2600/10000) completed... ETA: 14:38:40 (status=RUNNING)
...
Export ready! Download URL: https://api.sekoia.io/v1/files/abc123/download
```

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

- Python 3.8 or higher
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

### 0.1.0 (Initial Release)

- Initial implementation of export and status commands
- Real-time progress monitoring with ETA
- Comprehensive error handling
- Modern Python package structure
