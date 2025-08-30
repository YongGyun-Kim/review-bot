import simpleGit, { SimpleGit, DiffResult } from 'simple-git';
import { GitDiff, FileChange } from '../types';

export class GitManager {
  private git: SimpleGit;

  constructor(workingDirectory?: string) {
    this.git = simpleGit(workingDirectory);
  }

  async getDiff(staged = false, commitHash?: string): Promise<GitDiff> {
    try {
      let diffResult: DiffResult;
      
      if (commitHash) {
        diffResult = await this.git.diff([`${commitHash}^`, commitHash]);
      } else if (staged) {
        diffResult = await this.git.diff(['--staged']);
      } else {
        diffResult = await this.git.diff(['HEAD']);
      }

      const status = await this.git.status();
      const branch = await this.getCurrentBranch();
      const commitMessage = await this.getLastCommitMessage();

      const files: FileChange[] = [];
      let totalInsertions = 0;
      let totalDeletions = 0;

      for (const file of status.files) {
        const fileDiff = await this.git.diff([staged ? '--staged' : 'HEAD', '--', file.path]);
        const stats = this.parseFileStats(fileDiff);
        
        files.push({
          path: file.path,
          status: this.mapGitStatus(file.index || file.working_dir),
          additions: stats.additions,
          deletions: stats.deletions,
          patch: fileDiff
        });

        totalInsertions += stats.additions;
        totalDeletions += stats.deletions;
      }

      return {
        files,
        stats: {
          filesChanged: files.length,
          insertions: totalInsertions,
          deletions: totalDeletions
        },
        commitMessage,
        branch
      };
    } catch (error) {
      throw new Error(`Git diff failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async getStagedDiff(): Promise<GitDiff> {
    return this.getDiff(true);
  }

  async getWorkingDiff(): Promise<GitDiff> {
    return this.getDiff(false);
  }

  async getCommitDiff(commitHash: string): Promise<GitDiff> {
    return this.getDiff(false, commitHash);
  }

  async getCurrentBranch(): Promise<string> {
    try {
      const branch = await this.git.branch();
      return branch.current || 'unknown';
    } catch (error) {
      console.warn('Failed to get current branch:', error);
      return 'unknown';
    }
  }

  async getLastCommitMessage(): Promise<string> {
    try {
      const log = await this.git.log({ maxCount: 1 });
      return log.latest?.message || '';
    } catch (error) {
      console.warn('Failed to get last commit message:', error);
      return '';
    }
  }

  async isGitRepository(): Promise<boolean> {
    try {
      await this.git.status();
      return true;
    } catch {
      return false;
    }
  }

  async hasChanges(): Promise<boolean> {
    try {
      const status = await this.git.status();
      return status.files.length > 0;
    } catch {
      return false;
    }
  }

  async hasStagedChanges(): Promise<boolean> {
    try {
      const status = await this.git.status();
      return status.staged.length > 0;
    } catch {
      return false;
    }
  }

  async installHooks(): Promise<void> {
    try {
      const hooksPath = '.git/hooks';
      const preCommitHook = `#!/bin/sh
# Review Bot pre-commit hook
if command -v review-bot >/dev/null 2>&1; then
  if review-bot config get autoReview.onCommit 2>/dev/null | grep -q "true"; then
    echo "Running code review..."
    review-bot run --staged
  fi
fi
`;

      const prePushHook = `#!/bin/sh
# Review Bot pre-push hook
if command -v review-bot >/dev/null 2>&1; then
  if review-bot config get autoReview.onPush 2>/dev/null | grep -q "true"; then
    echo "Running code review before push..."
    review-bot run
  fi
fi
`;

      const fs = await import('fs/promises');
      
      await fs.writeFile(`${hooksPath}/pre-commit`, preCommitHook, { mode: 0o755 });
      await fs.writeFile(`${hooksPath}/pre-push`, prePushHook, { mode: 0o755 });
      
      console.log('Git hooks installed successfully');
    } catch (error) {
      throw new Error(`Failed to install git hooks: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async uninstallHooks(): Promise<void> {
    try {
      const fs = await import('fs/promises');
      const hooksPath = '.git/hooks';
      
      try {
        await fs.unlink(`${hooksPath}/pre-commit`);
      } catch {}
      
      try {
        await fs.unlink(`${hooksPath}/pre-push`);
      } catch {}
      
      console.log('Git hooks uninstalled successfully');
    } catch (error) {
      throw new Error(`Failed to uninstall git hooks: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private parseFileStats(diff: string): { additions: number; deletions: number } {
    let additions = 0;
    let deletions = 0;

    const lines = diff.split('\n');
    for (const line of lines) {
      if (line.startsWith('+') && !line.startsWith('+++')) {
        additions++;
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        deletions++;
      }
    }

    return { additions, deletions };
  }

  private mapGitStatus(status: string): 'added' | 'modified' | 'deleted' | 'renamed' {
    switch (status) {
      case 'A':
        return 'added';
      case 'M':
        return 'modified';
      case 'D':
        return 'deleted';
      case 'R':
        return 'renamed';
      default:
        return 'modified';
    }
  }

  async formatDiffForReview(): Promise<string> {
    const diff = await this.getDiff();
    const formattedFiles: string[] = [];

    for (const file of diff.files) {
      formattedFiles.push(`## ${file.path} (${file.status})`);
      formattedFiles.push(`**+${file.additions} -${file.deletions}**\n`);
      
      if (file.patch) {
        formattedFiles.push('```diff');
        formattedFiles.push(file.patch);
        formattedFiles.push('```\n');
      }
    }

    return formattedFiles.join('\n');
  }
}