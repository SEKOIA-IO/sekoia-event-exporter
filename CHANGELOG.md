# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet

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

[Unreleased]: https://github.com/sekoia-io/sekoia-event-exporter/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sekoia-io/sekoia-event-exporter/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sekoia-io/sekoia-event-exporter/releases/tag/v0.1.0
