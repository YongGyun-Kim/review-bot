"""Tests for TodoManager."""

import pytest
from pathlib import Path
from datetime import datetime
import json
import tempfile
import shutil

from core.todo_manager import TodoManager
from models.types import TodoItem, Priority


class TestTodoManager:
    """Test TodoManager functionality."""
    
    @pytest.mark.asyncio
    async def test_create_todo_basic(self, todo_manager: TodoManager):
        """Test creating a basic TODO item."""
        todo_item = await todo_manager.create_todo(
            "Fix authentication bug",
            "The login form doesn't validate properly",
            priority=Priority.HIGH
        )
        
        assert todo_item is not None
        assert isinstance(todo_item, TodoItem)
        assert todo_item.title == "Fix authentication bug"
        assert todo_item.description == "The login form doesn't validate properly"
        assert todo_item.priority == Priority.HIGH
    
    @pytest.mark.asyncio
    async def test_create_todo_with_file_location(self, todo_manager: TodoManager):
        """Test creating TODO with file and line information."""
        todo_id = await todo_manager.create_todo(
            "Add type hints",
            "Function parameters need type annotations",
            priority=Priority.MEDIUM,
            assignee="developer",
            file="auth.py",
            line=25
        )
        
        # Retrieve and verify
        todos = await todo_manager.get_active_todos()
        created_todo = next((t for t in todos if t.id == todo_id), None)
        
        assert created_todo is not None
        assert created_todo.title == "Add type hints"
        assert created_todo.priority == Priority.MEDIUM
        assert created_todo.assignee == "developer"
        assert created_todo.file == "auth.py"
        assert created_todo.line == 25
    
    @pytest.mark.asyncio
    async def test_get_active_todos(self, todo_manager: TodoManager):
        """Test getting active TODO items."""
        # Create several TODOs
        await todo_manager.create_todo("Task 1", priority=Priority.HIGH)
        await todo_manager.create_todo("Task 2", priority=Priority.MEDIUM)
        await todo_manager.create_todo("Task 3", priority=Priority.LOW)
        
        active_todos = await todo_manager.get_active_todos()
        
        assert len(active_todos) == 3
        assert all(not todo.completed for todo in active_todos)
        
        # Should be sorted by priority (HIGH, MEDIUM, LOW)
        priorities = [todo.priority for todo in active_todos]
        assert priorities[0] == Priority.HIGH
    
    @pytest.mark.asyncio
    async def test_mark_completed(self, todo_manager: TodoManager):
        """Test marking TODO as completed."""
        todo_id = await todo_manager.create_todo("Complete me", priority=Priority.MEDIUM)
        
        # Mark as completed
        success = await todo_manager.mark_completed(todo_id)
        assert success is True
        
        # Verify it's no longer active
        active_todos = await todo_manager.get_active_todos()
        assert not any(t.id == todo_id for t in active_todos)
        
        # Verify it's in completed list
        completed_todos = await todo_manager.get_completed_todos()
        completed_todo = next((t for t in completed_todos if t.id == todo_id), None)
        
        assert completed_todo is not None
        assert completed_todo.completed is True
    
    @pytest.mark.asyncio
    async def test_mark_active(self, todo_manager: TodoManager):
        """Test marking TODO as active/in-progress."""
        todo_id = await todo_manager.create_todo("Work on this", priority=Priority.MEDIUM)
        
        # Mark as active
        success = await todo_manager.mark_active(todo_id)
        assert success is True
        
        # Verify status changed
        active_todos = await todo_manager.get_active_todos()
        active_todo = next((t for t in active_todos if t.id == todo_id), None)
        
        assert active_todo is not None
        assert active_todo.status == TodoStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_delete_todo(self, todo_manager: TodoManager):
        """Test deleting a TODO item."""
        todo_id = await todo_manager.create_todo("Delete me", priority=Priority.LOW)
        
        # Verify it exists
        active_todos = await todo_manager.get_active_todos()
        assert any(t.id == todo_id for t in active_todos)
        
        # Delete it
        success = await todo_manager.delete_todo(todo_id)
        assert success is True
        
        # Verify it's gone
        active_todos = await todo_manager.get_active_todos()
        assert not any(t.id == todo_id for t in active_todos)
    
    @pytest.mark.asyncio
    async def test_get_todos_by_priority(self, todo_manager: TodoManager):
        """Test filtering TODOs by priority."""
        await todo_manager.create_todo("High priority", priority=Priority.HIGH)
        await todo_manager.create_todo("Medium priority", priority=Priority.MEDIUM)
        await todo_manager.create_todo("Low priority", priority=Priority.LOW)
        
        high_todos = await todo_manager.get_todos_by_priority(Priority.HIGH)
        assert len(high_todos) == 1
        assert high_todos[0].priority == Priority.HIGH
        
        medium_todos = await todo_manager.get_todos_by_priority(Priority.MEDIUM)
        assert len(medium_todos) == 1
        assert medium_todos[0].priority == Priority.MEDIUM
    
    @pytest.mark.asyncio
    async def test_get_todos_by_assignee(self, todo_manager: TodoManager):
        """Test filtering TODOs by assignee."""
        await todo_manager.create_todo("Task for Alice", assignee="alice", priority=Priority.HIGH)
        await todo_manager.create_todo("Task for Bob", assignee="bob", priority=Priority.MEDIUM)
        await todo_manager.create_todo("Unassigned task", priority=Priority.LOW)
        
        alice_todos = await todo_manager.get_todos_by_assignee("alice")
        assert len(alice_todos) == 1
        assert alice_todos[0].assignee == "alice"
        
        bob_todos = await todo_manager.get_todos_by_assignee("bob")
        assert len(bob_todos) == 1
        assert bob_todos[0].assignee == "bob"
        
        unassigned_todos = await todo_manager.get_todos_by_assignee(None)
        assert len(unassigned_todos) == 1
        assert unassigned_todos[0].assignee is None
    
    @pytest.mark.asyncio
    async def test_search_todos(self, todo_manager: TodoManager):
        """Test searching TODOs by text."""
        await todo_manager.create_todo(
            "Fix authentication bug",
            "Login form validation issue",
            priority=Priority.HIGH
        )
        await todo_manager.create_todo(
            "Add unit tests",
            "Need comprehensive test coverage",
            priority=Priority.MEDIUM
        )
        await todo_manager.create_todo(
            "Update documentation",
            "API docs need updating",
            priority=Priority.LOW
        )
        
        # Search by title
        auth_todos = await todo_manager.search_todos("authentication")
        assert len(auth_todos) == 1
        assert "authentication" in auth_todos[0].title.lower()
        
        # Search by description
        test_todos = await todo_manager.search_todos("test")
        assert len(test_todos) == 1
        assert "test" in test_todos[0].description.lower()
        
        # Search case insensitive
        doc_todos = await todo_manager.search_todos("API")
        assert len(doc_todos) == 1
    
    @pytest.mark.asyncio
    async def test_export_todos_json(self, todo_manager: TodoManager, temp_dir: Path):
        """Test exporting TODOs to JSON."""
        # Create some TODOs
        await todo_manager.create_todo("Task 1", priority=Priority.HIGH)
        await todo_manager.create_todo("Task 2", priority=Priority.MEDIUM)
        
        # Export
        output_file = temp_dir / "todos_export.json"
        result_path = await todo_manager.export_todos(format="json", output_path=output_file)
        
        assert result_path == output_file
        assert output_file.exists()
        
        # Verify content
        with open(output_file) as f:
            exported_data = json.load(f)
        
        assert "todos" in exported_data
        assert len(exported_data["todos"]) == 2
        assert exported_data["todos"][0]["title"] == "Task 1"
    
    @pytest.mark.asyncio
    async def test_export_todos_markdown(self, todo_manager: TodoManager, temp_dir: Path):
        """Test exporting TODOs to Markdown."""
        # Create TODOs with different statuses
        todo_id = await todo_manager.create_todo("Completed task", priority=Priority.HIGH)
        await todo_manager.mark_completed(todo_id)
        await todo_manager.create_todo("Active task", priority=Priority.MEDIUM)
        
        # Export
        output_file = temp_dir / "todos_export.md"
        result_path = await todo_manager.export_todos(format="markdown", output_path=output_file)
        
        assert result_path == output_file
        assert output_file.exists()
        
        # Verify content
        content = output_file.read_text()
        assert "# TODO Items" in content
        assert "Completed task" in content
        assert "Active task" in content
        assert "- [x]" in content  # Completed checkbox
        assert "- [ ]" in content  # Pending checkbox
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, todo_manager: TodoManager):
        """Test getting TODO statistics."""
        # Create TODOs with different statuses and priorities
        todo1 = await todo_manager.create_todo("High priority", priority=Priority.HIGH)
        todo2 = await todo_manager.create_todo("Medium priority", priority=Priority.MEDIUM)
        todo3 = await todo_manager.create_todo("Low priority", priority=Priority.LOW)
        
        # Complete one
        await todo_manager.mark_completed(todo1)
        
        # Mark one as in progress
        await todo_manager.mark_active(todo2)
        
        stats = await todo_manager.get_statistics()
        
        assert stats["total"] == 3
        assert stats["pending"] == 1
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["medium"] == 1
        assert stats["by_priority"]["low"] == 1
    
    @pytest.mark.asyncio
    async def test_invalid_todo_operations(self, todo_manager: TodoManager):
        """Test operations on non-existent TODOs."""
        # Mark non-existent TODO as completed
        success = await todo_manager.mark_completed("invalid-id")
        assert success is False
        
        # Mark non-existent TODO as active
        success = await todo_manager.mark_active("invalid-id")
        assert success is False
        
        # Delete non-existent TODO
        success = await todo_manager.delete_todo("invalid-id")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_todo_persistence(self, temp_dir: Path):
        """Test that TODOs persist across manager instances."""
        todos_dir = temp_dir / "persist_test"
        
        # Create manager and add TODOs
        manager1 = TodoManager(todos_dir=todos_dir)
        todo_id = await manager1.create_todo("Persistent task", priority=Priority.HIGH)
        
        # Create new manager instance
        manager2 = TodoManager(todos_dir=todos_dir)
        active_todos = await manager2.get_active_todos()
        
        # Should find the previously created TODO
        assert len(active_todos) == 1
        assert active_todos[0].id == todo_id
        assert active_todos[0].title == "Persistent task"
    
    @pytest.mark.asyncio
    async def test_auto_generated_id(self, todo_manager: TodoManager):
        """Test that TODO IDs are auto-generated and unique."""
        id1 = await todo_manager.create_todo("Task 1", priority=Priority.HIGH)
        id2 = await todo_manager.create_todo("Task 2", priority=Priority.HIGH)
        
        assert id1 != id2
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert len(id1) > 8  # Should be reasonably long
        assert len(id2) > 8
    
    @pytest.mark.asyncio
    async def test_todo_timestamps(self, todo_manager: TodoManager):
        """Test that TODOs have proper timestamps."""
        before_create = datetime.now()
        todo_id = await todo_manager.create_todo("Timestamped task", priority=Priority.MEDIUM)
        after_create = datetime.now()
        
        active_todos = await todo_manager.get_active_todos()
        created_todo = next(t for t in active_todos if t.id == todo_id)
        
        # Created timestamp should be between before and after
        assert before_create <= created_todo.created_at <= after_create
        assert created_todo.completed_at is None
        
        # Complete and check completion timestamp
        before_complete = datetime.now()
        await todo_manager.mark_completed(todo_id)
        after_complete = datetime.now()
        
        completed_todos = await todo_manager.get_completed_todos()
        completed_todo = next(t for t in completed_todos if t.id == todo_id)
        
        assert before_complete <= completed_todo.completed_at <= after_complete