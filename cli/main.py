#!/usr/bin/env python3
"""Main CLI interface for the review bot."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from rich.syntax import Syntax
from typing_extensions import Annotated

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.types import Provider, Priority
from core.review_manager import ReviewManager
from core.config_manager import ConfigManager
from core.todo_manager import TodoManager
from core.git_manager import GitManager
from core.prompt_manager import PromptManager
from providers import AVAILABLE_PROVIDERS, DEFAULT_MODELS

# Initialize Typer app
app = typer.Typer(
    name="review-bot",
    help="🤖 AI-powered code review bot with CLI and Web Dashboard",
    add_completion=True,
    rich_markup_mode="rich",
)

# Initialize console
console = Console()


# Sub-commands
config_app = typer.Typer(help="Configuration management")
todo_app = typer.Typer(help="TODO management")
prompt_app = typer.Typer(help="Prompt template management")
hooks_app = typer.Typer(help="Git hooks management")

app.add_typer(config_app, name="config")
app.add_typer(todo_app, name="todo")
app.add_typer(prompt_app, name="prompt")
app.add_typer(hooks_app, name="hooks")


@app.command()
def run(
    staged: Annotated[bool, typer.Option("--staged", "-s", help="Review only staged changes")] = False,
    commit: Annotated[Optional[str], typer.Option("--commit", "-c", help="Review specific commit")] = None,
    prompt: Annotated[Optional[str], typer.Option("--prompt", "-p", help="Prompt template to use")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "markdown",
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Interactive mode")] = False,
):
    """🚀 Run code review on current changes."""
    try:
        review_manager = ReviewManager()
        
        # Run async review
        result = asyncio.run(
            review_manager.run_review(
                staged=staged,
                commit_hash=commit,
                prompt_template=prompt,
                output_format=format,
                interactive=interactive
            )
        )
        
        # Show completion message
        console.print("\n[bold green]✅ Review completed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def status():
    """📊 Show current status and configuration."""
    try:
        config_manager = ConfigManager()
        git_manager = GitManager()
        todo_manager = TodoManager()
        
        # Load configuration
        config = asyncio.run(config_manager.load_config())
        
        # Get Git status
        is_git_repo = git_manager.is_git_repository()
        has_changes = git_manager.has_changes() if is_git_repo else False
        branch = git_manager.get_current_branch() if is_git_repo else "N/A"
        
        # Get TODO count
        active_todos = asyncio.run(todo_manager.get_active_todos())
        
        # Create status panel
        status_content = f"""
[bold cyan]🤖 Review Bot Status[/bold cyan]

[bold]Repository:[/bold]
  Git Repository: {'✅ Yes' if is_git_repo else '❌ No'}
  Current Branch: {branch}
  Has Changes: {'📝 Yes' if has_changes else '✅ No'}

[bold]Configuration:[/bold]
  Provider: {config.provider.value}
  Model: {config.model or DEFAULT_MODELS.get(config.provider, 'default')}
  API Key: {'✅ Set' if config.api_key else '❌ Not set'}
  Output Dir: {config.output_dir}

[bold]Auto Review:[/bold]
  On Commit: {'✅ Enabled' if config.auto_review.get('on_commit') else '❌ Disabled'}
  On Push: {'✅ Enabled' if config.auto_review.get('on_push') else '❌ Disabled'}

[bold]TODOs:[/bold]
  Active Items: {len(active_todos)}
"""
        
        panel = Panel(
            status_content.strip(),
            title="System Status",
            border_style="cyan",
            padding=(1, 2)
        )
        
        console.print(panel)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def providers():
    """🤖 List available AI providers and models."""
    table = Table(title="Available AI Providers", show_lines=True)
    
    table.add_column("Provider", style="cyan", width=15)
    table.add_column("Default Model", style="green", width=30)
    table.add_column("Environment Variable", style="yellow", width=25)
    table.add_column("Cost Estimate", style="magenta", width=20)
    
    provider_info = {
        "claude": ("ANTHROPIC_API_KEY", "$0.003-0.015/1K tokens"),
        "chatgpt": ("OPENAI_API_KEY", "$0.03-0.06/1K tokens"),
        "gemini": ("GOOGLE_API_KEY", "$0.00025-0.0005/1K tokens"),
    }
    
    for provider in AVAILABLE_PROVIDERS:
        model = DEFAULT_MODELS.get(Provider(provider), "default")
        env_var, cost = provider_info.get(provider, ("", ""))
        
        table.add_row(
            provider.title(),
            model,
            env_var,
            cost
        )
    
    console.print(table)
    
    console.print("\n[dim]Set your API keys using environment variables or config file[/dim]")


@app.command()
def dashboard(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to run on")] = 8000,
    host: Annotated[str, typer.Option("--host", "-h", help="Host to bind to")] = "127.0.0.1",
    reload: Annotated[bool, typer.Option("--reload", "-r", help="Enable auto-reload")] = False,
):
    """🌐 Launch the web dashboard."""
    console.print(f"[bold cyan]🚀 Launching web dashboard at http://{host}:{port}[/bold cyan]")
    
    try:
        import uvicorn
        from web.app import app as web_app
        
        uvicorn.run(
            web_app if not reload else "web.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except ImportError:
        console.print("[bold red]❌ Web dashboard dependencies not installed[/bold red]")
        console.print("Install with: pip install 'code-review-bot[web]'")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Failed to start dashboard:[/bold red] {e}")
        raise typer.Exit(1)


# Configuration commands
@config_app.command("init")
def config_init():
    """Initialize configuration file."""
    try:
        config_manager = ConfigManager()
        asyncio.run(config_manager.init_config())
        console.print("[bold green]✅ Configuration initialized successfully[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
    global_config: Annotated[bool, typer.Option("--global", "-g", help="Set global config")] = False,
):
    """Set configuration value."""
    try:
        config_manager = ConfigManager()
        
        # Parse value for specific keys
        if key in ["auto_review.on_commit", "auto_review.on_push"]:
            value = value.lower() in ["true", "yes", "1", "on"]
            key_parts = key.split(".")
            config = {key_parts[0]: {key_parts[1]: value}}
        elif key in ["max_files_per_review", "max_tokens"]:
            config = {key: int(value)}
        elif key == "temperature":
            config = {key: float(value)}
        else:
            config = {key: value}
        
        asyncio.run(config_manager.save_config(config, global_config))
        console.print(f"[bold green]✅ Configuration updated: {key} = {value}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@config_app.command("get")
def config_get(
    key: Optional[str] = typer.Argument(None, help="Configuration key"),
):
    """Get configuration value(s)."""
    try:
        config_manager = ConfigManager()
        config = asyncio.run(config_manager.load_config())
        
        if key:
            # Navigate nested keys
            value = config
            for part in key.split("."):
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    console.print(f"[yellow]Key '{key}' not found[/yellow]")
                    return
            
            console.print(f"{value}")
        else:
            # Show all configuration
            import json
            config_dict = config.model_dump()
            console.print(Syntax(
                json.dumps(config_dict, indent=2),
                "json",
                theme="monokai",
                line_numbers=False
            ))
            
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


# TODO commands
@todo_app.command("list")
def todo_list(
    all: Annotated[bool, typer.Option("--all", "-a", help="Show all todos including completed")] = False,
    priority: Annotated[Optional[str], typer.Option("--priority", "-p", help="Filter by priority")] = None,
    assignee: Annotated[Optional[str], typer.Option("--assignee", help="Filter by assignee")] = None,
    search: Annotated[Optional[str], typer.Option("--search", "-s", help="Search in title and description")] = None,
):
    """📋 List TODO items."""
    try:
        todo_manager = TodoManager()
        
        filter_priority = Priority(priority.lower()) if priority else None
        
        asyncio.run(
            todo_manager.display_todos(
                show_completed=all,
                filter_priority=filter_priority,
                filter_assignee=assignee,
                search=search
            )
        )
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@todo_app.command("complete")
def todo_complete(
    todo_id: str = typer.Argument(..., help="TODO item ID"),
):
    """✅ Mark TODO item as completed."""
    try:
        todo_manager = TodoManager()
        success = asyncio.run(todo_manager.mark_completed(todo_id))
        
        if not success:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@todo_app.command("activate")
def todo_activate(
    todo_id: str = typer.Argument(..., help="TODO item ID"),
):
    """↺ Mark TODO item as active."""
    try:
        todo_manager = TodoManager()
        success = asyncio.run(todo_manager.mark_active(todo_id))
        
        if not success:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@todo_app.command("delete")
def todo_delete(
    todo_id: str = typer.Argument(..., help="TODO item ID"),
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
):
    """🗑 Delete TODO item."""
    try:
        if not force:
            confirm = Confirm.ask(f"Are you sure you want to delete TODO '{todo_id}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return
        
        todo_manager = TodoManager()
        success = asyncio.run(todo_manager.delete_todo(todo_id))
        
        if not success:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@todo_app.command("progress")
def todo_progress():
    """📊 Show TODO completion progress."""
    try:
        todo_manager = TodoManager()
        asyncio.run(todo_manager.display_progress())
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@todo_app.command("export")
def todo_export(
    format: Annotated[str, typer.Option("--format", "-f", help="Export format")] = "json",
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output file path")] = None,
):
    """📤 Export TODO items."""
    try:
        todo_manager = TodoManager()
        output_path = asyncio.run(
            todo_manager.export_todos(format=format, output_path=output)
        )
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


# Prompt commands
@prompt_app.command("list")
def prompt_list():
    """📝 List available prompt templates."""
    try:
        prompt_manager = PromptManager()
        templates = asyncio.run(prompt_manager.get_available_prompts())
        
        if not templates:
            console.print("[yellow]No prompt templates found[/yellow]")
            return
        
        table = Table(title="Available Prompt Templates", show_lines=True)
        
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Description", style="green", width=50)
        table.add_column("Variables", style="yellow", width=30)
        
        for template in templates:
            variables = ", ".join(template.variables) if template.variables else "None"
            table.add_row(
                template.name,
                template.description[:47] + "..." if len(template.description) > 50 else template.description,
                variables
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@prompt_app.command("create")
def prompt_create(
    name: str = typer.Argument(..., help="Template name"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Template file"),
):
    """➕ Create a new prompt template."""
    try:
        prompt_manager = PromptManager()
        
        if file:
            if not file.exists():
                console.print(f"[bold red]❌ File not found: {file}[/bold red]")
                raise typer.Exit(1)
            content = file.read_text(encoding='utf-8')
        else:
            console.print("[cyan]Enter prompt template content (Ctrl+D to finish):[/cyan]")
            lines = []
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass
            content = '\n'.join(lines)
        
        asyncio.run(prompt_manager.create_prompt(name, content))
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


# Git hooks commands
@hooks_app.command("install")
def hooks_install():
    """🔧 Install Git hooks."""
    try:
        git_manager = GitManager()
        git_manager.install_hooks()
        console.print("[bold green]✅ Git hooks installed successfully[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@hooks_app.command("uninstall")
def hooks_uninstall():
    """🔧 Uninstall Git hooks."""
    try:
        git_manager = GitManager()
        git_manager.uninstall_hooks()
        console.print("[bold green]✅ Git hooks uninstalled successfully[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.callback()
def main_callback():
    """
    🤖 AI-powered Code Review Bot
    
    Review your code with the power of Claude, ChatGPT, or Gemini!
    """
    pass


if __name__ == "__main__":
    app()