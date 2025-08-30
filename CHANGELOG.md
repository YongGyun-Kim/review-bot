# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-08-30

### Added
- 🐍 Complete Python rewrite using modern Python 3.11+ features
- 🌐 FastAPI-based web dashboard with real-time WebSocket updates
- ⚡ Async/await patterns for better performance and concurrency
- 🎨 Rich CLI interface with beautiful terminal output using Rich library
- 🧪 Comprehensive pytest test suite with fixtures and mocking
- 🔧 Jinja2 template engine for powerful, customizable prompts
- ⚙️ YAML configuration support with environment variable overrides
- 📈 GitPython integration for robust and reliable Git operations
- 💰 Cost estimation and token usage tracking for AI API calls
- 🎯 Advanced file filtering and smart change detection
- ✅ Enhanced TODO management system with priority tracking and export
- 📝 Multiple output formats (Markdown, JSON) for review results
- 🪝 Improved Git hooks integration for automatic reviews
- 🔍 Real-time progress tracking and status updates

### Changed
- **Architecture**: Migrated from TypeScript/Node.js to Python for better universality and ecosystem
- **Configuration**: Enhanced management with local/global config support and YAML format
- **Templates**: Improved prompt template system with YAML front matter and variable extraction  
- **Error Handling**: Better error messages, validation, and user feedback
- **Git Integration**: More reliable operations using GitPython instead of shell commands
- **CLI Framework**: Switched to Typer for better argument parsing and help generation
- **Testing**: Comprehensive pytest suite with async testing and better coverage

### Technical Details
- **Python 3.11+** with Poetry for dependency management
- **Pydantic V2** for robust data validation and type safety
- **FastAPI** for modern web API with automatic documentation
- **Rich & Typer** for beautiful CLI interfaces with colors and formatting
- **GitPython** for reliable Git repository operations
- **Jinja2** for flexible template rendering with custom filters
- **Async/await** patterns throughout for better performance
- **WebSocket** support for real-time dashboard updates

### Removed
- TypeScript/Node.js implementation (moved to `archive/` directory)
- Legacy configuration format and CLI structure
- Old prompt template system without YAML support

## [1.0.0] - 2025-01-15

### Added
- 🎉 Initial TypeScript implementation
- 🤖 Basic AI provider support (Claude, ChatGPT, Gemini)
- 📝 Simple prompt template system
- 🔧 Git hooks integration
- 📋 Basic TODO management
- 🎨 CLI interface using Commander.js
- ⚙️ Configuration management