# Contributing to AI Code Review Bot

Thank you for considering contributing to AI Code Review Bot! This document provides guidelines and instructions for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Git
- API key for at least one AI provider (Claude, ChatGPT, or Gemini)

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/code-review-bot.git
   cd code-review-bot
   ```

2. **Install Poetry if you haven't already:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies:**
   ```bash
   poetry install
   ```

4. **Set up pre-commit hooks (optional but recommended):**
   ```bash
   poetry run pre-commit install
   ```

5. **Run tests to ensure everything works:**
   ```bash
   poetry run pytest tests/test_basic.py -v
   ```

## 🏗️ Development Workflow

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards below.

3. **Write tests** for your changes in the `tests/` directory.

4. **Run the test suite:**
   ```bash
   poetry run pytest
   ```

5. **Run linting and type checking:**
   ```bash
   poetry run flake8 .
   poetry run black .
   poetry run isort .
   poetry run mypy .
   ```

6. **Update documentation** if needed.

7. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

8. **Push and create a pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation updates
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
- `feat: add Gemini AI provider support`
- `fix: resolve configuration file parsing issue`
- `docs: update README with new installation instructions`

## 🧪 Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_basic.py

# Run with coverage
poetry run pytest --cov=.

# Run integration tests
poetry run pytest tests/test_integration.py -m integration
```

### Writing Tests

- Place tests in the appropriate directory under `tests/`
- Use descriptive test names that explain what is being tested
- Follow the AAA pattern (Arrange, Act, Assert)
- Use fixtures for common test setup
- Mock external dependencies (AI APIs, Git operations)

Example test:
```python
@pytest.mark.asyncio
async def test_create_todo_basic():
    """Test creating a basic TODO item."""
    todo_manager = TodoManager(output_dir=tmp_path / "todos")
    
    todo_item = await todo_manager.create_todo(
        "Test TODO",
        "This is a test TODO item"
    )
    
    assert isinstance(todo_item, TodoItem)
    assert todo_item.title == "Test TODO"
    assert todo_item.completed is False
```

## 📏 Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use type hints throughout the codebase

### Code Quality

- Write self-documenting code with clear variable and function names
- Add docstrings to all public functions and classes
- Use Pydantic models for data validation
- Handle errors gracefully with specific exception types
- Follow SOLID principles
- Maintain high test coverage

### Architecture Guidelines

- Keep modules focused and cohesive
- Use dependency injection where appropriate
- Separate business logic from infrastructure concerns
- Use async/await for I/O operations
- Follow the existing project structure

## 🐛 Reporting Issues

When reporting issues, please include:

1. **Clear description** of the problem
2. **Steps to reproduce** the issue
3. **Expected behavior** vs actual behavior
4. **Environment information**:
   - Python version
   - Operating system
   - Package version
   - AI provider being used
5. **Error messages** or logs if applicable
6. **Minimal code example** that reproduces the issue

## 💡 Feature Requests

For feature requests, please provide:

1. **Clear description** of the feature
2. **Use case** and motivation
3. **Proposed implementation** (if you have ideas)
4. **Alternatives considered**
5. **Additional context** or examples

## 🔧 Development Scripts

Useful commands for development:

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run linting
poetry run flake8 .

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy .

# Build package
poetry build

# Install local development version
poetry install

# Run CLI in development
poetry run python -m cli.main

# Start web dashboard
poetry run python -m web.app
```

## 📦 Package Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with new features and fixes
3. Run tests and ensure all pass
4. Build package: `poetry build`
5. Test package installation locally
6. Create a release on GitHub
7. GitHub Actions will automatically publish to PyPI

## 🤝 Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Provide constructive feedback
- Follow the code of conduct
- Ask questions if you're unsure about anything

## 📞 Getting Help

- Open an issue for bugs or feature requests
- Start a discussion for general questions
- Check existing documentation and issues first
- Tag maintainers in urgent issues

Thank you for contributing! 🎉