"""Tests for ReviewManager."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
import tempfile
import shutil
import git

from core.review_manager import ReviewManager
from models.types import ReviewConfig, Provider, ReviewResult, GitDiff, GitDiffStats, GitDiffFile


class TestReviewManager:
    """Test ReviewManager functionality."""
    
    @pytest.fixture
    def review_temp_dir(self):
        """Create temporary directory for review tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def review_git_repo(self, review_temp_dir):
        """Create git repository for review tests."""
        repo = git.Repo.init(review_temp_dir)
        
        # Configure git
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()
        
        # Create initial file
        test_file = review_temp_dir / "test.py"
        test_file.write_text("print('hello world')")
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")
        
        yield review_temp_dir
    
    @pytest.fixture
    def review_config(self, review_temp_dir):
        """Create review configuration."""
        return ReviewConfig(
            provider=Provider.CLAUDE,
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
            output_dir=review_temp_dir / "reviews",
            max_files_per_review=10,
            temperature=0.1
        )
    
    @pytest.mark.asyncio
    async def test_review_manager_initialization(self, review_git_repo, review_config):
        """Test ReviewManager initialization."""
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        
        assert manager.repo_path == review_git_repo
        assert manager.config == review_config
        assert hasattr(manager, 'git_manager')
        assert hasattr(manager, 'prompt_manager')
    
    @pytest.mark.asyncio
    @patch('providers.claude.ClaudeProvider')
    async def test_run_review_working_changes(self, mock_provider_class, review_git_repo, review_config):
        """Test running review on working directory changes."""
        # Make changes to trigger review
        test_file = review_git_repo / "test.py"
        test_file.write_text("print('hello modified world')\ndef new_function():\n    return 42")
        
        # Setup mock AI provider
        mock_provider = Mock()
        mock_review_response = """# Code Review
        
## Summary
Code looks good with minor suggestions.

## Issues Found
1. Missing type hints on new_function
2. Consider adding docstring

## Suggestions
- Add return type annotation
- Add docstring explaining function purpose
"""
        mock_provider.review_code = AsyncMock(return_value=mock_review_response)
        mock_provider.estimate_cost.return_value = {"tokens": 500, "estimated_cost": 0.015}
        mock_provider_class.return_value = mock_provider
        
        # Run review
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        result = await manager.run_review(staged=False)
        
        assert result is not None
        assert isinstance(result, ReviewResult)
        assert result.provider == Provider.CLAUDE
        assert "Code Review" in result.review
        
        # Verify review file was created
        reviews_dir = review_config.output_dir
        review_files = list(reviews_dir.glob("*.md"))
        assert len(review_files) > 0
        
        # Check review content
        review_content = review_files[0].read_text()
        assert "Code Review" in review_content
        assert "new_function" in review_content
    
    @pytest.mark.asyncio
    @patch('providers.claude.ClaudeProvider')
    async def test_run_review_staged_changes(self, mock_provider_class, review_git_repo, review_config):
        """Test running review on staged changes."""
        # Create and stage new file
        new_file = review_git_repo / "new_module.py"
        new_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
""")
        
        repo = git.Repo(review_git_repo)
        repo.index.add([str(new_file)])
        
        # Setup mock
        mock_provider = Mock()
        mock_provider.review_code = AsyncMock(return_value="Review of Calculator class: Looks good!")
        mock_provider.estimate_cost.return_value = {"tokens": 300, "estimated_cost": 0.01}
        mock_provider_class.return_value = mock_provider
        
        # Run review on staged changes
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        result = await manager.run_review(staged=True)
        
        assert result is not None
        assert "Calculator" in result.review
        assert len(result.files_reviewed) > 0
        assert "new_module.py" in result.files_reviewed
    
    @pytest.mark.asyncio
    @patch('providers.claude.ClaudeProvider')  
    async def test_run_review_specific_commit(self, mock_provider_class, review_git_repo, review_config):
        """Test running review on specific commit."""
        # Create a commit
        commit_file = review_git_repo / "commit_test.py"
        commit_file.write_text("# Test commit file\nprint('commit test')")
        
        repo = git.Repo(review_git_repo)
        repo.index.add([str(commit_file)])
        commit = repo.index.commit("Add commit test file")
        
        # Setup mock
        mock_provider = Mock()
        mock_provider.review_code = AsyncMock(return_value="Review of commit: File looks good!")
        mock_provider.estimate_cost.return_value = {"tokens": 200, "estimated_cost": 0.006}
        mock_provider_class.return_value = mock_provider
        
        # Run review on specific commit
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        result = await manager.run_review(commit_hash=commit.hexsha)
        
        assert result is not None
        assert "commit" in result.review.lower()
    
    @pytest.mark.asyncio
    async def test_run_review_no_changes(self, review_git_repo, review_config):
        """Test running review with no changes."""
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        
        # Clean repository should have no changes
        with pytest.raises(ValueError) as exc_info:
            await manager.run_review()
        
        assert "No changes found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('providers.claude.ClaudeProvider')
    async def test_run_review_with_file_filters(self, mock_provider_class, review_git_repo, review_config):
        """Test running review with file filters."""
        # Create files with different extensions
        py_file = review_git_repo / "script.py"
        js_file = review_git_repo / "app.js"
        txt_file = review_git_repo / "readme.txt"
        
        py_file.write_text("print('python')")
        js_file.write_text("console.log('javascript')")
        txt_file.write_text("This is a readme")
        
        # Setup mock
        mock_provider = Mock()
        mock_provider.review_code = AsyncMock(return_value="Python code review")
        mock_provider.estimate_cost.return_value = {"tokens": 100, "estimated_cost": 0.003}
        mock_provider_class.return_value = mock_provider
        
        # Run review with Python file filter
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        result = await manager.run_review(file_filters=["*.py"])
        
        assert result is not None
        assert "script.py" in result.files_reviewed
        assert "app.js" not in result.files_reviewed
        assert "readme.txt" not in result.files_reviewed
    
    @pytest.mark.asyncio
    @patch('providers.claude.ClaudeProvider')
    async def test_run_review_with_custom_prompt(self, mock_provider_class, review_git_repo, review_config):
        """Test running review with custom prompt template."""
        # Make changes
        test_file = review_git_repo / "test.py" 
        test_file.write_text("print('custom prompt test')")
        
        # Create custom prompt template
        prompts_dir = review_git_repo / ".review-bot" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        
        custom_prompt = prompts_dir / "security.md"
        custom_prompt.write_text("""# Security Review
        
Please perform a security review of:
{{ code_diff }}

Focus on potential vulnerabilities.
""")
        
        # Setup mock
        mock_provider = Mock()
        mock_provider.review_code = AsyncMock(return_value="Security review: No vulnerabilities found")
        mock_provider.estimate_cost.return_value = {"tokens": 250, "estimated_cost": 0.008}
        mock_provider_class.return_value = mock_provider
        
        # Run review with custom prompt
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        result = await manager.run_review(prompt_template="security")
        
        assert result is not None
        assert "security" in result.review.lower()
        
        # Verify the prompt template was used
        call_args = mock_provider.review_code.call_args[0][0]
        assert "Security Review" in call_args
        assert "vulnerabilities" in call_args
    
    @pytest.mark.asyncio
    async def test_save_review_result(self, review_git_repo, review_config):
        """Test saving review result to file."""
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        
        # Create mock review result
        from datetime import datetime
        result = ReviewResult(
            timestamp=datetime.now(),
            provider=Provider.CLAUDE,
            model="claude-3-5-sonnet-20241022",
            review="This is a test review result",
            files_reviewed=["test.py"],
            tokens_used=500,
            estimated_cost=0.015
        )
        
        # Save result
        saved_path = await manager._save_review_result(result, output_format="markdown")
        
        assert saved_path.exists()
        assert saved_path.suffix == ".md"
        assert saved_path.parent == review_config.output_dir
        
        # Check content
        content = saved_path.read_text()
        assert "This is a test review result" in content
        assert "test.py" in content
        assert "claude-3-5-sonnet-20241022" in content
    
    @pytest.mark.asyncio
    async def test_save_review_result_json(self, review_git_repo, review_config):
        """Test saving review result as JSON."""
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        
        from datetime import datetime
        result = ReviewResult(
            timestamp=datetime.now(),
            provider=Provider.CLAUDE,
            review="JSON test review",
            files_reviewed=["app.py"]
        )
        
        # Save as JSON
        saved_path = await manager._save_review_result(result, output_format="json")
        
        assert saved_path.exists()
        assert saved_path.suffix == ".json"
        
        # Verify JSON content
        import json
        with open(saved_path) as f:
            data = json.load(f)
        
        assert data["review"] == "JSON test review"
        assert "app.py" in data["files_reviewed"]
    
    @pytest.mark.asyncio
    @patch('providers.claude.ClaudeProvider')
    async def test_run_review_interactive_mode(self, mock_provider_class, review_git_repo, review_config):
        """Test running review in interactive mode."""
        # Make changes
        test_file = review_git_repo / "test.py"
        test_file.write_text("print('interactive test')")
        
        # Setup mock
        mock_provider = Mock()
        mock_provider.review_code = AsyncMock(return_value="Interactive review result")
        mock_provider.estimate_cost.return_value = {"tokens": 300, "estimated_cost": 0.01}
        mock_provider_class.return_value = mock_provider
        
        # Mock user input (simulate "yes" to proceed)
        with patch('builtins.input', return_value='y'):
            manager = ReviewManager(repo_path=review_git_repo, config=review_config)
            result = await manager.run_review(interactive=True)
        
        assert result is not None
        assert "Interactive" in result.review
    
    @pytest.mark.asyncio
    async def test_max_files_limit(self, review_git_repo, review_config):
        """Test maximum files per review limit."""
        # Set low file limit
        review_config.max_files_per_review = 2
        
        # Create more files than the limit
        for i in range(5):
            test_file = review_git_repo / f"test_{i}.py"
            test_file.write_text(f"print('test {i}')")
        
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        
        # Get diff to see files that would be reviewed
        git_diff = manager.git_manager.get_diff()
        
        # Should respect the file limit
        if len(git_diff.files) > review_config.max_files_per_review:
            with patch('providers.claude.ClaudeProvider') as mock_provider_class:
                mock_provider = Mock()
                mock_provider.review_code = AsyncMock(return_value="Limited review")
                mock_provider.estimate_cost.return_value = {"tokens": 200, "estimated_cost": 0.006}
                mock_provider_class.return_value = mock_provider
                
                result = await manager.run_review()
                
                # Should only review up to the limit
                assert len(result.files_reviewed) <= review_config.max_files_per_review
    
    @pytest.mark.asyncio
    @patch('providers.claude.ClaudeProvider')
    async def test_error_handling_in_review(self, mock_provider_class, review_git_repo, review_config):
        """Test error handling during review process."""
        # Make changes
        test_file = review_git_repo / "test.py"
        test_file.write_text("print('error test')")
        
        # Setup mock to raise exception
        mock_provider = Mock()
        mock_provider.review_code = AsyncMock(side_effect=Exception("API Error"))
        mock_provider.estimate_cost.return_value = {"tokens": 100, "estimated_cost": 0.003}
        mock_provider_class.return_value = mock_provider
        
        manager = ReviewManager(repo_path=review_git_repo, config=review_config)
        
        # Should propagate the exception
        with pytest.raises(Exception) as exc_info:
            await manager.run_review()
        
        assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_non_git_repository(self, review_temp_dir, review_config):
        """Test ReviewManager with non-git directory."""
        # Create non-git directory
        non_git_dir = review_temp_dir / "not-git"
        non_git_dir.mkdir()
        
        manager = ReviewManager(repo_path=non_git_dir, config=review_config)
        
        with pytest.raises(ValueError) as exc_info:
            await manager.run_review()
        
        assert "Not a git repository" in str(exc_info.value)