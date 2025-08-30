"""TODO management system for tracking review suggestions."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TaskProgressColumn
from rich import box

from models.types import TodoItem, Priority, Suggestion


class TodoManager:
    """Manages TODO items from code reviews."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize TODO manager.
        
        Args:
            output_dir: Directory for TODO storage
        """
        self.output_dir = output_dir or Path("reviews")
        self.todo_dir = self.output_dir / "todo"
        self.todo_dir.mkdir(parents=True, exist_ok=True)
        
        self.console = Console()
    
    async def get_all_todos(self) -> List[TodoItem]:
        """Get all TODO items.
        
        Returns:
            List of all TodoItem objects
        """
        todos = []
        
        for todo_file in self.todo_dir.glob("todo_*.json"):
            try:
                data = json.loads(todo_file.read_text(encoding='utf-8'))
                
                # Handle both single todo and list of todos
                if isinstance(data, list):
                    for item in data:
                        todos.append(self._parse_todo_item(item))
                else:
                    todos.append(self._parse_todo_item(data))
                    
            except (json.JSONDecodeError, KeyError) as e:
                self.console.print(f"[yellow]Warning: Failed to load {todo_file}: {e}[/yellow]")
                continue
        
        # Sort by priority and creation date
        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        todos.sort(
            key=lambda t: (
                t.completed,  # Incomplete first
                priority_order.get(t.priority, 999),
                t.created_at
            )
        )
        
        return todos
    
    async def get_active_todos(self) -> List[TodoItem]:
        """Get only active (not completed) TODO items.
        
        Returns:
            List of active TodoItem objects
        """
        all_todos = await self.get_all_todos()
        return [todo for todo in all_todos if not todo.completed]
    
    async def get_completed_todos(self) -> List[TodoItem]:
        """Get only completed TODO items.
        
        Returns:
            List of completed TodoItem objects
        """
        all_todos = await self.get_all_todos()
        return [todo for todo in all_todos if todo.completed]
    
    async def get_todo_by_id(self, todo_id: str) -> Optional[TodoItem]:
        """Get a specific TODO by ID.
        
        Args:
            todo_id: TODO item ID
            
        Returns:
            TodoItem if found, None otherwise
        """
        all_todos = await self.get_all_todos()
        for todo in all_todos:
            if todo.id == todo_id:
                return todo
        return None
    
    async def mark_completed(self, todo_id: str) -> bool:
        """Mark a TODO item as completed.
        
        Args:
            todo_id: TODO item ID
            
        Returns:
            True if successful, False otherwise
        """
        todo = await self.get_todo_by_id(todo_id)
        if not todo:
            self.console.print(f"[red]TODO item '{todo_id}' not found[/red]")
            return False
        
        if todo.completed:
            self.console.print(f"[yellow]TODO item '{todo_id}' is already completed[/yellow]")
            return True
        
        todo.completed = True
        await self._update_todo(todo)
        
        self.console.print(f"[green]✓ Marked TODO '{todo.title}' as completed[/green]")
        return True
    
    async def mark_active(self, todo_id: str) -> bool:
        """Mark a TODO item as active (not completed).
        
        Args:
            todo_id: TODO item ID
            
        Returns:
            True if successful, False otherwise
        """
        todo = await self.get_todo_by_id(todo_id)
        if not todo:
            self.console.print(f"[red]TODO item '{todo_id}' not found[/red]")
            return False
        
        if not todo.completed:
            self.console.print(f"[yellow]TODO item '{todo_id}' is already active[/yellow]")
            return True
        
        todo.completed = False
        await self._update_todo(todo)
        
        self.console.print(f"[blue]↺ Marked TODO '{todo.title}' as active[/blue]")
        return True
    
    async def delete_todo(self, todo_id: str) -> bool:
        """Delete a TODO item.
        
        Args:
            todo_id: TODO item ID
            
        Returns:
            True if successful, False otherwise
        """
        todo = await self.get_todo_by_id(todo_id)
        if not todo:
            self.console.print(f"[red]TODO item '{todo_id}' not found[/red]")
            return False
        
        # Find and update the file containing this TODO
        for todo_file in self.todo_dir.glob("todo_*.json"):
            try:
                data = json.loads(todo_file.read_text(encoding='utf-8'))
                
                if isinstance(data, list):
                    filtered_data = [item for item in data if item.get('id') != todo_id]
                    if len(filtered_data) < len(data):
                        if filtered_data:
                            todo_file.write_text(json.dumps(filtered_data, indent=2), encoding='utf-8')
                        else:
                            todo_file.unlink()  # Delete empty file
                        
                        self.console.print(f"[red]🗑 Deleted TODO '{todo.title}'[/red]")
                        return True
                        
            except (json.JSONDecodeError, KeyError):
                continue
        
        return False
    
    async def update_todo(
        self,
        todo_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[Priority] = None,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> bool:
        """Update a TODO item.
        
        Args:
            todo_id: TODO item ID
            title: New title
            description: New description
            priority: New priority
            assignee: New assignee
            due_date: New due date
            
        Returns:
            True if successful, False otherwise
        """
        todo = await self.get_todo_by_id(todo_id)
        if not todo:
            self.console.print(f"[red]TODO item '{todo_id}' not found[/red]")
            return False
        
        if title:
            todo.title = title
        if description:
            todo.description = description
        if priority:
            todo.priority = priority
        if assignee is not None:
            todo.assignee = assignee
        if due_date is not None:
            todo.due_date = due_date
        
        await self._update_todo(todo)
        
        self.console.print(f"[green]Updated TODO '{todo.title}'[/green]")
        return True
    
    async def create_todo(
        self,
        title: str,
        description: str,
        priority: Priority = Priority.MEDIUM,
        files: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> TodoItem:
        """Create a new TODO item.
        
        Args:
            title: TODO title
            description: TODO description
            priority: Priority level
            files: Related files
            assignee: Assigned to
            due_date: Due date
            
        Returns:
            Created TodoItem
        """
        todo = TodoItem(
            id=f"todo-{uuid4().hex[:8]}",
            title=title,
            description=description,
            priority=priority,
            files=files or [],
            completed=False,
            created_at=datetime.now(),
            review_id=f"manual-{datetime.now().strftime('%Y%m%d')}",
            assignee=assignee,
            due_date=due_date
        )
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        todo_file = self.todo_dir / f"todo_manual_{timestamp}.json"
        
        todo_data = self._serialize_todo(todo)
        todo_file.write_text(json.dumps([todo_data], indent=2), encoding='utf-8')
        
        self.console.print(f"[green]Created TODO: {todo.title}[/green]")
        return todo
    
    async def display_todos(
        self,
        show_completed: bool = False,
        filter_priority: Optional[Priority] = None,
        filter_assignee: Optional[str] = None,
        search: Optional[str] = None
    ) -> None:
        """Display TODO items in a formatted table.
        
        Args:
            show_completed: Include completed TODOs
            filter_priority: Filter by priority
            filter_assignee: Filter by assignee
            search: Search in title and description
        """
        todos = await self.get_all_todos()
        
        # Apply filters
        if not show_completed:
            todos = [t for t in todos if not t.completed]
        
        if filter_priority:
            todos = [t for t in todos if t.priority == filter_priority]
        
        if filter_assignee:
            todos = [t for t in todos if t.assignee == filter_assignee]
        
        if search:
            search_lower = search.lower()
            todos = [
                t for t in todos
                if search_lower in t.title.lower() or search_lower in t.description.lower()
            ]
        
        if not todos:
            self.console.print("[yellow]No TODO items found[/yellow]")
            return
        
        # Create table
        table = Table(
            title="📋 TODO Items",
            box=box.ROUNDED,
            show_lines=True,
            title_style="bold cyan"
        )
        
        table.add_column("ID", style="dim", width=12)
        table.add_column("Status", width=8)
        table.add_column("Priority", width=8)
        table.add_column("Title", width=30)
        table.add_column("Description", width=40)
        table.add_column("Created", width=10)
        table.add_column("Assignee", width=10)
        
        for todo in todos:
            status = "✅" if todo.completed else "⭕"
            
            priority_style = {
                Priority.HIGH: "red",
                Priority.MEDIUM: "yellow",
                Priority.LOW: "green"
            }.get(todo.priority, "white")
            
            priority_icon = {
                Priority.HIGH: "🔴",
                Priority.MEDIUM: "🟡",
                Priority.LOW: "🟢"
            }.get(todo.priority, "⚪")
            
            # Truncate description
            desc = todo.description[:37] + "..." if len(todo.description) > 40 else todo.description
            
            table.add_row(
                todo.id,
                status,
                f"{priority_icon} {todo.priority.value}",
                todo.title,
                desc,
                todo.created_at.strftime("%Y-%m-%d"),
                todo.assignee or "-"
            )
        
        self.console.print(table)
        
        # Show summary
        active_count = sum(1 for t in todos if not t.completed)
        completed_count = sum(1 for t in todos if t.completed)
        
        self.console.print(
            f"\n[cyan]Total:[/cyan] {len(todos)} | "
            f"[yellow]Active:[/yellow] {active_count} | "
            f"[green]Completed:[/green] {completed_count}"
        )
    
    async def display_progress(self) -> None:
        """Display TODO completion progress."""
        todos = await self.get_all_todos()
        
        if not todos:
            self.console.print("[yellow]No TODO items to show progress[/yellow]")
            return
        
        # Calculate statistics
        total = len(todos)
        completed = sum(1 for t in todos if t.completed)
        active = total - completed
        
        # Priority breakdown
        high_count = sum(1 for t in todos if t.priority == Priority.HIGH and not t.completed)
        medium_count = sum(1 for t in todos if t.priority == Priority.MEDIUM and not t.completed)
        low_count = sum(1 for t in todos if t.priority == Priority.LOW and not t.completed)
        
        # Create progress bar
        progress = Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        
        with progress:
            task = progress.add_task(
                "[cyan]Overall Progress",
                total=total,
                completed=completed
            )
            progress.update(task, completed=completed)
        
        # Display statistics panel
        stats_content = f"""
[bold]📊 TODO Statistics[/bold]

Total TODOs: {total}
Completed: {completed} ({completed/total*100:.1f}%)
Active: {active}

[bold]Priority Breakdown (Active):[/bold]
🔴 High: {high_count}
🟡 Medium: {medium_count}
🟢 Low: {low_count}
"""
        
        panel = Panel(
            stats_content.strip(),
            title="Progress Report",
            border_style="cyan",
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    async def export_todos(
        self,
        format: str = "json",
        output_path: Optional[Path] = None
    ) -> Path:
        """Export TODO items to file.
        
        Args:
            format: Export format (json, csv, markdown)
            output_path: Output file path
            
        Returns:
            Path to exported file
        """
        todos = await self.get_all_todos()
        
        if not todos:
            raise ValueError("No TODO items to export")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not output_path:
            filename = f"todos_export_{timestamp}.{format}"
            output_path = Path(filename)
        
        if format == "json":
            data = [self._serialize_todo(todo) for todo in todos]
            output_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
            
        elif format == "csv":
            import csv
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['id', 'title', 'description', 'priority', 'status', 
                               'created_at', 'assignee', 'due_date', 'files']
                )
                writer.writeheader()
                
                for todo in todos:
                    writer.writerow({
                        'id': todo.id,
                        'title': todo.title,
                        'description': todo.description,
                        'priority': todo.priority.value,
                        'status': 'completed' if todo.completed else 'active',
                        'created_at': todo.created_at.isoformat(),
                        'assignee': todo.assignee or '',
                        'due_date': todo.due_date.isoformat() if todo.due_date else '',
                        'files': ', '.join(todo.files)
                    })
                    
        elif format == "markdown":
            lines = ["# TODO Items Export", ""]
            lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*", "")
            
            # Active TODOs
            active_todos = [t for t in todos if not t.completed]
            if active_todos:
                lines.append("## 📋 Active TODOs")
                lines.append("")
                
                for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                    priority_todos = [t for t in active_todos if t.priority == priority]
                    if priority_todos:
                        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[priority.value]
                        lines.append(f"### {icon} {priority.value.title()} Priority")
                        lines.append("")
                        
                        for todo in priority_todos:
                            lines.append(f"- **[{todo.id}]** {todo.title}")
                            lines.append(f"  - {todo.description}")
                            if todo.assignee:
                                lines.append(f"  - Assignee: {todo.assignee}")
                            if todo.due_date:
                                lines.append(f"  - Due: {todo.due_date.strftime('%Y-%m-%d')}")
                            lines.append("")
            
            # Completed TODOs
            completed_todos = [t for t in todos if t.completed]
            if completed_todos:
                lines.append("## ✅ Completed TODOs")
                lines.append("")
                
                for todo in completed_todos:
                    lines.append(f"- ~~[{todo.id}] {todo.title}~~")
                lines.append("")
            
            # Statistics
            lines.append("## 📊 Statistics")
            lines.append("")
            lines.append(f"- Total: {len(todos)}")
            lines.append(f"- Active: {len(active_todos)}")
            lines.append(f"- Completed: {len(completed_todos)}")
            lines.append(f"- Completion Rate: {len(completed_todos)/len(todos)*100:.1f}%")
            
            output_path.write_text('\n'.join(lines), encoding='utf-8')
            
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        self.console.print(f"[green]TODOs exported to: {output_path}[/green]")
        return output_path
    
    async def get_overdue_todos(self) -> List[TodoItem]:
        """Get overdue TODO items.
        
        Returns:
            List of overdue TodoItem objects
        """
        todos = await self.get_active_todos()
        now = datetime.now()
        
        return [
            todo for todo in todos
            if todo.due_date and todo.due_date < now
        ]
    
    async def get_upcoming_todos(self, days: int = 7) -> List[TodoItem]:
        """Get upcoming TODO items within specified days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of upcoming TodoItem objects
        """
        todos = await self.get_active_todos()
        now = datetime.now()
        future = now + timedelta(days=days)
        
        return [
            todo for todo in todos
            if todo.due_date and now <= todo.due_date <= future
        ]
    
    def _parse_todo_item(self, data: Dict[str, Any]) -> TodoItem:
        """Parse TODO item from dictionary.
        
        Args:
            data: TODO data dictionary
            
        Returns:
            TodoItem object
        """
        return TodoItem(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            files=data.get('files', []),
            priority=Priority(data.get('priority', 'medium')),
            completed=data.get('completed', False),
            example=data.get('example'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            review_id=data.get('review_id', 'unknown'),
            assignee=data.get('assignee'),
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
        )
    
    def _serialize_todo(self, todo: TodoItem) -> Dict[str, Any]:
        """Serialize TODO item to dictionary.
        
        Args:
            todo: TodoItem object
            
        Returns:
            Serialized dictionary
        """
        return {
            'id': todo.id,
            'title': todo.title,
            'description': todo.description,
            'files': todo.files,
            'priority': todo.priority.value,
            'completed': todo.completed,
            'example': todo.example,
            'created_at': todo.created_at.isoformat(),
            'review_id': todo.review_id,
            'assignee': todo.assignee,
            'due_date': todo.due_date.isoformat() if todo.due_date else None
        }
    
    async def _update_todo(self, todo: TodoItem) -> None:
        """Update TODO item in storage.
        
        Args:
            todo: TodoItem to update
        """
        # Find the file containing this TODO
        for todo_file in self.todo_dir.glob("todo_*.json"):
            try:
                data = json.loads(todo_file.read_text(encoding='utf-8'))
                
                if isinstance(data, list):
                    for i, item in enumerate(data):
                        if item.get('id') == todo.id:
                            data[i] = self._serialize_todo(todo)
                            todo_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
                            return
                            
            except (json.JSONDecodeError, KeyError):
                continue
        
        # If not found, create new file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        todo_file = self.todo_dir / f"todo_updated_{timestamp}.json"
        todo_file.write_text(json.dumps([self._serialize_todo(todo)], indent=2), encoding='utf-8')