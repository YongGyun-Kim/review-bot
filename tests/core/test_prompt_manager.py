"""Tests for PromptManager."""

import pytest
from pathlib import Path
from unittest.mock import patch
from jinja2 import TemplateError

from core.prompt_manager import PromptManager
from models.types import PromptTemplate, GitDiff, GitStats, FileChange


class TestPromptManager:
    """Test PromptManager functionality."""
    
    @pytest.mark.asyncio
    async def test_load_existing_prompt(self, prompt_manager: PromptManager):
        """Test loading an existing prompt template."""
        template_content = await prompt_manager.load_prompt("default")
        
        assert "Code Review Prompt" in template_content
        assert "{{ code_diff }}" in template_content
        assert isinstance(template_content, str)
        assert len(template_content) > 0
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_prompt_fallback(self, prompt_manager: PromptManager):
        """Test loading non-existent prompt falls back to default."""
        template_content = await prompt_manager.load_prompt("nonexistent")
        
        # Should fallback to default template
        assert "Code Review Prompt" in template_content
        assert "{{ code_diff }}" in template_content
    
    @pytest.mark.asyncio
    async def test_load_prompt_no_default(self, temp_dir: Path):
        """Test loading prompt when no default exists."""
        empty_prompts_dir = temp_dir / "empty_prompts"
        empty_prompts_dir.mkdir()
        
        manager = PromptManager(prompts_dir=empty_prompts_dir)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            await manager.load_prompt("default")
        
        assert "Default template not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_available_prompts(self, prompt_manager: PromptManager):
        """Test getting list of available prompt templates."""
        templates = await prompt_manager.get_available_prompts()
        
        assert len(templates) >= 1
        assert isinstance(templates[0], PromptTemplate)
        
        # Check default template is included
        default_template = next((t for t in templates if t.name == "default"), None)
        assert default_template is not None
        assert "code_diff" in default_template.variables
    
    @pytest.mark.asyncio
    async def test_create_new_prompt(self, temp_dir: Path):
        """Test creating a new prompt template."""
        prompts_dir = temp_dir / "test_prompts"
        manager = PromptManager(prompts_dir=prompts_dir)
        
        template_content = """# Security Review Template
Please review this code for security vulnerabilities:

{{ code_diff }}

Focus on:
- Input validation
- Authentication issues  
- SQL injection risks
"""
        
        await manager.create_prompt("security", template_content)
        
        # Verify file was created
        template_file = prompts_dir / "security.md"
        assert template_file.exists()
        
        # Verify content
        saved_content = template_file.read_text()
        assert saved_content == template_content
    
    @pytest.mark.asyncio
    async def test_create_duplicate_prompt(self, prompt_manager: PromptManager):
        """Test creating prompt that already exists."""
        template_content = "Duplicate template"
        
        with pytest.raises(FileExistsError) as exc_info:
            await prompt_manager.create_prompt("default", template_content)
        
        assert "already exists" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_invalid_prompt(self, temp_dir: Path):
        """Test creating prompt with invalid template syntax."""
        prompts_dir = temp_dir / "test_prompts"
        manager = PromptManager(prompts_dir=prompts_dir)
        
        # Invalid Jinja2 syntax
        invalid_template = "Review: {{ unclosed_block"
        
        with pytest.raises(ValueError) as exc_info:
            await manager.create_prompt("invalid", invalid_template)
        
        assert "Invalid template" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_prompt(self, prompt_manager: PromptManager):
        """Test updating an existing prompt template."""
        updated_content = """# Updated Code Review Prompt

Updated review template:

{{ code_diff }}

New requirements:
- Check for {{ branch }} specific issues
"""
        
        await prompt_manager.update_prompt("default", updated_content)
        
        # Verify content was updated
        new_content = await prompt_manager.load_prompt("default")
        assert "Updated Code Review Prompt" in new_content
        assert "New requirements" in new_content
        
        # Verify backup was created
        backup_file = prompt_manager.prompts_dir / "default.md.bak"
        assert backup_file.exists()
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_prompt(self, prompt_manager: PromptManager):
        """Test updating non-existent prompt."""
        with pytest.raises(FileNotFoundError) as exc_info:
            await prompt_manager.update_prompt("nonexistent", "content")
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_prompt(self, temp_dir: Path):
        """Test deleting a prompt template."""
        prompts_dir = temp_dir / "test_prompts"
        manager = PromptManager(prompts_dir=prompts_dir)
        
        # Create a template to delete
        template_file = prompts_dir / "deleteme.md"
        template_file.parent.mkdir(exist_ok=True)
        template_file.write_text("Template to delete")
        
        await manager.delete_prompt("deleteme")
        
        # Verify file was deleted
        assert not template_file.exists()
    
    @pytest.mark.asyncio
    async def test_delete_default_prompt(self, prompt_manager: PromptManager):
        """Test that deleting default prompt is prevented."""
        with pytest.raises(ValueError) as exc_info:
            await prompt_manager.delete_prompt("default")
        
        assert "Cannot delete default template" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_prompt(self, prompt_manager: PromptManager):
        """Test deleting non-existent prompt."""
        with pytest.raises(FileNotFoundError) as exc_info:
            await prompt_manager.delete_prompt("nonexistent")
        
        assert "not found" in str(exc_info.value)
    
    def test_populate_prompt_basic(self, prompt_manager: PromptManager):
        """Test basic template population."""
        template = "Review this code: {{ code_diff }}"
        data = {"code_diff": "diff content here"}
        
        result = prompt_manager.populate_prompt(template, data)
        
        assert result == "Review this code: diff content here"
    
    def test_populate_prompt_with_git_diff(self, prompt_manager: PromptManager):
        """Test template population with GitDiff object."""
        template = """Branch: {{ branch }}
Files changed: {{ files_changed }}
Lines added: {{ lines_added }}
Code: {{ code_diff }}"""
        
        # Create mock GitDiff
        stats = GitStats(files_changed=2, insertions=10, deletions=5)
        files = [
            FileChange(path="test.py", status="modified", insertions=10, deletions=5, content="diff content")
        ]
        git_diff = GitDiff(
            branch="feature-branch",
            commit_hash="abc123",
            commit_message="Test commit",
            author="Test User",
            stats=stats,
            files=files
        )
        
        data = {"git_diff": git_diff, "code_diff": "actual diff content"}
        
        result = prompt_manager.populate_prompt(template, data)
        
        assert "Branch: feature-branch" in result
        assert "Files changed: 2" in result
        assert "Lines added: 10" in result
        assert "Code: actual diff content" in result
    
    def test_populate_prompt_with_filters(self, prompt_manager: PromptManager):
        """Test template population with Jinja2 filters."""
        template = """Timestamp: {{ timestamp | format_date }}
Token count: {{ tokens | format_number }}"""
        
        from datetime import datetime
        data = {
            "timestamp": datetime(2024, 1, 15, 10, 30, 0),
            "tokens": 1500
        }
        
        result = prompt_manager.populate_prompt(template, data)
        
        assert "2024-01-15 10:30:00" in result
        assert "1,500" in result
    
    def test_populate_prompt_invalid_syntax(self, prompt_manager: PromptManager):
        """Test template population with invalid syntax."""
        template = "{{ invalid syntax }}"
        data = {}
        
        with pytest.raises(ValueError) as exc_info:
            prompt_manager.populate_prompt(template, data)
        
        assert "Template rendering error" in str(exc_info.value)
    
    def test_validate_prompt_valid(self, prompt_manager: PromptManager):
        """Test validating a valid prompt template."""
        template = """# Valid Template
Review code: {{ code_diff }}
Branch: {{ branch }}"""
        
        validation = prompt_manager.validate_prompt(template)
        
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert "code_diff" in validation["variables"]
        assert "branch" in validation["variables"]
    
    def test_validate_prompt_missing_required_variable(self, prompt_manager: PromptManager):
        """Test validating prompt missing required variables."""
        template = "Review code without required variable"
        
        validation = prompt_manager.validate_prompt(template)
        
        assert validation["valid"] is False
        assert any("code_diff" in error for error in validation["errors"])
    
    def test_validate_prompt_empty(self, prompt_manager: PromptManager):
        """Test validating empty prompt."""
        template = ""
        
        validation = prompt_manager.validate_prompt(template)
        
        assert validation["valid"] is False
        assert any("empty" in error.lower() for error in validation["errors"])
    
    def test_validate_prompt_syntax_error(self, prompt_manager: PromptManager):
        """Test validating prompt with syntax errors."""
        template = "{{ code_diff }} {{ unclosed"
        
        validation = prompt_manager.validate_prompt(template)
        
        assert validation["valid"] is False
        assert any("syntax error" in error.lower() for error in validation["errors"])
    
    def test_validate_prompt_warnings(self, prompt_manager: PromptManager):
        """Test prompt validation warnings."""
        # Very long template
        long_template = "{{ code_diff }}" + "x" * 10000
        
        validation = prompt_manager.validate_prompt(long_template)
        
        assert validation["valid"] is True  # Still valid, just with warnings
        assert any("very long" in warning.lower() for warning in validation["warnings"])
    
    def test_extract_variables(self, prompt_manager: PromptManager):
        """Test variable extraction from templates."""
        template = """
Review {{ code_diff }} for branch {{ branch }}.
Author: {{ git_diff.author }}
Time: {{ timestamp | format_date }}
"""
        
        variables = prompt_manager._extract_variables(template)
        
        assert "code_diff" in variables
        assert "branch" in variables
        assert "git_diff" in variables
        assert "timestamp" in variables
    
    def test_extract_metadata_with_yaml(self, prompt_manager: PromptManager):
        """Test extracting YAML metadata from template."""
        template = """---
description: "Security review template"
author: "Security Team"
version: "1.0"
---
# Security Review

{{ code_diff }}
"""
        
        metadata = prompt_manager._extract_metadata(template)
        
        assert metadata["description"] == "Security review template"
        assert metadata["author"] == "Security Team"
        assert metadata["version"] == "1.0"
    
    def test_extract_metadata_without_yaml(self, prompt_manager: PromptManager):
        """Test extracting metadata from template without YAML."""
        template = "# Simple Template\n{{ code_diff }}"
        
        metadata = prompt_manager._extract_metadata(template)
        
        assert metadata == {}
    
    def test_extract_description_from_heading(self, prompt_manager: PromptManager):
        """Test extracting description from template heading."""
        template = """# Code Quality Review Template
Review for quality issues:
{{ code_diff }}"""
        
        description = prompt_manager._extract_description(template)
        
        assert description == "Code Quality Review Template"
    
    def test_extract_description_from_first_line(self, prompt_manager: PromptManager):
        """Test extracting description from first non-template line."""
        template = """This is a description line.
{{ code_diff }}"""
        
        description = prompt_manager._extract_description(template)
        
        assert description == "This is a description line."
    
    def test_extract_description_default(self, prompt_manager: PromptManager):
        """Test default description when none found."""
        template = "{{ code_diff }}"
        
        description = prompt_manager._extract_description(template)
        
        assert description == "Custom prompt template"
    
    @pytest.mark.asyncio
    async def test_export_prompt(self, prompt_manager: PromptManager, temp_dir: Path):
        """Test exporting prompt template."""
        output_file = temp_dir / "exported_default.md"
        
        await prompt_manager.export_prompt("default", output_file)
        
        assert output_file.exists()
        
        exported_content = output_file.read_text()
        original_content = await prompt_manager.load_prompt("default")
        
        assert exported_content == original_content
    
    @pytest.mark.asyncio
    async def test_import_prompt(self, temp_dir: Path):
        """Test importing prompt template."""
        prompts_dir = temp_dir / "prompts"
        manager = PromptManager(prompts_dir=prompts_dir)
        
        # Create source file
        source_file = temp_dir / "import_template.md"
        source_content = """# Imported Template
This is an imported template:
{{ code_diff }}"""
        source_file.write_text(source_content)
        
        await manager.import_prompt(source_file, "imported")
        
        # Verify imported template
        imported_content = await manager.load_prompt("imported")
        assert imported_content == source_content
    
    @pytest.mark.asyncio
    async def test_import_prompt_with_filename(self, temp_dir: Path):
        """Test importing prompt using filename as template name."""
        prompts_dir = temp_dir / "prompts"
        manager = PromptManager(prompts_dir=prompts_dir)
        
        # Create source file
        source_file = temp_dir / "auto_named.md"
        source_content = "Template content: {{ code_diff }}"
        source_file.write_text(source_content)
        
        await manager.import_prompt(source_file)  # No name provided
        
        # Should use file stem as name
        imported_content = await manager.load_prompt("auto_named")
        assert imported_content == source_content
    
    @pytest.mark.asyncio
    async def test_import_nonexistent_file(self, temp_dir: Path):
        """Test importing from non-existent file."""
        prompts_dir = temp_dir / "prompts"
        manager = PromptManager(prompts_dir=prompts_dir)
        
        nonexistent_file = temp_dir / "nonexistent.md"
        
        with pytest.raises(FileNotFoundError):
            await manager.import_prompt(nonexistent_file)