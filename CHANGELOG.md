# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-15

### Added
- 🎉 Initial release of Code Review Bot
- 🤖 Multi-AI provider support (Claude, ChatGPT, Gemini)
- 📝 Customizable prompt template system
- 🔧 Git hooks integration for automatic reviews
- 📋 TODO management system for tracking improvements
- 🎨 Rich CLI interface with colors and progress indicators
- ⚙️ Flexible configuration system (local and global)
- 📊 Review history saved as markdown files
- 🧪 Comprehensive test suite
- 📖 Complete documentation

### Features
- **AI Providers**:
  - Claude (Anthropic) with cost estimation
  - ChatGPT (OpenAI) with multiple model support
  - Gemini (Google) with latest models
  
- **Review Capabilities**:
  - Review staged changes, working directory, or specific commits
  - Custom prompt templates (default, security-focused, performance-focused)
  - Detailed issue categorization (critical, major, minor)
  - Improvement suggestions with examples
  
- **CLI Commands**:
  - `review-bot run` - Execute code reviews
  - `review-bot config` - Manage configuration
  - `review-bot todo` - Manage TODO items
  - `review-bot hooks` - Git hooks management
  - `review-bot status` - Show current status
  
- **Configuration Options**:
  - Provider and model selection
  - API key management via env vars or config
  - Auto-review on commit/push
  - File filtering and limits
  - Custom output directories

### Technical Details
- TypeScript implementation with full type safety
- Modular architecture with separation of concerns
- Comprehensive error handling and validation
- Jest testing framework with high coverage
- ESLint and TypeScript strict mode
- Git integration using simple-git library
- Beautiful terminal output using chalk and ora

### Documentation
- Complete README with usage examples
- Inline code documentation
- Configuration reference
- Prompt template guide
- Development setup instructions