# Contributing to Sekoia.io Event Exporter

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- git

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Setting Up Your Development Environment

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/sekoia-event-exporter.git
cd sekoia-event-exporter
```

2. **Install dependencies with uv (recommended)**

```bash
# Install all dependencies including dev extras
uv sync --all-extras
```

**Alternative: Using pip and venv**

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

3. **Set up your API key for testing**

```bash
cp examples/.env.example .env
# Edit .env and add your API key
```

## Development Workflow

### Running Tests

Using uv (recommended):

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=sekoia_event_exporter --cov-report=html

# Run specific test file
uv run pytest tests/test_cli.py

# Run with verbose output
uv run pytest -v
```

Without uv (if using pip/venv):

```bash
pytest
pytest --cov=sekoia_event_exporter --cov-report=html
```

### Code Quality

We use several tools to maintain code quality:

Using uv (recommended):

```bash
# Format code with black
uv run black src/ tests/

# Check formatting without making changes
uv run black --check src/ tests/

# Lint with ruff
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/

# Type check with mypy
uv run mypy src/
```

Without uv:

```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Before Committing

Make sure to run all quality checks:

Using uv:

```bash
# Run all checks at once
uv run black --check src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run mypy src/ && \
uv run pytest
```

Without uv:

```bash
black src/ tests/ && ruff check src/ tests/ && mypy src/ && pytest
```

## Contribution Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write descriptive docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 120 characters

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Keep the first line under 72 characters
- Add detailed explanation in the commit body if needed

Example:
```
Add support for custom API host configuration

- Allow users to specify a custom API host via environment variable
- Update documentation with new configuration option
- Add tests for custom host functionality
```

### Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
   - Write clean, well-documented code
   - Add or update tests as needed
   - Update documentation if you're changing functionality
   - Add an entry to `CHANGELOG.md` under the `[Unreleased]` section:
     - **Added**: for new features
     - **Changed**: for changes in existing functionality
     - **Deprecated**: for soon-to-be removed features
     - **Removed**: for now removed features
     - **Fixed**: for any bug fixes
     - **Security**: for vulnerability fixes

3. **Test your changes**

With uv:

```bash
uv run pytest
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
```

Without uv:

```bash
pytest
black src/ tests/
ruff check src/ tests/
mypy src/
```

4. **Commit your changes**

```bash
git add .
git commit -m "Your descriptive commit message"
```

5. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

6. **Open a Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your feature branch
   - Fill in the PR template with:
     - Description of changes
     - Motivation and context
     - How to test
     - Related issues (if any)

7. **CI Checks**

   When you open a pull request, automated CI checks will run:

   - **Tests**: Runs test suite on Python 3.10, 3.11, 3.12, and 3.13
   - **Code Quality**: Checks formatting (black), linting (ruff), and type hints (mypy)
   - **Coverage**: Generates code coverage report

   All checks must pass before your PR can be merged. If any checks fail:
   - Review the error messages in the Actions tab
   - Fix the issues locally
   - Push the fixes to your branch (CI will re-run automatically)

### What to Contribute

We welcome contributions in many forms:

- **Bug fixes**: Found a bug? Submit a fix!
- **New features**: Have an idea? Open an issue first to discuss it
- **Documentation**: Improvements to README, docstrings, or examples
- **Tests**: Additional test coverage is always appreciated
- **Performance improvements**: Optimize existing code
- **Code quality**: Refactoring to improve maintainability

### Reporting Bugs

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to reproduce**: Detailed steps to reproduce the issue
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**: Python version, OS, package version
6. **Error messages**: Full error messages and stack traces

### Feature Requests

For feature requests:

1. **Use case**: Describe your use case and why this feature is needed
2. **Proposed solution**: How you envision the feature working
3. **Alternatives**: Any alternative solutions you've considered

## Project Structure

```
sekoia-event-exporter/
├── src/sekoia_event_exporter/
│   ├── __init__.py          # Package initialization
│   └── cli.py               # Main CLI implementation
├── tests/
│   ├── __init__.py
│   └── test_cli.py          # Tests for CLI module
├── examples/
│   ├── .env.example         # Example configuration
│   └── usage_example.py     # Example usage script
├── pyproject.toml           # Project configuration
├── README.md                # User documentation
└── CONTRIBUTING.md          # This file
```

## Code Review Process

- All contributions require review before merging
- Reviewers will check for:
  - Code quality and style
  - Test coverage
  - Documentation completeness
  - Backward compatibility
- Be responsive to feedback and questions
- Be respectful and constructive in discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the "question" label
- Reach out to the maintainers

Thank you for contributing!
