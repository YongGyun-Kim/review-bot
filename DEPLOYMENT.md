# Deployment Guide

This document describes how to build and deploy the AI Code Review Bot to PyPI.

## 📦 Package Structure

The package is configured with Poetry and includes:

- **Source Code**: All Python modules in the root directory
- **CLI Entry Point**: `review-bot` command via `cli.main:app`
- **Web Dashboard**: FastAPI application accessible via CLI
- **Dependencies**: Managed by Poetry with optional extras
- **Tests**: Comprehensive pytest suite
- **Documentation**: README, CHANGELOG, and contributing guides

## 🛠️ Build Process

### Prerequisites

1. **Python 3.11+** installed
2. **Poetry** installed (`curl -sSL https://install.python-poetry.org | python3 -`)
3. **PyPI account** with API token
4. **Test PyPI account** for testing (optional but recommended)

### Building the Package

```bash
# Install dependencies
poetry install

# Run tests to ensure quality
poetry run pytest tests/test_basic.py -v

# Build the package
poetry build
```

This creates:
- `dist/code_review_bot-2.0.0-py3-none-any.whl` (wheel)
- `dist/code_review_bot-2.0.0.tar.gz` (source distribution)

### Version Management

Update version in `pyproject.toml`:
```toml
[tool.poetry]
version = "2.0.0"
```

Poetry automatically syncs this with the package metadata.

## 🚀 Publishing to PyPI

### Manual Publishing

1. **Configure PyPI credentials:**
   ```bash
   poetry config pypi-token.pypi YOUR_PYPI_API_TOKEN
   ```

2. **Publish to Test PyPI (recommended first):**
   ```bash
   poetry config repositories.testpypi https://test.pypi.org/legacy/
   poetry config pypi-token.testpypi YOUR_TEST_PYPI_TOKEN
   poetry publish -r testpypi
   ```

3. **Test installation from Test PyPI:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ code-review-bot
   ```

4. **Publish to production PyPI:**
   ```bash
   poetry publish
   ```

### Automated Publishing (GitHub Actions)

The repository includes a GitHub Actions workflow (`.github/workflows/publish.yml`) that:

1. **Runs tests** on Python 3.11, 3.12, and 3.13
2. **Performs linting** with flake8
3. **Runs type checking** with mypy
4. **Builds the package** with Poetry
5. **Publishes to PyPI** on release creation

#### Setup Required Secrets:

- `PYPI_API_TOKEN`: Your PyPI API token
- `TEST_PYPI_API_TOKEN`: Your Test PyPI API token (optional)

#### Triggering Release:

1. **Create a new release** on GitHub
2. **Tag format**: `v2.0.0` (semantic versioning)
3. **Actions will automatically** run tests and publish

## 📋 Release Checklist

Before releasing a new version:

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md` with new features and fixes
- [ ] Run full test suite: `poetry run pytest`
- [ ] Run linting: `poetry run flake8 .`
- [ ] Run type checking: `poetry run mypy .`
- [ ] Build package locally: `poetry build`
- [ ] Test package installation: `pip install dist/code_review_bot-*.whl`
- [ ] Test CLI functionality
- [ ] Update documentation if needed
- [ ] Create GitHub release with tag

## 🔧 Package Configuration

### Entry Points

The package provides the following console scripts:
```toml
[tool.poetry.scripts]
review-bot = "cli.main:app"
```

### Dependencies

**Core dependencies:**
- `typer[all]` - CLI framework with Rich support
- `fastapi[all]` - Web framework with all extras  
- `pydantic` - Data validation
- `gitpython` - Git operations
- `rich` - Terminal formatting
- `jinja2` - Template engine
- `pyyaml` - YAML configuration
- `anthropic`, `openai`, `google-generativeai` - AI providers

**Development dependencies:**
- `pytest`, `pytest-asyncio`, `pytest-cov` - Testing
- `black`, `isort`, `flake8`, `mypy` - Code quality
- `pre-commit` - Git hooks

### Optional Extras

Users can install with specific extras:
```bash
# Web dashboard only
pip install code-review-bot[web]

# Development tools
pip install code-review-bot[dev]

# All extras
pip install code-review-bot[all]
```

## 🧪 Testing the Package

### Local Testing

```bash
# Install in development mode
poetry install

# Test CLI
poetry run review-bot --help
poetry run review-bot status

# Test web dashboard
poetry run review-bot dashboard --port 8000
```

### Integration Testing

```bash
# Test in a real Git repository
cd /path/to/test/repo
review-bot config init
review-bot config set provider claude
review-bot config set api_key YOUR_API_KEY
review-bot run --staged
```

## 📊 Package Metrics

The package includes:
- **~40KB wheel** with all dependencies
- **~35KB source** distribution
- **8 main modules** (cli, core, models, providers, web)
- **Comprehensive test suite** with fixtures
- **Type hints** throughout
- **Documentation** and examples

## 🔍 Troubleshooting

### Common Issues

1. **ImportError during installation**
   - Check Python version (3.11+ required)
   - Verify all dependencies are available

2. **CLI command not found**
   - Ensure installation completed successfully
   - Check PATH includes Python scripts directory

3. **Permission errors during publishing**
   - Verify API tokens are correct
   - Check package name availability on PyPI

4. **Test failures**
   - Check Git is available and configured
   - Ensure test environment has required dependencies

### Support

For deployment issues:
- Check the GitHub Issues page
- Review the CONTRIBUTING.md guide
- Contact maintainers via GitHub discussions

## 🎉 Success!

Once published, users can install with:
```bash
pip install code-review-bot
```

And use immediately:
```bash
review-bot config init
review-bot run
review-bot dashboard
```