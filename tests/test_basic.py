"""Basic smoke tests to verify the core functionality."""

import pytest
from pathlib import Path
from models.types import Provider, Priority, ReviewConfig, TodoItem
from core.config_manager import ConfigManager
from core.todo_manager import TodoManager
from core.prompt_manager import PromptManager


class TestBasicFunctionality:
    """Basic smoke tests for core components."""
    
    def test_provider_enum(self):
        """Test Provider enum works correctly."""
        assert Provider.CLAUDE == "claude"
        assert Provider.CHATGPT == "chatgpt"
        assert Provider.GEMINI == "gemini"
    
    def test_priority_enum(self):
        """Test Priority enum works correctly."""
        assert Priority.HIGH == "high"
        assert Priority.MEDIUM == "medium"
        assert Priority.LOW == "low"
    
    def test_review_config_creation(self):
        """Test ReviewConfig can be created."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        assert config.provider == Provider.CLAUDE
        assert config.api_key == "test-key"
        assert config.output_dir == Path("reviews")
    
    def test_config_manager_instantiation(self):
        """Test ConfigManager can be instantiated."""
        config_manager = ConfigManager()
        assert config_manager is not None
    
    def test_todo_manager_instantiation(self, tmp_path):
        """Test TodoManager can be instantiated."""
        todo_manager = TodoManager(output_dir=tmp_path / "todos")
        assert todo_manager is not None
    
    def test_prompt_manager_instantiation(self, tmp_path):
        """Test PromptManager can be instantiated."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        prompt_manager = PromptManager(prompts_dir=prompts_dir)
        assert prompt_manager is not None
    
    @pytest.mark.asyncio
    async def test_create_simple_todo(self, tmp_path):
        """Test creating a simple TODO item."""
        todo_manager = TodoManager(output_dir=tmp_path / "todos")
        
        todo_item = await todo_manager.create_todo(
            "Test TODO",
            "This is a test TODO item"
        )
        
        assert isinstance(todo_item, TodoItem)
        assert todo_item.title == "Test TODO"
        assert todo_item.description == "This is a test TODO item"
        assert todo_item.priority == Priority.MEDIUM  # Default
        assert todo_item.completed is False
    
    @pytest.mark.asyncio
    async def test_prompt_template_basic_usage(self, tmp_path):
        """Test basic prompt template functionality."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Create a simple template
        template_file = prompts_dir / "test.md"
        template_file.write_text("Review this code: {{ code_diff }}")
        
        prompt_manager = PromptManager(prompts_dir=prompts_dir)
        
        # Load template
        template_content = await prompt_manager.load_prompt("test")
        assert "{{ code_diff }}" in template_content
        
        # Populate template
        populated = prompt_manager.populate_prompt(
            template_content, 
            {"code_diff": "def hello(): pass"}
        )
        assert "def hello(): pass" in populated