"""Git repository management using GitPython."""

import os
from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError, GitCommandError
from git.diff import Diff

from models.types import GitDiff, FileChange, GitStats, FileStatus


class GitManager:
    """Manages Git operations for code review."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize Git manager.
        
        Args:
            repo_path: Path to Git repository. Uses current directory if None.
        """
        self.repo_path = repo_path or Path.cwd()
        self._repo: Optional[Repo] = None
    
    @property
    def repo(self) -> Repo:
        """Get Git repository instance."""
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError:
                raise ValueError(f"Not a git repository: {self.repo_path}")
        return self._repo
    
    def is_git_repository(self) -> bool:
        """Check if current directory is a Git repository."""
        try:
            self.repo
            return True
        except (InvalidGitRepositoryError, ValueError):
            return False
    
    def has_changes(self) -> bool:
        """Check if repository has any changes."""
        try:
            return (
                bool(self.repo.untracked_files) or
                bool(self.repo.index.diff(None)) or
                bool(self.repo.index.diff("HEAD"))
            )
        except Exception:
            return False
    
    def has_staged_changes(self) -> bool:
        """Check if repository has staged changes."""
        try:
            return bool(self.repo.index.diff("HEAD"))
        except Exception:
            return False
    
    def get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            return self.repo.active_branch.name
        except Exception:
            return "unknown"
    
    def get_last_commit_message(self) -> str:
        """Get the last commit message."""
        try:
            return self.repo.head.commit.message.strip()
        except Exception:
            return ""
    
    def get_diff(self, staged: bool = False, commit_hash: Optional[str] = None) -> GitDiff:
        """Get Git diff information.
        
        Args:
            staged: Get staged changes only
            commit_hash: Get diff for specific commit
            
        Returns:
            GitDiff object with change information
        """
        try:
            if commit_hash:
                return self._get_commit_diff(commit_hash)
            elif staged:
                return self._get_staged_diff()
            else:
                return self._get_working_diff()
        except Exception as e:
            raise ValueError(f"Failed to get git diff: {e}")
    
    def _get_commit_diff(self, commit_hash: str) -> GitDiff:
        """Get diff for a specific commit."""
        try:
            commit = self.repo.commit(commit_hash)
            parent = commit.parents[0] if commit.parents else None
            
            if parent:
                diffs = commit.diff(parent)
            else:
                # Initial commit
                diffs = commit.diff(None)
            
            return self._process_diffs(
                diffs, 
                commit_message=commit.message.strip(),
                branch=self.get_current_branch()
            )
        except Exception as e:
            raise ValueError(f"Invalid commit hash: {commit_hash}: {e}")
    
    def _get_staged_diff(self) -> GitDiff:
        """Get staged changes diff."""
        diffs = self.repo.index.diff("HEAD")
        return self._process_diffs(
            diffs,
            commit_message=None,
            branch=self.get_current_branch()
        )
    
    def _get_working_diff(self) -> GitDiff:
        """Get working directory diff."""
        # Get both staged and unstaged changes
        staged_diffs = self.repo.index.diff("HEAD")
        unstaged_diffs = self.repo.index.diff(None)
        
        all_diffs = list(staged_diffs) + list(unstaged_diffs)
        
        return self._process_diffs(
            all_diffs,
            commit_message=None,
            branch=self.get_current_branch()
        )
    
    def _process_diffs(self, diffs, commit_message: Optional[str], branch: str) -> GitDiff:
        """Process Git diffs into GitDiff object."""
        files = []
        total_insertions = 0
        total_deletions = 0
        
        for diff in diffs:
            file_change = self._process_single_diff(diff)
            if file_change:
                files.append(file_change)
                total_insertions += file_change.additions
                total_deletions += file_change.deletions
        
        return GitDiff(
            files=files,
            stats=GitStats(
                files_changed=len(files),
                insertions=total_insertions,
                deletions=total_deletions
            ),
            commit_message=commit_message,
            branch=branch
        )
    
    def _process_single_diff(self, diff: Diff) -> Optional[FileChange]:
        """Process a single diff into FileChange."""
        try:
            # Determine file path
            file_path = diff.b_path or diff.a_path
            if not file_path:
                return None
            
            # Determine change type
            if diff.new_file:
                status = FileStatus.ADDED
            elif diff.deleted_file:
                status = FileStatus.DELETED
            elif diff.renamed_file:
                status = FileStatus.RENAMED
            else:
                status = FileStatus.MODIFIED
            
            # Get patch content
            patch = None
            try:
                if hasattr(diff, 'diff') and diff.diff:
                    patch = diff.diff.decode('utf-8')
            except Exception:
                pass
            
            # Count additions and deletions
            additions = 0
            deletions = 0
            
            if patch:
                for line in patch.split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        additions += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        deletions += 1
            
            return FileChange(
                path=file_path,
                status=status,
                additions=additions,
                deletions=deletions,
                patch=patch
            )
        
        except Exception:
            return None
    
    def format_diff_for_review(self, git_diff: GitDiff) -> str:
        """Format git diff for AI review."""
        formatted_lines = []
        
        for file in git_diff.files:
            formatted_lines.append(f"## {file.path} ({file.status.value})")
            formatted_lines.append(f"**+{file.additions} -{file.deletions}**\n")
            
            if file.patch:
                formatted_lines.append("```diff")
                formatted_lines.append(file.patch)
                formatted_lines.append("```\n")
        
        return '\n'.join(formatted_lines)
    
    def install_hooks(self) -> None:
        """Install Git hooks for automatic reviews."""
        hooks_dir = self.repo_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        
        # Pre-commit hook
        pre_commit_content = '''#!/bin/sh
# Review Bot pre-commit hook
if command -v review-bot >/dev/null 2>&1; then
    CONFIG=$(review-bot config get autoReview.onCommit 2>/dev/null || echo "false")
    if [ "$CONFIG" = "true" ]; then
        echo "Running code review..."
        review-bot run --staged
        if [ $? -ne 0 ]; then
            echo "Code review failed. Commit aborted."
            exit 1
        fi
    fi
fi
'''
        
        # Pre-push hook
        pre_push_content = '''#!/bin/sh
# Review Bot pre-push hook
if command -v review-bot >/dev/null 2>&1; then
    CONFIG=$(review-bot config get autoReview.onPush 2>/dev/null || echo "false")
    if [ "$CONFIG" = "true" ]; then
        echo "Running code review before push..."
        review-bot run
        if [ $? -ne 0 ]; then
            echo "Code review failed. Push aborted."
            exit 1
        fi
    fi
fi
'''
        
        # Write hooks
        pre_commit_path = hooks_dir / "pre-commit"
        pre_push_path = hooks_dir / "pre-push"
        
        pre_commit_path.write_text(pre_commit_content)
        pre_push_path.write_text(pre_push_content)
        
        # Make executable
        pre_commit_path.chmod(0o755)
        pre_push_path.chmod(0o755)
    
    def uninstall_hooks(self) -> None:
        """Uninstall Git hooks."""
        hooks_dir = self.repo_path / ".git" / "hooks"
        
        for hook_name in ["pre-commit", "pre-push"]:
            hook_path = hooks_dir / hook_name
            if hook_path.exists():
                hook_path.unlink()