# Publishing to PyPI

This guide explains how to publish the `sekoia-event-exporter` package to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [TestPyPI](https://test.pypi.org/account/register/) (for testing)
   - [PyPI](https://pypi.org/account/register/) (for production)

2. **API Tokens**: Generate API tokens for both services:
   - TestPyPI: https://test.pypi.org/manage/account/token/
   - PyPI: https://pypi.org/manage/account/token/

   Save these tokens securely - you'll need them for publishing.

3. **uv installed**: Ensure you have uv installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## Publishing Process

### Step 1: Prepare the Release

1. **Update the version** in `pyproject.toml`:
   ```toml
   [project]
   version = "0.1.0"  # Update this
   ```

2. **Update CHANGELOG** (if you have one) with release notes

3. **Ensure all tests pass**:
   ```bash
   uv run pytest
   uv run black --check src/ tests/
   uv run ruff check src/ tests/
   uv run mypy src/
   ```

4. **Commit version changes**:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.1.0"
   git tag v0.1.0
   git push origin main --tags
   ```

### Step 2: Build the Package

Build the distribution packages (wheel and source):

```bash
uv build
```

This creates files in the `dist/` directory:
- `sekoia_event_exporter-0.1.0-py3-none-any.whl` (wheel)
- `sekoia_event_exporter-0.1.0.tar.gz` (source distribution)

### Step 3: Test on TestPyPI (Recommended)

Always test on TestPyPI before publishing to production PyPI.

1. **Configure TestPyPI credentials**:
   ```bash
   # Set environment variable
   export UV_PUBLISH_TOKEN="your-test-pypi-token"
   ```

2. **Publish to TestPyPI**:
   ```bash
   uv publish --publish-url https://test.pypi.org/legacy/
   ```

3. **Test installation from TestPyPI**:
   ```bash
   # In a clean environment
   uv pip install --index-url https://test.pypi.org/simple/ sekoia-event-exporter

   # Test the command
   sekoia-event-export --help
   ```

### Step 4: Publish to Production PyPI

Once you've verified everything works on TestPyPI:

1. **Configure PyPI credentials**:
   ```bash
   export UV_PUBLISH_TOKEN="your-pypi-token"
   ```

2. **Publish to PyPI**:
   ```bash
   uv publish
   ```

3. **Verify the package**:
   ```bash
   # Install from PyPI
   uv pip install sekoia-event-exporter

   # Test
   sekoia-event-export --help
   ```

## Alternative: Using twine

If you prefer the traditional approach with twine:

1. **Install twine**:
   ```bash
   uv pip install twine
   ```

2. **Build the package**:
   ```bash
   uv build
   ```

3. **Upload to TestPyPI**:
   ```bash
   uv run twine upload --repository testpypi dist/*
   ```

4. **Upload to PyPI**:
   ```bash
   uv run twine upload dist/*
   ```

## Using GitHub Actions (Automated)

For automated releases when you create a GitHub release, see the `.github/workflows/publish.yml` file.

To trigger an automated release:

1. Create a new release on GitHub
2. Tag it with the version (e.g., `v0.1.0`)
3. The workflow will automatically build and publish to PyPI

## Credential Management

### Option 1: Environment Variables (Recommended for CI)

```bash
export UV_PUBLISH_TOKEN="pypi-..."
uv publish
```

### Option 2: Interactive (Recommended for Local)

If you don't set `UV_PUBLISH_TOKEN`, uv will prompt for credentials interactively.

### Option 3: Configuration File

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token-here
```

**Security Warning**: Keep this file private (`chmod 600 ~/.pypirc`)

## Troubleshooting

### "File already exists" error

PyPI doesn't allow re-uploading the same version. You must increment the version number in `pyproject.toml`.

### Version conflicts

If you see version conflicts, check:
- Version in `pyproject.toml`
- Any git tags that might conflict
- Existing versions on PyPI

### Build errors

Clean the build directory and rebuild:
```bash
rm -rf dist/ build/ *.egg-info
uv build
```

### Import errors after installation

Make sure your package structure is correct and all dependencies are listed in `pyproject.toml`.

## Checklist

Before publishing to PyPI:

- [ ] All tests pass
- [ ] Code is formatted and linted
- [ ] Version number is updated
- [ ] Git tag created
- [ ] Tested on TestPyPI
- [ ] README is up to date
- [ ] LICENSE file is included
- [ ] Dependencies are correct in pyproject.toml

## Post-Publication

After publishing:

1. Verify the package page on PyPI
2. Test installation in a clean environment
3. Update documentation with installation instructions
4. Announce the release (blog, social media, etc.)
5. Monitor for issues and user feedback

## Resources

- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Semantic Versioning](https://semver.org/)
