# 🤖 Code Review Bot

AI-powered code review bot that integrates with your Git workflow to provide automated code reviews using Claude, ChatGPT, or Gemini.

## ✨ Features

- 🔍 **Multi-AI Support**: Choose from Claude, ChatGPT, or Gemini
- 📝 **Customizable Prompts**: Edit prompt templates to fit your review needs
- 🎯 **Git Integration**: Review on commit, push, or manually
- 📊 **TODO Management**: Track improvement suggestions as actionable items
- 🎨 **Rich CLI Interface**: Beautiful terminal interface with colors and progress indicators
- ⚙️ **Flexible Configuration**: Local and global configuration options
- 📈 **Review History**: Save all reviews as markdown files

## 🚀 Installation

### Prerequisites
- Node.js 18+ 
- Git repository
- API key for your chosen AI provider

### Quick Start

1. **Clone and install:**
```bash
git clone <repository-url>
cd review-bot
npm install
npm run build
npm link  # Makes 'review-bot' available globally
```

2. **Initialize configuration:**
```bash
review-bot config init
```

3. **Set your AI provider and API key:**
```bash
# Using Claude (recommended)
review-bot config set provider claude
review-bot config set apiKey your-anthropic-api-key

# Or using environment variables
export ANTHROPIC_API_KEY="your-api-key"
```

4. **Run your first review:**
```bash
# Review current changes
review-bot run

# Review staged changes only
review-bot run --staged

# Review specific commit
review-bot run --commit abc123
```

## 🎯 Usage

### Basic Commands

```bash
# Run code review
review-bot run [options]

# Manage configuration
review-bot config init|set|get

# Manage TODO items
review-bot todo list|complete|delete

# Install/uninstall Git hooks
review-bot hooks install|uninstall

# View status
review-bot status
```

### Configuration

Create a `.reviewbotrc` file in your project or home directory:

```json
{
  "provider": "claude",
  "model": "claude-3-sonnet-20240229",
  "apiKey": "your-api-key",
  "promptTemplate": "default",
  "autoReview": {
    "onCommit": true,
    "onPush": false
  },
  "outputDir": "./reviews",
  "maxFilesPerReview": 50,
  "maxTokens": 4000
}
```

### Environment Variables

```bash
# API Keys
export ANTHROPIC_API_KEY="your-claude-api-key"
export OPENAI_API_KEY="your-openai-api-key" 
export GOOGLE_API_KEY="your-gemini-api-key"
```

## 🎨 Prompt Templates

The bot comes with three built-in prompt templates:

- **`default`**: General code review covering quality, performance, security
- **`security-focused`**: Specialized security vulnerability analysis
- **`performance-focused`**: Performance and optimization analysis

### Creating Custom Prompts

1. Create a new `.md` file in the `prompts/` directory
2. Use template variables like `{{code_diff}}`, `{{files_changed}}`
3. Use the new template: `review-bot run --prompt your-template`

Example custom prompt:
```markdown
# My Custom Review

Please review this code focusing on:
- Code readability
- Error handling
- Documentation

## Code Changes
{{code_diff}}
```

## 📋 TODO Management

The bot automatically creates TODO items from review suggestions:

```bash
# List active TODOs
review-bot todo list

# Mark TODO as completed
review-bot todo complete suggestion-1

# Export TODOs
review-bot todo export --format markdown
```

## 🔧 Git Hooks

Install Git hooks for automatic reviews:

```bash
# Install hooks
review-bot hooks install

# Enable auto-review on commit
review-bot config set autoReview.onCommit true
```

## 📊 Review Output

Reviews are saved as markdown files in the `reviews/` directory:

```
reviews/
├── review-2025-01-15T10-30-00.md
├── review-2025-01-14T15-45-00.md
└── todo/
    ├── todo-2025-01-15.json
    └── todo-2025-01-14.json
```

## 🤖 AI Providers

### Claude (Recommended)
- **Model**: `claude-3-sonnet-20240229` (default)
- **API Key**: Set `ANTHROPIC_API_KEY`
- **Cost**: ~$0.003-0.015 per 1K tokens

### ChatGPT
- **Model**: `gpt-4` (default)
- **API Key**: Set `OPENAI_API_KEY`  
- **Cost**: ~$0.03-0.06 per 1K tokens

### Gemini
- **Model**: `gemini-pro` (default)
- **API Key**: Set `GOOGLE_API_KEY`
- **Cost**: ~$0.00025-0.0005 per 1K tokens

## 📈 Examples

### Basic Review
```bash
# Review current changes
review-bot run

# Output:
# ✅ Review Summary:
# Provider: claude (claude-3-sonnet-20240229)
# Issues found: 3
# Suggestions: 5
# Tokens used: 2,450
# Estimated cost: $0.0087
```

### Security Review
```bash
review-bot run --prompt security-focused
```

### Performance Review
```bash
review-bot run --prompt performance-focused
```

## 🛠️ Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Run tests
npm test

# Build
npm run build

# Lint and type check
npm run lint
npm run typecheck
```

## 📁 Project Structure

```
review-bot/
├── src/
│   ├── core/           # Core managers (config, git, review, etc.)
│   ├── providers/      # AI service integrations  
│   ├── cli/           # Command-line interface
│   └── types/         # TypeScript definitions
├── prompts/           # Review prompt templates
├── reviews/           # Review output directory
├── tests/             # Test files
└── config/            # Configuration files
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- 🐛 **Bug reports**: Create an issue on GitHub
- 💡 **Feature requests**: Create an issue with enhancement label  
- 📖 **Documentation**: Check the `/docs` directory
- 💬 **Questions**: Start a discussion on GitHub

## 🗺️ Roadmap

- [ ] **Web Dashboard**: Browser-based review management
- [ ] **Team Features**: Shared configurations and reviews
- [ ] **Integration**: GitHub/GitLab PR integration
- [ ] **Analytics**: Review metrics and insights
- [ ] **Custom Rules**: Define project-specific review criteria

---

Made with ❤️ for better code quality