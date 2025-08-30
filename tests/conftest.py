"""Pytest configuration and fixtures."""

import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest
from unittest.mock import Mock, patch
import git

from models.types import ReviewConfig, Provider, Priority
from core.config_manager import ConfigManager
from core.git_manager import GitManager
from core.todo_manager import TodoManager
from core.prompt_manager import PromptManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for tests."""
    repo = git.Repo.init(temp_dir)
    
    # Configure git user for tests
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    # Create initial commit
    test_file = temp_dir / "test.py"
    test_file.write_text("# Test file\nprint('hello world')\n")
    repo.index.add([str(test_file)])
    repo.index.commit("Initial commit")
    
    yield temp_dir


@pytest.fixture
def sample_config() -> ReviewConfig:
    """Sample configuration for tests."""
    return ReviewConfig(
        provider=Provider.CLAUDE,
        model="claude-3-5-sonnet-20241022",
        api_key="test-api-key",
        output_dir=Path("reviews"),
        max_files_per_review=10,
        max_tokens=100000,
        temperature=0.1,
        auto_review={
            "on_commit": True,
            "on_push": False
        }
    )


@pytest.fixture
def config_manager(temp_dir: Path, sample_config: ReviewConfig):
    """ConfigManager instance with temporary directory."""
    with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
        manager = ConfigManager()
        manager.config = sample_config
        return manager


@pytest.fixture
def git_manager(temp_git_repo: Path):
    """GitManager instance with temporary git repository."""
    return GitManager(repo_path=temp_git_repo)


@pytest.fixture
def todo_manager(temp_dir: Path):
    """TodoManager instance with temporary directory."""
    return TodoManager(todos_dir=temp_dir / "todos")


@pytest.fixture
def prompt_manager(temp_dir: Path):
    """PromptManager instance with temporary directory."""
    prompts_dir = temp_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    
    # Create a default prompt template
    default_prompt = prompts_dir / "default.md"
    default_prompt.write_text("""# Code Review Prompt

Please review the following code changes:

{{ code_diff }}

Provide detailed feedback including:
- Code quality issues
- Potential bugs
- Performance improvements
- Best practices recommendations
""")
    
    return PromptManager(prompts_dir=prompts_dir)


@pytest.fixture
def mock_ai_response():
    """Mock AI provider response."""
    return {
        "review": "This is a mock review response.",
        "issues": [
            {
                "type": "bug",
                "severity": "medium",
                "message": "Potential null pointer exception",
                "file": "test.py",
                "line": 5
            }
        ],
        "suggestions": [
            "Add error handling",
            "Use type hints"
        ]
    }


@pytest.fixture
def mock_claude_provider():
    """Mock Claude provider for testing."""
    with patch('providers.claude.ClaudeProvider') as mock:
        mock_instance = Mock()
        mock_instance.review_code.return_value = asyncio.Future()
        mock_instance.review_code.return_value.set_result("Mock review result")
        mock_instance.estimate_cost.return_value = {"estimated_cost": 0.05, "tokens": 1000}
        mock.return_value = mock_instance
        yield mock_instance