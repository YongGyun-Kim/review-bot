"""Review management and orchestration."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import uuid4

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from models.types import (
    ReviewResult, ReviewConfig, GitDiff, Issue, Suggestion, 
    TodoItem, ProviderConfig
)
from providers import create_provider
from .git_manager import GitManager
from .prompt_manager import PromptManager
from .config_manager import ConfigManager


class ReviewManager:
    """Manages code review workflow and results."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize review manager.
        
        Args:
            output_dir: Directory for review outputs
        """
        self.output_dir = output_dir or Path("reviews")
        self.output_dir.mkdir(exist_ok=True)
        
        self.git_manager = GitManager()
        self.prompt_manager = PromptManager()
        self.config_manager = ConfigManager()
        
        self.console = Console()
    
    async def run_review(
        self,
        staged: bool = False,
        commit_hash: Optional[str] = None,
        prompt_template: Optional[str] = None,
        output_format: str = "markdown",
        interactive: bool = False
    ) -> ReviewResult:
        """Run a code review.
        
        Args:
            staged: Review only staged changes
            commit_hash: Review specific commit
            prompt_template: Template to use
            output_format: Output format (markdown, json, html)
            interactive: Run in interactive mode
            
        Returns:
            ReviewResult object
        """
        # Load configuration
        config = await self.config_manager.load_config()
        
        # Validate configuration
        valid, errors = self.config_manager.validate_config(config)
        if not valid:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")
        
        # Check Git repository
        if not self.git_manager.is_git_repository():
            raise ValueError("Not a Git repository")
        
        # Get Git diff
        with self.console.status("[bold green]Getting Git diff...") as status:
            git_diff = self._get_git_diff(staged, commit_hash)
            
            if not git_diff.files:
                raise ValueError("No changes found to review")
            
            status.update(f"[bold blue]Found {git_diff.stats.files_changed} files with changes")
        
        # Prepare code diff for review
        code_diff = self.git_manager.format_diff_for_review(git_diff)
        
        # Filter files based on patterns
        filtered_diff = self._filter_files(git_diff, config)
        
        if not filtered_diff.files:
            raise ValueError("No files to review after filtering")
        
        # Load prompt template
        template_name = prompt_template or config.prompt_template
        prompt = await self.prompt_manager.load_prompt(template_name)
        
        # Populate prompt with data
        populated_prompt = self.prompt_manager.populate_prompt(prompt, {
            'git_diff': filtered_diff,
            'code_diff': code_diff,
            'timestamp': datetime.now(),
            'branch': self.git_manager.get_current_branch(),
        })
        
        # Create AI provider
        provider_config = ProviderConfig(
            api_key=config.api_key,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        provider = create_provider(config.provider.value, provider_config)
        
        # Run review with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Running review with {config.provider.value}...",
                total=None
            )
            
            try:
                result = await provider.review(code_diff, populated_prompt)
                progress.update(task, completed=True)
            except Exception as e:
                progress.stop()
                raise ValueError(f"Review failed: {e}")
        
        # Save review result
        await self._save_review_result(result, output_format)
        
        # Create TODO items if there are suggestions
        if result.suggestions:
            await self._create_todo_items(result)
        
        # Display summary
        self._display_review_summary(result)
        
        return result
    
    def _get_git_diff(self, staged: bool, commit_hash: Optional[str]) -> GitDiff:
        """Get Git diff based on parameters.
        
        Args:
            staged: Get staged changes
            commit_hash: Get specific commit diff
            
        Returns:
            GitDiff object
        """
        if commit_hash:
            return self.git_manager.get_diff(commit_hash=commit_hash)
        elif staged:
            return self.git_manager.get_diff(staged=True)
        else:
            return self.git_manager.get_diff()
    
    def _filter_files(self, git_diff: GitDiff, config: ReviewConfig) -> GitDiff:
        """Filter files based on include/exclude patterns.
        
        Args:
            git_diff: Original Git diff
            config: Review configuration
            
        Returns:
            Filtered GitDiff
        """
        import fnmatch
        
        filtered_files = []
        
        for file in git_diff.files:
            # Check exclude patterns
            excluded = any(
                fnmatch.fnmatch(file.path, pattern)
                for pattern in config.exclude_patterns
            )
            
            if excluded:
                continue
            
            # Check include patterns
            included = any(
                fnmatch.fnmatch(file.path, pattern)
                for pattern in config.include_patterns
            )
            
            if included:
                filtered_files.append(file)
        
        # Limit number of files
        if len(filtered_files) > config.max_files_per_review:
            filtered_files = filtered_files[:config.max_files_per_review]
            self.console.print(
                f"[yellow]Warning: Limited to {config.max_files_per_review} files[/yellow]"
            )
        
        # Create new GitDiff with filtered files
        filtered_diff = GitDiff(
            files=filtered_files,
            stats=git_diff.stats,
            commit_message=git_diff.commit_message,
            branch=git_diff.branch
        )
        
        return filtered_diff
    
    async def _save_review_result(self, result: ReviewResult, format: str) -> Path:
        """Save review result to file.
        
        Args:
            result: Review result to save
            format: Output format
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = f"review_{timestamp}.json"
            filepath = self.output_dir / filename
            
            # Convert to JSON-serializable format
            data = self._serialize_result(result)
            filepath.write_text(json.dumps(data, indent=2), encoding='utf-8')
            
        elif format == "html":
            filename = f"review_{timestamp}.html"
            filepath = self.output_dir / filename
            html_content = self._format_as_html(result)
            filepath.write_text(html_content, encoding='utf-8')
            
        else:  # markdown (default)
            filename = f"review_{timestamp}.md"
            filepath = self.output_dir / filename
            markdown_content = self._format_as_markdown(result)
            filepath.write_text(markdown_content, encoding='utf-8')
        
        self.console.print(f"[green]Review saved to: {filepath}[/green]")
        return filepath
    
    def _serialize_result(self, result: ReviewResult) -> Dict[str, Any]:
        """Serialize ReviewResult to JSON-compatible format.
        
        Args:
            result: Review result
            
        Returns:
            Serializable dictionary
        """
        return {
            'provider': result.provider,
            'model': result.model,
            'timestamp': result.timestamp.isoformat(),
            'summary': result.summary,
            'strengths': result.strengths,
            'issues': [
                {
                    'severity': issue.severity.value,
                    'type': issue.type,
                    'file': issue.file,
                    'line': issue.line,
                    'description': issue.description,
                    'suggestion': issue.suggestion,
                    'code_example': issue.code_example
                }
                for issue in result.issues
            ],
            'suggestions': [
                {
                    'id': suggestion.id,
                    'title': suggestion.title,
                    'description': suggestion.description,
                    'files': suggestion.files,
                    'priority': suggestion.priority.value,
                    'completed': suggestion.completed,
                    'example': suggestion.example
                }
                for suggestion in result.suggestions
            ],
            'tokens': {
                'input': result.tokens.input_tokens if result.tokens else 0,
                'output': result.tokens.output_tokens if result.tokens else 0,
                'total': result.tokens.total_tokens if result.tokens else 0,
            } if result.tokens else None,
            'estimated_cost': result.estimated_cost
        }
    
    def _format_as_markdown(self, result: ReviewResult) -> str:
        """Format review result as markdown.
        
        Args:
            result: Review result
            
        Returns:
            Markdown string
        """
        lines = []
        
        # Header
        lines.append(f"# Code Review - {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"**Provider:** {result.provider}")
        lines.append(f"**Model:** {result.model}")
        
        if result.tokens:
            lines.append(f"**Tokens:** {result.tokens.total_tokens:,} "
                        f"(input: {result.tokens.input_tokens:,}, "
                        f"output: {result.tokens.output_tokens:,})")
        
        if result.estimated_cost is not None:
            lines.append(f"**Estimated Cost:** ${result.estimated_cost:.4f}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Summary
        if result.summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(result.summary)
            lines.append("")
        
        # Strengths
        if result.strengths:
            lines.append("## Strengths")
            lines.append("")
            for strength in result.strengths:
                lines.append(f"- {strength}")
            lines.append("")
        
        # Issues
        if result.issues:
            lines.append("## Issues Found")
            lines.append("")
            
            # Group by severity
            critical = [i for i in result.issues if i.severity.value == 'critical']
            major = [i for i in result.issues if i.severity.value == 'major']
            minor = [i for i in result.issues if i.severity.value == 'minor']
            
            if critical:
                lines.append("### 🔴 Critical Issues")
                lines.append("")
                for issue in critical:
                    lines.extend(self._format_issue_markdown(issue))
            
            if major:
                lines.append("### 🟡 Major Issues")
                lines.append("")
                for issue in major:
                    lines.extend(self._format_issue_markdown(issue))
            
            if minor:
                lines.append("### 🟢 Minor Issues")
                lines.append("")
                for issue in minor:
                    lines.extend(self._format_issue_markdown(issue))
        
        # Suggestions
        if result.suggestions:
            lines.append("## Improvement Suggestions")
            lines.append("")
            
            for i, suggestion in enumerate(result.suggestions, 1):
                lines.append(f"### {i}. {suggestion.title}")
                lines.append("")
                lines.append(f"**Priority:** {suggestion.priority.value}")
                lines.append("")
                lines.append(suggestion.description)
                
                if suggestion.files:
                    lines.append("")
                    lines.append(f"**Files:** {', '.join(suggestion.files)}")
                
                if suggestion.example:
                    lines.append("")
                    lines.append("**Example:**")
                    lines.append("```")
                    lines.append(suggestion.example)
                    lines.append("```")
                
                lines.append("")
        
        return '\n'.join(lines)
    
    def _format_issue_markdown(self, issue: Issue) -> List[str]:
        """Format a single issue as markdown lines.
        
        Args:
            issue: Issue to format
            
        Returns:
            List of markdown lines
        """
        lines = []
        
        header = f"**{issue.type}**"
        if issue.file:
            header += f" - `{issue.file}"
            if issue.line:
                header += f":{issue.line}"
            header += "`"
        
        lines.append(header)
        lines.append("")
        lines.append(issue.description)
        
        if issue.suggestion:
            lines.append("")
            lines.append(f"*Suggestion:* {issue.suggestion}")
        
        if issue.code_example:
            lines.append("")
            lines.append("```")
            lines.append(issue.code_example)
            lines.append("```")
        
        lines.append("")
        return lines
    
    def _format_as_html(self, result: ReviewResult) -> str:
        """Format review result as HTML.
        
        Args:
            result: Review result
            
        Returns:
            HTML string
        """
        # Simple HTML template
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Code Review - {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
        h3 {{ color: #888; }}
        .metadata {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .critical {{ color: #d32f2f; }}
        .major {{ color: #f57c00; }}
        .minor {{ color: #388e3c; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        code {{ background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>Code Review - {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</h1>
    <div class="metadata">
        <p><strong>Provider:</strong> {result.provider}</p>
        <p><strong>Model:</strong> {result.model}</p>
        {'<p><strong>Tokens:</strong> ' + str(result.tokens.total_tokens) + '</p>' if result.tokens else ''}
        {'<p><strong>Estimated Cost:</strong> $' + f'{result.estimated_cost:.4f}' + '</p>' if result.estimated_cost else ''}
    </div>
    
    {self._html_section('Summary', result.summary) if result.summary else ''}
    {self._html_list_section('Strengths', result.strengths) if result.strengths else ''}
    {self._html_issues_section(result.issues) if result.issues else ''}
    {self._html_suggestions_section(result.suggestions) if result.suggestions else ''}
</body>
</html>
"""
        return html
    
    def _html_section(self, title: str, content: str) -> str:
        """Create HTML section."""
        return f"<h2>{title}</h2><p>{content}</p>"
    
    def _html_list_section(self, title: str, items: List[str]) -> str:
        """Create HTML list section."""
        items_html = ''.join(f"<li>{item}</li>" for item in items)
        return f"<h2>{title}</h2><ul>{items_html}</ul>"
    
    def _html_issues_section(self, issues: List[Issue]) -> str:
        """Create HTML issues section."""
        html = "<h2>Issues Found</h2>"
        
        for severity in ['critical', 'major', 'minor']:
            severity_issues = [i for i in issues if i.severity.value == severity]
            if severity_issues:
                html += f'<h3 class="{severity}">{severity.title()} Issues</h3>'
                for issue in severity_issues:
                    html += f"<div><strong>{issue.type}</strong>"
                    if issue.file:
                        html += f" - <code>{issue.file}</code>"
                    html += f"<p>{issue.description}</p>"
                    if issue.suggestion:
                        html += f"<p><em>Suggestion:</em> {issue.suggestion}</p>"
                    html += "</div>"
        
        return html
    
    def _html_suggestions_section(self, suggestions: List[Suggestion]) -> str:
        """Create HTML suggestions section."""
        html = "<h2>Improvement Suggestions</h2>"
        
        for i, suggestion in enumerate(suggestions, 1):
            html += f"<h3>{i}. {suggestion.title}</h3>"
            html += f"<p><strong>Priority:</strong> {suggestion.priority.value}</p>"
            html += f"<p>{suggestion.description}</p>"
            
            if suggestion.example:
                html += f"<pre><code>{suggestion.example}</code></pre>"
        
        return html
    
    async def _create_todo_items(self, result: ReviewResult) -> None:
        """Create TODO items from review suggestions.
        
        Args:
            result: Review result with suggestions
        """
        todo_dir = self.output_dir / "todo"
        todo_dir.mkdir(exist_ok=True)
        
        todos = []
        review_id = str(uuid4())[:8]
        
        for suggestion in result.suggestions:
            todo = TodoItem(
                id=suggestion.id,
                title=suggestion.title,
                description=suggestion.description,
                files=suggestion.files,
                priority=suggestion.priority,
                completed=False,
                example=suggestion.example,
                created_at=datetime.now(),
                review_id=review_id
            )
            todos.append(todo)
        
        # Save TODOs to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        todo_file = todo_dir / f"todo_{timestamp}.json"
        
        todo_data = [
            {
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
            for todo in todos
        ]
        
        todo_file.write_text(json.dumps(todo_data, indent=2), encoding='utf-8')
        
        self.console.print(f"[green]Created {len(todos)} TODO items in {todo_file}[/green]")
    
    def _display_review_summary(self, result: ReviewResult) -> None:
        """Display review summary to console.
        
        Args:
            result: Review result
        """
        self.console.print("\n[bold green]✅ Review Complete![/bold green]\n")
        
        # Provider info
        self.console.print(f"[cyan]Provider:[/cyan] {result.provider} ({result.model})")
        
        # Token usage
        if result.tokens:
            self.console.print(
                f"[cyan]Tokens:[/cyan] {result.tokens.total_tokens:,} "
                f"(input: {result.tokens.input_tokens:,}, output: {result.tokens.output_tokens:,})"
            )
        
        # Cost
        if result.estimated_cost is not None:
            self.console.print(f"[cyan]Estimated Cost:[/cyan] ${result.estimated_cost:.4f}")
        
        # Issue counts
        critical_count = sum(1 for i in result.issues if i.severity.value == 'critical')
        major_count = sum(1 for i in result.issues if i.severity.value == 'major')
        minor_count = sum(1 for i in result.issues if i.severity.value == 'minor')
        
        self.console.print(f"\n[cyan]Issues Found:[/cyan]")
        if critical_count:
            self.console.print(f"  🔴 Critical: {critical_count}")
        if major_count:
            self.console.print(f"  🟡 Major: {major_count}")
        if minor_count:
            self.console.print(f"  🟢 Minor: {minor_count}")
        
        if not result.issues:
            self.console.print("  [green]No issues found![/green]")
        
        # Suggestions
        if result.suggestions:
            self.console.print(f"\n[cyan]Suggestions:[/cyan] {len(result.suggestions)} improvement(s) identified")
        
        # Summary snippet
        if result.summary:
            summary_lines = result.summary.split('\n')
            snippet = summary_lines[0][:100] + "..." if len(summary_lines[0]) > 100 else summary_lines[0]
            self.console.print(f"\n[dim]{snippet}[/dim]")