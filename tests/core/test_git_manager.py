"""Tests for GitManager."""

import pytest
from pathlib import Path
import git
from unittest.mock import patch, Mock

from core.git_manager import GitManager
from models.types import GitDiff, FileChange, GitStats


class TestGitManager:
    """Test GitManager functionality."""
    
    def test_is_git_repository_true(self, temp_git_repo: Path):
        """Test detection of valid git repository."""
        manager = GitManager(repo_path=temp_git_repo)
        assert manager.is_git_repository() is True
    
    def test_is_git_repository_false(self, temp_dir: Path):
        """Test detection of non-git directory."""
        manager = GitManager(repo_path=temp_dir)
        assert manager.is_git_repository() is False
    
    def test_get_current_branch(self, temp_git_repo: Path):
        """Test getting current branch name."""
        manager = GitManager(repo_path=temp_git_repo)
        branch = manager.get_current_branch()
        
        # Should be 'main' or 'master' for new repos
        assert branch in ['main', 'master']
    
    def test_has_changes_with_no_changes(self, temp_git_repo: Path):
        """Test has_changes with clean working directory."""
        manager = GitManager(repo_path=temp_git_repo)
        assert manager.has_changes() is False
    
    def test_has_changes_with_unstaged_changes(self, temp_git_repo: Path):
        """Test has_changes with unstaged changes."""
        # Modify existing file
        test_file = temp_git_repo / "test.py"
        test_file.write_text("# Modified test file\nprint('hello modified world')\n")
        
        manager = GitManager(repo_path=temp_git_repo)
        assert manager.has_changes() is True
    
    def test_has_changes_with_staged_changes(self, temp_git_repo: Path):
        """Test has_changes with staged changes."""
        # Create and stage new file
        new_file = temp_git_repo / "new_file.py"
        new_file.write_text("# New file\nprint('new')\n")
        
        repo = git.Repo(temp_git_repo)
        repo.index.add([str(new_file)])
        
        manager = GitManager(repo_path=temp_git_repo)
        assert manager.has_changes() is True
    
    def test_get_staged_files(self, temp_git_repo: Path):
        """Test getting staged files."""
        # Create and stage new files
        file1 = temp_git_repo / "staged1.py"
        file2 = temp_git_repo / "staged2.py"
        file1.write_text("print('staged1')")
        file2.write_text("print('staged2')")
        
        repo = git.Repo(temp_git_repo)
        repo.index.add([str(file1), str(file2)])
        
        manager = GitManager(repo_path=temp_git_repo)
        staged_files = manager.get_staged_files()
        
        assert len(staged_files) == 2
        assert "staged1.py" in staged_files
        assert "staged2.py" in staged_files
    
    def test_get_modified_files(self, temp_git_repo: Path):
        """Test getting modified files."""
        # Modify existing file
        test_file = temp_git_repo / "test.py"
        test_file.write_text("# Modified content\nprint('modified')\n")
        
        # Create new untracked file
        new_file = temp_git_repo / "untracked.py"
        new_file.write_text("print('untracked')")
        
        manager = GitManager(repo_path=temp_git_repo)
        modified_files = manager.get_modified_files()
        
        assert "test.py" in modified_files
        assert "untracked.py" in modified_files
    
    def test_get_working_diff(self, temp_git_repo: Path):
        """Test getting working directory diff."""
        # Modify existing file
        test_file = temp_git_repo / "test.py"
        original_content = test_file.read_text()
        new_content = "# Modified test file\nprint('hello modified world')\n"
        test_file.write_text(new_content)
        
        manager = GitManager(repo_path=temp_git_repo)
        diff = manager.get_diff()
        
        assert isinstance(diff, GitDiff)
        assert diff.branch in ['main', 'master']
        assert diff.stats.files_changed >= 1
        assert len(diff.files) >= 1
        
        # Check that the modified file is in the diff
        modified_file = next((f for f in diff.files if f.path == "test.py"), None)
        assert modified_file is not None
        assert modified_file.status in ['modified', 'M']
        assert "Modified test file" in modified_file.content
    
    def test_get_staged_diff(self, temp_git_repo: Path):
        """Test getting staged changes diff."""
        # Create and stage new file
        new_file = temp_git_repo / "staged_file.py"
        new_file.write_text("# Staged file\nprint('staged content')\n")
        
        repo = git.Repo(temp_git_repo)
        repo.index.add([str(new_file)])
        
        manager = GitManager(repo_path=temp_git_repo)
        diff = manager.get_diff(staged=True)
        
        assert isinstance(diff, GitDiff)
        assert diff.stats.files_changed >= 1
        assert len(diff.files) >= 1
        
        # Check that the staged file is in the diff
        staged_file = next((f for f in diff.files if f.path == "staged_file.py"), None)
        assert staged_file is not None
        assert staged_file.status in ['added', 'A']
        assert "staged content" in staged_file.content
    
    def test_get_commit_diff(self, temp_git_repo: Path):
        """Test getting diff for specific commit."""
        # Create a new commit
        new_file = temp_git_repo / "commit_file.py"
        new_file.write_text("# Commit file\nprint('commit content')\n")
        
        repo = git.Repo(temp_git_repo)
        repo.index.add([str(new_file)])
        commit = repo.index.commit("Add commit file")
        
        manager = GitManager(repo_path=temp_git_repo)
        diff = manager.get_diff(commit_hash=commit.hexsha)
        
        assert isinstance(diff, GitDiff)
        assert diff.commit_hash == commit.hexsha
        assert diff.commit_message == "Add commit file"
        assert diff.author.startswith("Test User")
        assert diff.stats.files_changed >= 1
        
        # Check that the committed file is in the diff
        commit_file = next((f for f in diff.files if f.path == "commit_file.py"), None)
        assert commit_file is not None
        assert commit_file.status in ['added', 'A']
    
    def test_parse_diff_stats(self, temp_git_repo: Path):
        """Test parsing diff statistics."""
        manager = GitManager(repo_path=temp_git_repo)
        
        # Create mock diff with stats
        mock_stats = "2 files changed, 10 insertions(+), 5 deletions(-)"
        stats = manager._parse_diff_stats(mock_stats)
        
        assert isinstance(stats, GitStats)
        assert stats.files_changed == 2
        assert stats.insertions == 10
        assert stats.deletions == 5
    
    def test_parse_diff_stats_single_file(self, temp_git_repo: Path):
        """Test parsing diff stats for single file."""
        manager = GitManager(repo_path=temp_git_repo)
        
        mock_stats = "1 file changed, 3 insertions(+)"
        stats = manager._parse_diff_stats(mock_stats)
        
        assert stats.files_changed == 1
        assert stats.insertions == 3
        assert stats.deletions == 0
    
    def test_parse_diff_stats_deletions_only(self, temp_git_repo: Path):
        """Test parsing diff stats with only deletions."""
        manager = GitManager(repo_path=temp_git_repo)
        
        mock_stats = "1 file changed, 7 deletions(-)"
        stats = manager._parse_diff_stats(mock_stats)
        
        assert stats.files_changed == 1
        assert stats.insertions == 0
        assert stats.deletions == 7
    
    def test_filter_files_by_extensions(self, temp_git_repo: Path):
        """Test filtering files by extensions."""
        # Create files with different extensions
        py_file = temp_git_repo / "script.py"
        js_file = temp_git_repo / "app.js"
        txt_file = temp_git_repo / "readme.txt"
        
        for f in [py_file, js_file, txt_file]:
            f.write_text("content")
        
        repo = git.Repo(temp_git_repo)
        repo.index.add([str(py_file), str(js_file), str(txt_file)])
        
        manager = GitManager(repo_path=temp_git_repo)
        diff = manager.get_diff(staged=True, file_filters=["*.py", "*.js"])
        
        file_paths = [f.path for f in diff.files]
        assert "script.py" in file_paths
        assert "app.js" in file_paths
        assert "readme.txt" not in file_paths
    
    def test_install_hooks(self, temp_git_repo: Path):
        """Test installing git hooks."""
        manager = GitManager(repo_path=temp_git_repo)
        
        with patch.object(manager, '_create_hook_script') as mock_create:
            manager.install_hooks()
            
            # Should create pre-commit and pre-push hooks
            assert mock_create.call_count == 2
            
            # Check hook files were created
            hooks_dir = temp_git_repo / ".git" / "hooks"
            pre_commit_hook = hooks_dir / "pre-commit"
            pre_push_hook = hooks_dir / "pre-push"
            
            # Files might not exist in test, but method should be called
            mock_create.assert_any_call(pre_commit_hook, "pre-commit")
            mock_create.assert_any_call(pre_push_hook, "pre-push")
    
    def test_uninstall_hooks(self, temp_git_repo: Path):
        """Test uninstalling git hooks."""
        # Create hook files
        hooks_dir = temp_git_repo / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        
        pre_commit_hook = hooks_dir / "pre-commit"
        pre_push_hook = hooks_dir / "pre-push"
        
        pre_commit_hook.write_text("#!/bin/sh\n# review-bot hook\necho 'test'")
        pre_push_hook.write_text("#!/bin/sh\n# review-bot hook\necho 'test'")
        
        manager = GitManager(repo_path=temp_git_repo)
        manager.uninstall_hooks()
        
        # Hooks should be removed
        assert not pre_commit_hook.exists()
        assert not pre_push_hook.exists()
    
    def test_get_diff_no_repository(self, temp_dir: Path):
        """Test get_diff on non-git directory."""
        manager = GitManager(repo_path=temp_dir)
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_diff()
        
        assert "Not a git repository" in str(exc_info.value)
    
    def test_get_diff_invalid_commit(self, temp_git_repo: Path):
        """Test get_diff with invalid commit hash."""
        manager = GitManager(repo_path=temp_git_repo)
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_diff(commit_hash="invalid-hash")
        
        assert "Invalid commit hash" in str(exc_info.value)
    
    def test_get_user_info(self, temp_git_repo: Path):
        """Test getting git user information."""
        manager = GitManager(repo_path=temp_git_repo)
        user_info = manager._get_user_info()
        
        assert "name" in user_info
        assert "email" in user_info
        assert user_info["name"] == "Test User"
        assert user_info["email"] == "test@example.com"
    
    def test_empty_diff(self, temp_git_repo: Path):
        """Test handling of empty diff."""
        manager = GitManager(repo_path=temp_git_repo)
        
        # Clean repository should have no working changes
        diff = manager.get_diff()
        
        assert isinstance(diff, GitDiff)
        assert diff.stats.files_changed == 0
        assert diff.stats.insertions == 0
        assert diff.stats.deletions == 0
        assert len(diff.files) == 0