import { promises as fs } from 'fs';
import { join } from 'path';
import { TodoItem } from '../types';
import chalk from 'chalk';

export class TodoManager {
  private todoDir: string;

  constructor(outputDir = './reviews') {
    this.todoDir = join(outputDir, 'todo');
  }

  async getAllTodos(): Promise<TodoItem[]> {
    try {
      await fs.access(this.todoDir);
    } catch {
      await fs.mkdir(this.todoDir, { recursive: true });
      return [];
    }

    try {
      const files = await fs.readdir(this.todoDir);
      const todoFiles = files.filter(f => f.startsWith('todo-') && f.endsWith('.json'));
      
      const allTodos: TodoItem[] = [];
      
      for (const file of todoFiles) {
        const filepath = join(this.todoDir, file);
        const content = await fs.readFile(filepath, 'utf-8');
        const todos = JSON.parse(content) as TodoItem[];
        allTodos.push(...todos);
      }
      
      return allTodos.sort((a, b) => {
        if (a.completed && !b.completed) return 1;
        if (!a.completed && b.completed) return -1;
        
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        const aPriority = priorityOrder[a.priority] ?? 1;
        const bPriority = priorityOrder[b.priority] ?? 1;
        
        if (aPriority !== bPriority) {
          return aPriority - bPriority;
        }
        
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      });
    } catch (error) {
      console.warn('Error reading TODO items:', error);
      return [];
    }
  }

  async getActiveTodos(): Promise<TodoItem[]> {
    const allTodos = await this.getAllTodos();
    return allTodos.filter(todo => !todo.completed);
  }

  async getCompletedTodos(): Promise<TodoItem[]> {
    const allTodos = await this.getAllTodos();
    return allTodos.filter(todo => todo.completed);
  }

  async markTodoCompleted(todoId: string): Promise<void> {
    const todos = await this.getAllTodos();
    const todo = todos.find(t => t.id === todoId);
    
    if (!todo) {
      throw new Error(`TODO item with id '${todoId}' not found`);
    }
    
    if (todo.completed) {
      console.log(`TODO item '${todoId}' is already completed`);
      return;
    }
    
    todo.completed = true;
    await this.saveTodoUpdate(todo);
    
    console.log(chalk.green(`✓ TODO item '${todo.title}' marked as completed`));
  }

  async markTodoActive(todoId: string): Promise<void> {
    const todos = await this.getAllTodos();
    const todo = todos.find(t => t.id === todoId);
    
    if (!todo) {
      throw new Error(`TODO item with id '${todoId}' not found`);
    }
    
    if (!todo.completed) {
      console.log(`TODO item '${todoId}' is already active`);
      return;
    }
    
    todo.completed = false;
    await this.saveTodoUpdate(todo);
    
    console.log(chalk.blue(`↺ TODO item '${todo.title}' marked as active`));
  }

  async deleteTodo(todoId: string): Promise<void> {
    const todos = await this.getAllTodos();
    const todoIndex = todos.findIndex(t => t.id === todoId);
    
    if (todoIndex === -1) {
      throw new Error(`TODO item with id '${todoId}' not found`);
    }
    
    const todo = todos[todoIndex];
    todos.splice(todoIndex, 1);
    
    await this.saveAllTodos(todos);
    
    console.log(chalk.red(`🗑 TODO item '${todo.title}' deleted`));
  }

  async displayTodos(options: {
    showCompleted?: boolean;
    filter?: 'all' | 'active' | 'completed';
    priority?: 'high' | 'medium' | 'low';
  } = {}): Promise<void> {
    let todos = await this.getAllTodos();
    
    if (options.filter === 'active') {
      todos = todos.filter(t => !t.completed);
    } else if (options.filter === 'completed') {
      todos = todos.filter(t => t.completed);
    }
    
    if (options.priority) {
      todos = todos.filter(t => t.priority === options.priority);
    }

    if (todos.length === 0) {
      console.log(chalk.gray('No TODO items found'));
      return;
    }

    const activeTodos = todos.filter(t => !t.completed);
    const completedTodos = todos.filter(t => t.completed);

    if (activeTodos.length > 0) {
      console.log(chalk.bold('\n📝 Active TODOs:\n'));
      this.displayTodoList(activeTodos);
    }

    if (completedTodos.length > 0 && (options.showCompleted || options.filter === 'completed')) {
      console.log(chalk.bold('\n✅ Completed TODOs:\n'));
      this.displayTodoList(completedTodos, true);
    }

    this.displaySummary(activeTodos.length, completedTodos.length);
  }

  private displayTodoList(todos: TodoItem[], showCompleted = false): void {
    todos.forEach((todo, index) => {
      const priorityIcon = this.getPriorityIcon(todo.priority);
      const statusIcon = todo.completed ? '✅' : '⭕';
      const todoText = showCompleted ? chalk.strikethrough(todo.title) : todo.title;
      
      console.log(`${statusIcon} ${priorityIcon} [${chalk.cyan(todo.id)}] ${todoText}`);
      
      if (todo.description && todo.description !== todo.title) {
        console.log(chalk.gray(`   ${todo.description}`));
      }
      
      if (todo.files && todo.files.length > 0) {
        console.log(chalk.gray(`   📁 Files: ${todo.files.join(', ')}`));
      }
      
      const createdDate = new Date(todo.createdAt).toLocaleDateString();
      console.log(chalk.gray(`   📅 Created: ${createdDate} | Review: ${todo.reviewId}`));
      
      if (todo.dueDate) {
        const dueDate = new Date(todo.dueDate).toLocaleDateString();
        console.log(chalk.gray(`   ⏰ Due: ${dueDate}`));
      }
      
      console.log();
    });
  }

  private getPriorityIcon(priority: string): string {
    switch (priority) {
      case 'high': return chalk.red('🔴');
      case 'medium': return chalk.yellow('🟡');
      case 'low': return chalk.green('🟢');
      default: return '⚪';
    }
  }

  private displaySummary(active: number, completed: number): void {
    const total = active + completed;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    console.log(chalk.bold('\n📊 Summary:'));
    console.log(`Total: ${chalk.blue(total.toString())} | Active: ${chalk.yellow(active.toString())} | Completed: ${chalk.green(completed.toString())} | Progress: ${chalk.cyan(completionRate + '%')}`);
  }

  private async saveTodoUpdate(todo: TodoItem): Promise<void> {
    const todos = await this.getAllTodos();
    const index = todos.findIndex(t => t.id === todo.id);
    
    if (index !== -1) {
      todos[index] = todo;
      await this.saveAllTodos(todos);
    }
  }

  private async saveAllTodos(todos: TodoItem[]): Promise<void> {
    const files = await fs.readdir(this.todoDir);
    const todoFiles = files.filter(f => f.startsWith('todo-') && f.endsWith('.json'));
    
    for (const file of todoFiles) {
      const filepath = join(this.todoDir, file);
      await fs.unlink(filepath);
    }

    const todosByDate: { [date: string]: TodoItem[] } = {};
    
    todos.forEach(todo => {
      const dateKey = todo.createdAt.split('T')[0];
      if (!todosByDate[dateKey]) {
        todosByDate[dateKey] = [];
      }
      todosByDate[dateKey].push(todo);
    });

    for (const [date, dateTodos] of Object.entries(todosByDate)) {
      const filename = `todo-${date}.json`;
      const filepath = join(this.todoDir, filename);
      await fs.writeFile(filepath, JSON.stringify(dateTodos, null, 2), 'utf-8');
    }
  }

  async exportTodos(format: 'json' | 'csv' | 'markdown' = 'json', outputPath?: string): Promise<void> {
    const todos = await this.getAllTodos();
    
    if (todos.length === 0) {
      console.log('No TODOs to export');
      return;
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const defaultPath = `todos-export-${timestamp}`;
    
    switch (format) {
      case 'json':
        const jsonPath = outputPath || `${defaultPath}.json`;
        await fs.writeFile(jsonPath, JSON.stringify(todos, null, 2), 'utf-8');
        console.log(chalk.green(`TODOs exported to: ${jsonPath}`));
        break;
        
      case 'csv':
        const csvPath = outputPath || `${defaultPath}.csv`;
        const csvContent = this.convertToCsv(todos);
        await fs.writeFile(csvPath, csvContent, 'utf-8');
        console.log(chalk.green(`TODOs exported to: ${csvPath}`));
        break;
        
      case 'markdown':
        const mdPath = outputPath || `${defaultPath}.md`;
        const mdContent = this.convertToMarkdown(todos);
        await fs.writeFile(mdPath, mdContent, 'utf-8');
        console.log(chalk.green(`TODOs exported to: ${mdPath}`));
        break;
    }
  }

  private convertToCsv(todos: TodoItem[]): string {
    const headers = ['ID', 'Title', 'Description', 'Priority', 'Status', 'Files', 'Created', 'Due Date', 'Review ID'];
    const rows = todos.map(todo => [
      todo.id,
      `"${todo.title.replace(/"/g, '""')}"`,
      `"${(todo.description || '').replace(/"/g, '""')}"`,
      todo.priority,
      todo.completed ? 'Completed' : 'Active',
      `"${(todo.files || []).join(', ')}"`,
      new Date(todo.createdAt).toLocaleDateString(),
      todo.dueDate ? new Date(todo.dueDate).toLocaleDateString() : '',
      todo.reviewId
    ]);
    
    return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
  }

  private convertToMarkdown(todos: TodoItem[]): string {
    const active = todos.filter(t => !t.completed);
    const completed = todos.filter(t => t.completed);
    
    let markdown = '# TODO Items Export\n\n';
    
    if (active.length > 0) {
      markdown += '## Active TODOs\n\n';
      active.forEach(todo => {
        const priorityEmoji = todo.priority === 'high' ? '🔴' : todo.priority === 'medium' ? '🟡' : '🟢';
        markdown += `### ${priorityEmoji} ${todo.title}\n\n`;
        markdown += `**ID:** ${todo.id}\n`;
        markdown += `**Priority:** ${todo.priority}\n`;
        markdown += `**Created:** ${new Date(todo.createdAt).toLocaleDateString()}\n`;
        if (todo.files && todo.files.length > 0) {
          markdown += `**Files:** ${todo.files.join(', ')}\n`;
        }
        if (todo.dueDate) {
          markdown += `**Due Date:** ${new Date(todo.dueDate).toLocaleDateString()}\n`;
        }
        markdown += `**Review:** ${todo.reviewId}\n\n`;
        if (todo.description && todo.description !== todo.title) {
          markdown += `${todo.description}\n\n`;
        }
        if (todo.example) {
          markdown += `**Example:**\n\`\`\`\n${todo.example}\n\`\`\`\n\n`;
        }
        markdown += '---\n\n';
      });
    }

    if (completed.length > 0) {
      markdown += '## Completed TODOs\n\n';
      completed.forEach(todo => {
        markdown += `- ✅ ~~${todo.title}~~ (${new Date(todo.createdAt).toLocaleDateString()})\n`;
      });
    }

    return markdown;
  }
}