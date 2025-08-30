#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import dotenv from 'dotenv';
import ora from 'ora';
import { ReviewManager } from '../core/review.manager';
import { ConfigManager } from '../core/config.manager';
import { TodoManager } from '../core/todo.manager';
import { GitManager } from '../core/git.manager';
import { PromptManager } from '../core/prompt.manager';
import { AVAILABLE_PROVIDERS, DEFAULT_MODELS } from '../providers';

dotenv.config();

const program = new Command();

program
  .name('review-bot')
  .description('AI-powered code review bot for Git repositories')
  .version('1.0.0');

program
  .command('run')
  .description('Run code review on current changes')
  .option('-s, --staged', 'Review only staged changes')
  .option('-c, --commit <hash>', 'Review specific commit')
  .option('-p, --prompt <template>', 'Use specific prompt template')
  .option('-f, --format <format>', 'Output format (markdown|json)', 'markdown')
  .action(async (options) => {
    const spinner = ora('Running code review...').start();
    
    try {
      const reviewManager = new ReviewManager();
      const result = await reviewManager.runReview({
        staged: options.staged,
        commitHash: options.commit,
        promptTemplate: options.prompt,
        outputFormat: options.format
      });

      spinner.succeed('Code review completed');
      
      console.log(chalk.green('\n✅ Review Summary:'));
      console.log(`Provider: ${result.provider} (${result.model})`);
      console.log(`Issues found: ${result.issues.length}`);
      console.log(`Suggestions: ${result.suggestions.length}`);
      
      if (result.tokens) {
        console.log(`Tokens used: ${result.tokens.total}`);
      }
      
      if (result.estimatedCost) {
        console.log(`Estimated cost: $${result.estimatedCost.toFixed(4)}`);
      }

      const criticalIssues = result.issues.filter(i => i.severity === 'critical');
      if (criticalIssues.length > 0) {
        console.log(chalk.red(`\n⚠️  ${criticalIssues.length} critical issues found that must be addressed!`));
      }

    } catch (error) {
      spinner.fail('Code review failed');
      console.error(chalk.red(error instanceof Error ? error.message : 'Unknown error'));
      process.exit(1);
    }
  });

const configCmd = program.command('config').description('Manage configuration');

configCmd
  .command('init')
  .description('Initialize configuration file')
  .action(async () => {
    try {
      const configManager = new ConfigManager();
      await configManager.initConfig();
      console.log(chalk.green('✅ Configuration initialized'));
    } catch (error) {
      console.error(chalk.red(`Failed to initialize config: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

configCmd
  .command('set <key> <value>')
  .description('Set configuration value')
  .option('-g, --global', 'Set global configuration')
  .action(async (key, value, options) => {
    try {
      const configManager = new ConfigManager();
      const config = { [key]: value };
      await configManager.saveConfig(config, options.global);
      console.log(chalk.green(`✅ Configuration updated: ${key} = ${value}`));
    } catch (error) {
      console.error(chalk.red(`Failed to set config: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

configCmd
  .command('get [key]')
  .description('Get configuration value(s)')
  .action(async (key) => {
    try {
      const configManager = new ConfigManager();
      const config = await configManager.loadConfig();
      
      if (key) {
        const value = (config as any)[key];
        console.log(value !== undefined ? value : chalk.gray('(not set)'));
      } else {
        console.log(JSON.stringify(config, null, 2));
      }
    } catch (error) {
      console.error(chalk.red(`Failed to get config: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

const todoCmd = program.command('todo').description('Manage TODO items');

todoCmd
  .command('list')
  .description('List TODO items')
  .option('-a, --all', 'Show all todos including completed')
  .option('-c, --completed', 'Show only completed todos')
  .option('-p, --priority <priority>', 'Filter by priority (high|medium|low)')
  .action(async (options) => {
    try {
      const todoManager = new TodoManager();
      await todoManager.displayTodos({
        showCompleted: options.all,
        filter: options.completed ? 'completed' : options.all ? 'all' : 'active',
        priority: options.priority
      });
    } catch (error) {
      console.error(chalk.red(`Failed to list todos: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

todoCmd
  .command('complete <id>')
  .description('Mark TODO item as completed')
  .action(async (id) => {
    try {
      const todoManager = new TodoManager();
      await todoManager.markTodoCompleted(id);
    } catch (error) {
      console.error(chalk.red(`Failed to complete todo: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

todoCmd
  .command('activate <id>')
  .description('Mark TODO item as active')
  .action(async (id) => {
    try {
      const todoManager = new TodoManager();
      await todoManager.markTodoActive(id);
    } catch (error) {
      console.error(chalk.red(`Failed to activate todo: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

todoCmd
  .command('delete <id>')
  .description('Delete TODO item')
  .action(async (id) => {
    try {
      const todoManager = new TodoManager();
      await todoManager.deleteTodo(id);
    } catch (error) {
      console.error(chalk.red(`Failed to delete todo: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

todoCmd
  .command('export')
  .description('Export TODO items')
  .option('-f, --format <format>', 'Export format (json|csv|markdown)', 'json')
  .option('-o, --output <path>', 'Output file path')
  .action(async (options) => {
    try {
      const todoManager = new TodoManager();
      await todoManager.exportTodos(options.format, options.output);
    } catch (error) {
      console.error(chalk.red(`Failed to export todos: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

const promptCmd = program.command('prompt').description('Manage prompt templates');

promptCmd
  .command('list')
  .description('List available prompt templates')
  .action(async () => {
    try {
      const promptManager = new PromptManager();
      const prompts = await promptManager.getAvailablePrompts();
      
      if (prompts.length === 0) {
        console.log(chalk.gray('No prompt templates found'));
        return;
      }

      console.log(chalk.bold('\n📝 Available Prompt Templates:\n'));
      prompts.forEach(prompt => {
        console.log(`${chalk.cyan(prompt.name)}: ${prompt.description}`);
        if (prompt.variables.length > 0) {
          console.log(chalk.gray(`  Variables: ${prompt.variables.join(', ')}`));
        }
        console.log();
      });
    } catch (error) {
      console.error(chalk.red(`Failed to list prompts: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

const hooksCmd = program.command('hooks').description('Manage Git hooks');

hooksCmd
  .command('install')
  .description('Install Git hooks')
  .action(async () => {
    try {
      const gitManager = new GitManager();
      await gitManager.installHooks();
      console.log(chalk.green('✅ Git hooks installed'));
    } catch (error) {
      console.error(chalk.red(`Failed to install hooks: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

hooksCmd
  .command('uninstall')
  .description('Uninstall Git hooks')
  .action(async () => {
    try {
      const gitManager = new GitManager();
      await gitManager.uninstallHooks();
      console.log(chalk.green('✅ Git hooks uninstalled'));
    } catch (error) {
      console.error(chalk.red(`Failed to uninstall hooks: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

program
  .command('providers')
  .description('List available AI providers and models')
  .action(() => {
    console.log(chalk.bold('\n🤖 Available AI Providers:\n'));
    
    AVAILABLE_PROVIDERS.forEach(provider => {
      console.log(`${chalk.cyan(provider)}: ${DEFAULT_MODELS[provider as keyof typeof DEFAULT_MODELS]}`);
    });

    console.log(chalk.gray('\nSet your API keys using environment variables:'));
    console.log(chalk.gray('- Claude: ANTHROPIC_API_KEY'));
    console.log(chalk.gray('- ChatGPT: OPENAI_API_KEY'));
    console.log(chalk.gray('- Gemini: GOOGLE_API_KEY'));
  });

program
  .command('status')
  .description('Show current status and configuration')
  .action(async () => {
    try {
      const configManager = new ConfigManager();
      const gitManager = new GitManager();
      const todoManager = new TodoManager();
      
      const config = await configManager.loadConfig();
      const isGitRepo = await gitManager.isGitRepository();
      const hasChanges = await gitManager.hasChanges();
      const todos = await todoManager.getActiveTodos();

      console.log(chalk.bold('\n📊 Review Bot Status:\n'));
      
      console.log(`${chalk.cyan('Git Repository:')} ${isGitRepo ? '✅ Yes' : '❌ No'}`);
      console.log(`${chalk.cyan('Changes:')} ${hasChanges ? '📝 Yes' : '✅ None'}`);
      console.log(`${chalk.cyan('Provider:')} ${config.provider}`);
      console.log(`${chalk.cyan('Model:')} ${config.model || DEFAULT_MODELS[config.provider as keyof typeof DEFAULT_MODELS]}`);
      console.log(`${chalk.cyan('API Key:')} ${config.apiKey ? '✅ Set' : '❌ Not set'}`);
      console.log(`${chalk.cyan('Active TODOs:')} ${todos.length}`);
      console.log(`${chalk.cyan('Auto Review:')} Commit: ${config.autoReview?.onCommit ? '✅' : '❌'}, Push: ${config.autoReview?.onPush ? '✅' : '❌'}`);
    } catch (error) {
      console.error(chalk.red(`Failed to get status: ${error instanceof Error ? error.message : 'Unknown error'}`));
      process.exit(1);
    }
  });

if (require.main === module) {
  program.parse();
}