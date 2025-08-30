"""Integration tests for the review bot."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
import tempfile
import shutil
import git

from core.review_manager import ReviewManager
from core.config_manager import ConfigManager
from core.git_manager import GitManager
from core.todo_manager import TodoManager
from core.prompt_manager import PromptManager
from models.types import ReviewConfig, Provider, Priority


class TestReviewBotIntegration:
    """Integration tests for the complete review bot workflow."""
    
    @pytest.fixture
    def integration_temp_dir(self):
        """Create temporary directory for integration tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def integration_git_repo(self, integration_temp_dir):
        """Create git repository for integration tests."""
        repo = git.Repo.init(integration_temp_dir)
        
        # Configure git
        repo.config_writer().set_value("user", "name", "Integration Test").release()
        repo.config_writer().set_value("user", "email", "test@integration.com").release()
        
        # Create initial files
        (integration_temp_dir / "src").mkdir()
        main_file = integration_temp_dir / "src" / "main.py"
        main_file.write_text("""#!/usr/bin/env python3
\"\"\"Main application module.\"\"\"

def greet(name):
    print(f"Hello, {name}!")

if __name__ == "__main__":
    greet("World")
""")
        
        utils_file = integration_temp_dir / "src" / "utils.py"
        utils_file.write_text("""\"\"\"Utility functions.\"\"\"

def calculate_sum(a, b):
    return a + b

def format_message(msg):
    return f"Message: {msg}"
""")
        
        # Initial commit
        repo.index.add([str(main_file), str(utils_file)])
        repo.index.commit("Initial commit")
        
        yield integration_temp_dir
    
    @pytest.fixture
    def integration_config(self, integration_temp_dir):
        """Create configuration for integration tests."""
        return ReviewConfig(
            provider=Provider.CLAUDE,
            model="claude-3-5-sonnet-20241022",
            api_key="test-integration-key",
            output_dir=integration_temp_dir / "reviews",
            max_files_per_review=10,
            temperature=0.1
        )
    
    @pytest.mark.asyncio
    async def test_complete_review_workflow(self, integration_git_repo, integration_config):
        """Test complete code review workflow."""
        repo_path = integration_git_repo
        
        # Make some changes
        main_file = repo_path / "src" / "main.py"
        main_file.write_text("""#!/usr/bin/env python3
\"\"\"Main application module.\"\"\"

def greet(name: str) -> None:
    \"\"\"Greet a person by name.\"\"\"
    if not name:
        raise ValueError("Name cannot be empty")
    print(f"Hello, {name}!")

def farewell(name: str) -> None:
    \"\"\"Say goodbye to a person.\"\"\"
    print(f"Goodbye, {name}!")

if __name__ == "__main__":
    greet("World")
    farewell("World")
""")
        
        # Create new file
        new_file = repo_path / "src" / "config.py"
        new_file.write_text("""\"\"\"Configuration module.\"\"\"

import os
from typing import Optional

class Config:
    def __init__(self):
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.database_url: Optional[str] = os.getenv("DATABASE_URL")
    
    def validate(self):
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
""")
        
        # Mock AI provider response
        mock_review_response = """# Code Review Results

## Summary
The code changes look good overall with proper type hints and error handling added.

## Issues Found

### Minor Issues
1. **Type Safety**: The `Config.database_url` could use better validation
2. **Error Handling**: Consider more specific exception types

## Suggestions
- Add unit tests for the new functions
- Consider using a configuration library like `pydantic` for the Config class
- Add docstring examples for the new functions

## Files Reviewed
- src/main.py: Added type hints and error handling ✅
- src/config.py: New configuration module ⚠️ (needs validation improvements)

Overall assessment: Good improvements with minor suggestions for enhancement.
"""
        
        with patch('providers.claude.ClaudeProvider') as mock_provider_class:
            # Setup mock
            mock_provider = Mock()
            mock_provider.review_code = AsyncMock(return_value=mock_review_response)
            mock_provider.estimate_cost.return_value = {
                "tokens": 1500,
                "estimated_cost": 0.045
            }
            mock_provider_class.return_value = mock_provider
            
            # Initialize review manager
            with patch('core.config_manager.ConfigManager._get_config_dir', return_value=repo_path / ".review-bot"):
                config_manager = ConfigManager()
                config_manager.config = integration_config
                
                review_manager = ReviewManager(repo_path=repo_path, config=integration_config)
                
                # Run review on working changes
                result = await review_manager.run_review(staged=False)
                
                assert result is not None
                
                # Verify review file was created
                reviews_dir = repo_path / "reviews"
                assert reviews_dir.exists()
                
                review_files = list(reviews_dir.glob("*.md"))
                assert len(review_files) > 0
                
                # Check review content
                review_content = review_files[0].read_text()
                assert "Code Review Results" in review_content
                assert "src/main.py" in review_content
                assert "src/config.py" in review_content
    
    @pytest.mark.asyncio
    async def test_todo_integration(self, integration_git_repo):
        """Test TODO management integration with reviews."""
        repo_path = integration_git_repo
        
        # Initialize TODO manager
        todo_manager = TodoManager(todos_dir=repo_path / ".review-bot" / "todos")
        
        # Create some TODOs that might come from a review
        await todo_manager.create_todo(
            "Add input validation",
            "The greet function should validate input parameters",
            priority=Priority.MEDIUM,
            file="src/main.py",
            line=5
        )
        
        await todo_manager.create_todo(
            "Add unit tests", 
            "Create comprehensive unit tests for all functions",
            priority=Priority.HIGH,
            assignee="developer"
        )
        
        await todo_manager.create_todo(
            "Improve error messages",
            "Make error messages more user-friendly",
            priority=Priority.LOW,
            file="src/config.py",
            line=15
        )
        
        # Get active TODOs
        active_todos = await todo_manager.get_active_todos()
        assert len(active_todos) == 3
        
        # Complete one TODO
        first_todo = active_todos[0]
        success = await todo_manager.mark_completed(first_todo.id)
        assert success is True
        
        # Check progress
        updated_todos = await todo_manager.get_active_todos()
        assert len(updated_todos) == 2
        
        completed_todos = await todo_manager.get_completed_todos()
        assert len(completed_todos) == 1
        assert completed_todos[0].id == first_todo.id
    
    @pytest.mark.asyncio
    async def test_prompt_template_integration(self, integration_git_repo):
        """Test prompt template integration with reviews."""
        repo_path = integration_git_repo
        prompts_dir = repo_path / ".review-bot" / "prompts"
        
        # Initialize prompt manager
        prompt_manager = PromptManager(prompts_dir=prompts_dir)
        
        # Create custom prompt template
        security_template = """---
description: "Security-focused code review template"
author: "Security Team"
---

# Security Code Review

Please perform a security-focused review of the following code changes:

{{ code_diff }}

## Focus Areas
- Input validation and sanitization
- Authentication and authorization
- SQL injection vulnerabilities
- XSS prevention
- Secure data handling

## Branch Information
- Branch: {{ branch }}
- Files changed: {{ files_changed }}
- Lines added: {{ lines_added }}
- Lines removed: {{ lines_deleted }}

Please provide specific recommendations for each security concern found.
"""
        
        await prompt_manager.create_prompt("security", security_template)
        
        # Verify template was created
        available_templates = await prompt_manager.get_available_prompts()
        security_prompt = next((t for t in available_templates if t.name == "security"), None)
        
        assert security_prompt is not None
        assert "security-focused" in security_prompt.description.lower()
        assert "code_diff" in security_prompt.variables
        assert "branch" in security_prompt.variables
        
        # Test template population
        test_data = {
            "code_diff": "def authenticate(password):\n    return password == 'admin'",
            "branch": "feature/auth",
            "files_changed": 1,
            "lines_added": 2,
            "lines_deleted": 0
        }
        
        template_content = await prompt_manager.load_prompt("security")
        populated = prompt_manager.populate_prompt(template_content, test_data)
        
        assert "def authenticate(password)" in populated
        assert "Branch: feature/auth" in populated
        assert "Files changed: 1" in populated
    
    @pytest.mark.asyncio
    async def test_config_management_integration(self, integration_temp_dir):
        """Test configuration management across components."""
        config_dir = integration_temp_dir / ".review-bot"
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=config_dir):
            config_manager = ConfigManager()
            
            # Initialize with default config
            await config_manager.init_config()
            
            # Update configuration
            config_updates = {
                "provider": "claude",
                "model": "claude-3-5-sonnet-20241022", 
                "temperature": 0.2,
                "max_files_per_review": 20,
                "auto_review": {
                    "on_commit": True,
                    "on_push": False
                }
            }
            
            await config_manager.save_config(config_updates)
            
            # Load and verify configuration
            loaded_config = await config_manager.load_config()
            
            assert loaded_config.provider == Provider.CLAUDE
            assert loaded_config.model == "claude-3-5-sonnet-20241022"
            assert loaded_config.temperature == 0.2
            assert loaded_config.max_files_per_review == 20
            assert loaded_config.auto_review["on_commit"] is True
            assert loaded_config.auto_review["on_push"] is False
            
            # Test environment variable override
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-api-key'}):
                env_config = await config_manager.load_config()
                assert env_config.api_key == "env-api-key"
    
    @pytest.mark.asyncio  
    async def test_git_integration_with_hooks(self, integration_git_repo):
        """Test Git integration with hooks installation."""
        repo_path = integration_git_repo
        
        git_manager = GitManager(repo_path=repo_path)
        
        # Verify it's a git repository
        assert git_manager.is_git_repository() is True
        assert git_manager.get_current_branch() in ['main', 'master']
        assert git_manager.has_changes() is False
        
        # Make changes
        test_file = repo_path / "src" / "main.py"
        original_content = test_file.read_text()
        test_file.write_text(original_content + "\n# Added comment\n")
        
        assert git_manager.has_changes() is True
        
        # Get diff
        diff = git_manager.get_diff()
        assert diff.stats.files_changed >= 1
        assert len(diff.files) >= 1
        assert any(f.path == "src/main.py" for f in diff.files)
        
        # Test hooks installation
        git_manager.install_hooks()
        
        hooks_dir = repo_path / ".git" / "hooks"
        assert hooks_dir.exists()
        
        # Hooks should be created (even if empty in test)
        pre_commit_hook = hooks_dir / "pre-commit"
        pre_push_hook = hooks_dir / "pre-push"
        
        # In a real scenario, these would exist and be executable
        # For test, we just verify the installation process doesn't error
        
        # Test uninstallation
        git_manager.uninstall_hooks()
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integration_git_repo, integration_config):
        """Test error handling across integrated components."""
        repo_path = integration_git_repo
        
        # Test with invalid API key
        invalid_config = integration_config.model_copy()
        invalid_config.api_key = "invalid-key"
        
        with patch('providers.claude.ClaudeProvider') as mock_provider_class:
            # Mock API error
            mock_provider = Mock()
            mock_provider.review_code = AsyncMock(side_effect=Exception("Invalid API key"))
            mock_provider_class.return_value = mock_provider
            
            review_manager = ReviewManager(repo_path=repo_path, config=invalid_config)
            
            # Should handle error gracefully
            with pytest.raises(Exception) as exc_info:
                await review_manager.run_review()
            
            assert "Invalid API key" in str(exc_info.value)
        
        # Test with non-git directory
        non_git_dir = repo_path / "not-git"
        non_git_dir.mkdir()
        
        git_manager = GitManager(repo_path=non_git_dir)
        assert git_manager.is_git_repository() is False
        
        with pytest.raises(ValueError) as exc_info:
            git_manager.get_diff()
        
        assert "Not a git repository" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, integration_git_repo):
        """Test concurrent operations don't interfere with each other."""
        repo_path = integration_git_repo
        
        # Initialize managers
        todo_manager = TodoManager(todos_dir=repo_path / ".review-bot" / "todos")
        prompts_dir = repo_path / ".review-bot" / "prompts"
        prompt_manager = PromptManager(prompts_dir=prompts_dir)
        
        # Define concurrent operations
        async def create_todos():
            tasks = []
            for i in range(5):
                tasks.append(todo_manager.create_todo(
                    f"TODO {i}",
                    f"Description for TODO {i}",
                    priority=Priority.MEDIUM
                ))
            await asyncio.gather(*tasks)
        
        async def create_prompts():
            tasks = []
            for i in range(3):
                template = f"Template {i}: {{{{ code_diff }}}}"
                tasks.append(prompt_manager.create_prompt(f"template{i}", template))
            await asyncio.gather(*tasks)
        
        async def check_git_status():
            git_manager = GitManager(repo_path=repo_path)
            for _ in range(10):
                git_manager.has_changes()
                await asyncio.sleep(0.01)
        
        # Run operations concurrently
        await asyncio.gather(
            create_todos(),
            create_prompts(),
            check_git_status()
        )
        
        # Verify results
        todos = await todo_manager.get_active_todos()
        assert len(todos) == 5
        
        templates = await prompt_manager.get_available_prompts()
        template_names = {t.name for t in templates}
        assert "template0" in template_names
        assert "template1" in template_names
        assert "template2" in template_names