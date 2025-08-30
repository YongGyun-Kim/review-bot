"""Tests for Pydantic models and types."""

import pytest
from pathlib import Path
from datetime import datetime
from pydantic import ValidationError

from models.types import (
    Provider, Priority, Severity, FileStatus,
    ReviewConfig, ReviewResult, TodoItem, GitDiff, FileChange, GitStats,
    PromptTemplate, Issue
)


class TestEnums:
    """Test enum types."""
    
    def test_provider_enum(self):
        """Test Provider enum values."""
        assert Provider.CLAUDE == "claude"
        assert Provider.CHATGPT == "chatgpt"
        assert Provider.GEMINI == "gemini"
        
        # Test case insensitive creation
        assert Provider("CLAUDE") == Provider.CLAUDE
        assert Provider("ChatGPT") == Provider.CHATGPT
    
    def test_priority_enum(self):
        """Test Priority enum values."""
        assert Priority.LOW == "low"
        assert Priority.MEDIUM == "medium"
        assert Priority.HIGH == "high"
        assert Priority.CRITICAL == "critical"
    
    def test_severity_enum(self):
        """Test Severity enum values."""
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.ERROR == "error"
        assert Severity.CRITICAL == "critical"
    
    def test_file_status_enum(self):
        """Test FileStatus enum values."""
        assert FileStatus.ADDED == "added"
        assert FileStatus.MODIFIED == "modified"
        assert FileStatus.DELETED == "deleted"
        assert FileStatus.RENAMED == "renamed"


class TestReviewConfig:
    """Test ReviewConfig model."""
    
    def test_valid_config(self):
        """Test valid configuration creation."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
            output_dir=Path("reviews"),
            max_files_per_review=10,
            max_tokens=100000,
            temperature=0.1,
            auto_review={
                "on_commit": True,
                "on_push": False
            }
        )
        
        assert config.provider == Provider.CLAUDE
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.api_key == "test-key"
        assert config.output_dir == Path("reviews")
        assert config.max_files_per_review == 10
        assert config.max_tokens == 100000
        assert config.temperature == 0.1
        assert config.auto_review["on_commit"] is True
        assert config.auto_review["on_push"] is False
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        assert config.model is None
        assert config.output_dir == Path("reviews")
        assert config.max_files_per_review == 50
        assert config.max_tokens == 100000
        assert config.temperature == 0.1
        assert config.auto_review == {}
    
    def test_invalid_temperature(self):
        """Test invalid temperature values."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewConfig(
                provider=Provider.CLAUDE,
                api_key="test-key",
                temperature=2.0  # > 1.0
            )
        assert "ensure this value is less than or equal to 1" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            ReviewConfig(
                provider=Provider.CLAUDE,
                api_key="test-key",
                temperature=-0.1  # < 0.0
            )
        assert "ensure this value is greater than or equal to 0" in str(exc_info.value)
    
    def test_invalid_max_files(self):
        """Test invalid max_files_per_review values."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewConfig(
                provider=Provider.CLAUDE,
                api_key="test-key",
                max_files_per_review=0  # Must be > 0
            )
        assert "ensure this value is greater than 0" in str(exc_info.value)


class TestGitDiffModels:
    """Test Git diff related models."""
    
    def test_git_stats(self):
        """Test GitStats model."""
        stats = GitStats(
            files_changed=5,
            insertions=100,
            deletions=50
        )
        
        assert stats.files_changed == 5
        assert stats.insertions == 100
        assert stats.deletions == 50
    
    def test_file_change(self):
        """Test FileChange model."""
        file_change = FileChange(
            path="src/main.py",
            status=FileStatus.MODIFIED,
            insertions=10,
            deletions=5,
            content="@@ -1,5 +1,10 @@\n+print('hello')\n-print('world')"
        )
        
        assert file_change.path == "src/main.py"
        assert file_change.status == FileStatus.MODIFIED
        assert file_change.insertions == 10
        assert file_change.deletions == 5
        assert "print('hello')" in file_change.content
    
    def test_git_diff(self):
        """Test GitDiff model."""
        stats = GitStats(files_changed=2, insertions=20, deletions=10)
        files = [
            FileChange(
                path="src/main.py",
                status=FileStatus.MODIFIED,
                insertions=15,
                deletions=8,
                content="diff content"
            ),
            FileChange(
                path="src/utils.py",
                status=FileStatus.ADDED,
                insertions=5,
                deletions=2,
                content="diff content"
            )
        ]
        
        diff = GitDiff(
            branch="main",
            commit_hash="abc123",
            commit_message="Test commit",
            author="Test User <test@example.com>",
            timestamp=datetime.now(),
            stats=stats,
            files=files
        )
        
        assert diff.branch == "main"
        assert diff.commit_hash == "abc123"
        assert diff.commit_message == "Test commit"
        assert diff.author == "Test User <test@example.com>"
        assert diff.stats == stats
        assert len(diff.files) == 2
        assert diff.files[0].path == "src/main.py"


class TestTodoItem:
    """Test TodoItem model."""
    
    def test_valid_todo_item(self):
        """Test valid TodoItem creation."""
        todo = TodoItem(
            id="todo-001",
            title="Fix authentication bug",
            description="The login form doesn't validate properly",
            priority=Priority.HIGH,
            status=TodoStatus.PENDING,
            assignee="developer",
            file="auth.py",
            line=45,
            created_at=datetime.now()
        )
        
        assert todo.id == "todo-001"
        assert todo.title == "Fix authentication bug"
        assert todo.priority == Priority.HIGH
        assert todo.status == TodoStatus.PENDING
        assert todo.assignee == "developer"
        assert todo.file == "auth.py"
        assert todo.line == 45
    
    def test_todo_item_defaults(self):
        """Test TodoItem default values."""
        todo = TodoItem(
            id="todo-001",
            title="Test todo"
        )
        
        assert todo.description == ""
        assert todo.priority == Priority.MEDIUM
        assert todo.status == TodoStatus.PENDING
        assert todo.assignee is None
        assert todo.file is None
        assert todo.line is None
        assert todo.completed_at is None


class TestIssue:
    """Test Issue model."""
    
    def test_valid_issue(self):
        """Test valid Issue creation."""
        issue = Issue(
            type="bug",
            severity=Severity.MAJOR,
            message="Potential null pointer exception",
            file="main.py",
            line=10
        )
        
        assert issue.type == "bug"
        assert issue.severity == Severity.MAJOR
        assert issue.message == "Potential null pointer exception"
        assert issue.file == "main.py"
        assert issue.line == 10
    
    def test_issue_defaults(self):
        """Test Issue default values."""
        issue = Issue(
            type="style",
            severity=Severity.MINOR,
            message="Code style issue"
        )
        
        assert issue.file is None
        assert issue.line is None


class TestReviewResult:
    """Test ReviewResult model."""
    
    def test_valid_review_result(self):
        """Test valid ReviewResult creation."""
        issues = [
            Issue(
                type="bug",
                severity=Severity.MAJOR,
                message="Test issue"
            )
        ]
        
        result = ReviewResult(
            timestamp=datetime.now(),
            provider=Provider.CLAUDE,
            model="claude-3-5-sonnet-20241022",
            review="This is a test review",
            issues=issues,
            suggestions=["Add tests", "Improve documentation"],
            files_reviewed=["main.py", "utils.py"],
            tokens_used=1500,
            estimated_cost=0.05
        )
        
        assert result.provider == Provider.CLAUDE
        assert result.model == "claude-3-5-sonnet-20241022"
        assert result.review == "This is a test review"
        assert len(result.issues) == 1
        assert len(result.suggestions) == 2
        assert len(result.files_reviewed) == 2
        assert result.tokens_used == 1500
        assert result.estimated_cost == 0.05
    
    def test_review_result_defaults(self):
        """Test ReviewResult default values."""
        result = ReviewResult(
            timestamp=datetime.now(),
            provider=Provider.CLAUDE,
            review="Test review"
        )
        
        assert result.model is None
        assert result.issues == []
        assert result.suggestions == []
        assert result.files_reviewed == []
        assert result.tokens_used is None
        assert result.estimated_cost is None


class TestPromptTemplate:
    """Test PromptTemplate model."""
    
    def test_valid_prompt_template(self):
        """Test valid PromptTemplate creation."""
        template = PromptTemplate(
            name="custom",
            description="Custom review template",
            template="Review this code: {{ code_diff }}",
            variables=["code_diff", "branch"]
        )
        
        assert template.name == "custom"
        assert template.description == "Custom review template"
        assert template.template == "Review this code: {{ code_diff }}"
        assert "code_diff" in template.variables
        assert "branch" in template.variables
    
    def test_prompt_template_defaults(self):
        """Test PromptTemplate default values."""
        template = PromptTemplate(
            name="test",
            template="Test template"
        )
        
        assert template.description == ""
        assert template.variables == []