# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Replaced Black with Ruff for code formatting (Ruff now handles both linting and formatting)
- Updated Ruff target version to Python 3.10 (matching project minimum version)

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet

## [0.5.0] - 2026-02-15

### Added
- **Field selection**: Specify which fields to export with `--fields` option (defaults to `message,timestamp` only)
- **New `download` command**: Dedicated command to download completed exports
- Visual progress bars with Unicode characters (█░) for export and download operations
- Color-coded output with ANSI colors (automatically disabled for non-TTY environments)
- Download speed indicator (MB/s) during file downloads
- Human-readable file size formatting (KB, MB, GB)
- Animated spinner for exports with unknown progress
- Formatted time deltas (e.g., "2m 30s", "1h 15m")
- Improved header display with visual separators
- `EXPORT_FIELDS` environment variable support for default field selection

### Changed
- **BREAKING**: `status` command no longer downloads files automatically - use the new `download` command instead
- **BREAKING**: `status` command now performs a single status check instead of polling continuously
- **BREAKING**: Default export fields changed to only `message` and `timestamp` (was all fields)
- Added documentation clarifying that API key only requires "Massive export of events" permission
- Export progress now updates on a single line instead of scrolling
- Download progress shows real-time speed and remaining time
- Enhanced visual feedback with checkmarks (✓), warnings (⚠), and color coding
- Progress bars change color based on completion (red < 33%, yellow < 66%, green ≥ 66%)
- Time estimates now calculate remaining time based on observed progress rate between polls (not elapsed time)
- Display shows "⏱ 2m 30s remaining" instead of "ETA: 14:38:42" for clarity
- Better formatting for encryption key warnings with visual separators
- `status` command now displays download URL and suggests using `download` command

### Fixed
- Time remaining estimates are now accurate when restarting the status command mid-export
- Remaining time calculation now based on actual progress rate, not command start time

## [0.4.0] - 2026-02-15

### Added
- **Automatic SSE-C encryption by default**: All exports are now encrypted with auto-generated 256-bit keys
- **Automatic file download**: Exports are automatically downloaded when ready with progress indicators
- **Custom S3 configuration support**: Full control over S3 settings including bucket, endpoint, region, and credentials
- **SSE-C encryption with customer-provided keys**: Support for server-side encryption with custom keys
- **Auto-generated encryption keys**: Tool generates cryptographically secure keys when none provided
- **Automatic MD5 computation**: SSE-C key MD5 hashes are automatically computed
- `--no-sse-c` flag to disable encryption when needed
- `--no-download` flag to skip automatic download and only display URL
- `--output` / `-o` flag to specify custom output filename for downloads
- `--s3-bucket`, `--s3-prefix`, `--s3-access-key`, `--s3-secret-key`, `--s3-endpoint`, `--s3-region` flags for custom S3 configuration
- `--s3-sse-c-key`, `--s3-sse-c-key-md5`, `--s3-sse-c-algorithm` flags for SSE-C encryption control
- Environment variable support for all S3 and SSE-C settings
- Prominent warnings when encryption keys are auto-generated, reminding users to save them
- Comprehensive documentation on SSE-C encryption and key generation
- Multiple methods for generating SSE-C keys (OpenSSL, Python, /dev/urandom)
- Streaming download with progress indicator for large files
- PyPI badge in README

### Changed
- Updated documentation to reflect PyPI availability
- Reorganized README installation section with PyPI as primary method
- Enhanced SSE-C documentation with security warnings and best practices
- Updated help text for all commands to clarify encryption defaults

### Fixed
- HTTP 400 error when downloading files from pre-signed S3 URLs (removed conflicting Authorization header)
- SSE-C key validation now ensures keys are exactly 32 bytes (256 bits)
- Display logic now correctly shows encryption status only when actually configured
- Status command no longer auto-generates keys (requires key from original export)

### Security
- **Encryption enabled by default**: All exports are now encrypted with SSE-C unless explicitly disabled
- Automatic generation of cryptographically secure 256-bit encryption keys using `os.urandom()`
- Clear warnings about key loss and inability to decrypt data without the key
- Validation of SSE-C keys to ensure they meet AWS S3 requirements (32 bytes)

## [0.3.0] - 2026-02-14

### Added
- Added `--version` flag to display package version
- Added `see` command alias as a shorter alternative to `sekoia-event-export`

## [0.2.0] - 2026-02-14

### Changed
- Migrated PyPI publishing workflow to use official PyPA `pypi-publish` action
- Enabled trusted publishing via OIDC for enhanced security (no API tokens required)
- Improved GitHub Actions workflow for more reliable package publishing
- **BREAKING**: Dropped Python 3.9 support, now requires Python 3.10+ (for native union type syntax)

## [0.1.0] - 2026-02-10

### Added
- Initial release of sekoia-event-exporter
- CLI command `sekoia-event-export` with two subcommands:
  - `export`: Trigger and monitor export jobs for search results
  - `status`: Check the status of existing export tasks
- Real-time progress monitoring with ETA calculations
- Multi-region support with configurable API host
  - Environment variable `API_HOST` for region configuration
  - Command-line argument `--api-host` for runtime override
  - Defaults to European region (`api.sekoia.io`)
- Support for Python 3.8, 3.9, 3.10, 3.11, and 3.12
- Comprehensive documentation:
  - README with installation and usage instructions
  - CONTRIBUTING guide for developers
  - PUBLISHING guide for package maintainers
  - API reference documentation
- Modern Python package structure:
  - `src/` layout for clean package organization
  - `pyproject.toml` for package configuration
  - `uv.lock` for reproducible builds
- Development tools integration:
  - Black for code formatting
  - Ruff for linting
  - MyPy for type checking
  - Pytest for testing with coverage
- GitHub Actions CI/CD workflows:
  - Automated testing on pull requests
  - Code quality checks (black, ruff, mypy)
  - Matrix testing across Python versions
  - Automated PyPI publishing on releases
- Configuration options:
  - `--interval`: Customizable polling interval
  - `--max-wait`: Optional timeout for operations
- Example scripts and configuration files
- Issue and pull request templates
- Comprehensive test suite

### Security
- API key authentication via `API_KEY` environment variable
- No credentials stored in code or configuration files

[Unreleased]: https://github.com/sekoia-io/sekoia-event-exporter/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/sekoia-io/sekoia-event-exporter/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/sekoia-io/sekoia-event-exporter/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/sekoia-io/sekoia-event-exporter/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/sekoia-io/sekoia-event-exporter/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sekoia-io/sekoia-event-exporter/releases/tag/v0.1.0
