# AI Code Review Bot 🤖

An intelligent code review assistant powered by Claude, ChatGPT, and Gemini that helps improve your code quality through automated reviews.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Poetry](https://img.shields.io/badge/Poetry-dependency%20management-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-pytest-green)

## ✨ Features

- 🤖 **Multi-AI Support**: Works with Claude (Anthropic), ChatGPT (OpenAI), and Gemini (Google)
- 📝 **Customizable Prompts**: Create and use custom review templates with Jinja2
- 🔧 **Git Integration**: Seamlessly integrates with your Git workflow via hooks
- 📊 **Rich CLI Interface**: Beautiful command-line interface with progress bars and colors
- 🌐 **Web Dashboard**: Modern FastAPI-based web interface for managing reviews
- ✅ **TODO Management**: Track and manage code improvement suggestions
- 🎯 **Smart Filtering**: Review specific files, staged changes, or commits
- 💰 **Cost Estimation**: Estimate AI API costs before running reviews
- 🔄 **Async Operations**: Fast, concurrent processing of multiple files

## 🚀 Quick Start

### Installation

**Recommended: Git-based Installation** (avoids system Python issues)

```bash
# Option 1: Automatic installation script
curl -sSL https://raw.githubusercontent.com/your-username/code-review-bot/main/install.sh | bash

# Option 2: Manual Git clone with Poetry
git clone https://github.com/your-username/code-review-bot.git
cd code-review-bot
poetry install

# Option 3: Manual Git clone with venv
git clone https://github.com/your-username/code-review-bot.git
cd code-review-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Option 4: pipx from Git
pipx install git+https://github.com/your-username/code-review-bot.git
```

### Basic Usage

1. **Initialize configuration:**
   ```bash
   review-bot config init
   ```

2. **Set your API key:**
   ```bash
   # For Claude (recommended)
   review-bot config set api_key YOUR_ANTHROPIC_API_KEY

   # For ChatGPT
   review-bot config set provider chatgpt
   review-bot config set api_key YOUR_OPENAI_API_KEY

   # For Gemini
   review-bot config set provider gemini
   review-bot config set api_key YOUR_GOOGLE_API_KEY
   ```

3. **Run your first review:**
   ```bash
   # Review current working changes
   review-bot run

   # Review staged changes
   review-bot run --staged

   # Review a specific commit
   review-bot run --commit abc123

   # Use a custom prompt template
   review-bot run --prompt security
   ```

4. **Launch web dashboard:**
   ```bash
   review-bot dashboard
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

The bot supports both file-based and environment variable configuration:

```yaml
# ~/.review-bot/config.yaml
provider: claude
model: claude-3-5-sonnet-20241022
api_key: your-api-key
output_dir: reviews
max_files_per_review: 50
temperature: 0.1
auto_review:
  on_commit: true
  on_push: false
```

Environment variables:
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - ChatGPT API key  
- `GOOGLE_API_KEY` - Gemini API key

## 🎨 Prompt Templates

The bot comes with three built-in prompt templates:

- **`default`**: General code review covering quality, performance, security
- **`security-focused`**: Specialized security vulnerability analysis
- **`performance-focused`**: Performance and optimization analysis

### Custom Prompt Templates

Create custom review templates with Jinja2:

```markdown
<!-- prompts/security.md -->
---
description: "Security-focused code review"
author: "Security Team"
---

# Security Code Review

Please perform a security review of the following changes:

{{ code_diff }}

## Focus Areas
- Input validation
- Authentication & authorization
- SQL injection prevention
- XSS prevention
- Secure data handling

Files changed: {{ files_changed }}
Branch: {{ branch }}
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

---

Made with ❤️ for better code quality
