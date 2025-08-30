"""Configuration management for the review bot."""

import os
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import ValidationError
from dotenv import load_dotenv

from models.types import ReviewConfig, Provider


class ConfigManager:
    """Manages configuration for the review bot."""
    
    def __init__(self):
        """Initialize config manager."""
        self.config_filename = ".reviewbotrc"
        self.global_config_path = Path.home() / self.config_filename
        self.local_config_path = Path.cwd() / self.config_filename
        
        # Load environment variables
        load_dotenv()
    
    async def load_config(self) -> ReviewConfig:
        """Load configuration from files and environment."""
        # Start with default config
        config_data = self._get_default_config()
        
        # Override with global config
        global_config = await self._load_config_file(self.global_config_path)
        if global_config:
            config_data.update(global_config)
        
        # Override with local config
        local_config = await self._load_config_file(self.local_config_path)
        if local_config:
            config_data.update(local_config)
        
        # Override with environment variables
        env_config = self._load_env_config()
        config_data.update(env_config)
        
        try:
            return ReviewConfig(**config_data)
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    async def save_config(self, config: Dict[str, Any], global_config: bool = False) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration data to save
            global_config: Whether to save to global or local config file
        """
        target_path = self.global_config_path if global_config else self.local_config_path
        
        # Load existing config
        existing_config = await self._load_config_file(target_path) or {}
        
        # Merge with new config
        existing_config.update(config)
        
        # Save to file
        await self._save_config_file(target_path, existing_config)
    
    async def init_config(self) -> None:
        """Initialize configuration file with defaults."""
        if self.local_config_path.exists():
            print("Configuration file already exists")
            return
        
        default_config = self._get_default_config()
        await self._save_config_file(self.local_config_path, default_config)
        print(f"Configuration initialized: {self.local_config_path}")
    
    def validate_config(self, config: ReviewConfig) -> tuple[bool, list[str]]:
        """Validate configuration.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not config.api_key:
            errors.append(f"API key is required for {config.provider}")
        
        if config.max_files_per_review <= 0:
            errors.append("max_files_per_review must be greater than 0")
        
        if config.max_tokens <= 0:
            errors.append("max_tokens must be greater than 0")
        
        if not config.output_dir:
            errors.append("output_dir is required")
        
        if config.temperature < 0 or config.temperature > 2:
            errors.append("temperature must be between 0 and 2")
        
        return len(errors) == 0, errors
    
    def get_config_path(self, global_config: bool = False) -> Path:
        """Get path to configuration file."""
        return self.global_config_path if global_config else self.local_config_path
    
    async def _load_config_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from file."""
        if not path.exists():
            return None
        
        try:
            content = path.read_text(encoding='utf-8')
            
            # Try YAML first, then JSON
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError:
                return json.loads(content)
                
        except (json.JSONDecodeError, yaml.YAMLError, OSError):
            return None
    
    async def _save_config_file(self, path: Path, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save as YAML for better readability
            content = yaml.dump(config, default_flow_style=False, sort_keys=True)
            path.write_text(content, encoding='utf-8')
            
        except OSError as e:
            raise ValueError(f"Failed to save configuration: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "provider": Provider.CLAUDE.value,
            "model": None,
            "api_key": "",
            "prompt_template": "default",
            "auto_review": {
                "on_commit": False,
                "on_push": False,
            },
            "output_dir": "./reviews",
            "exclude_patterns": [
                "node_modules/**",
                "*.log",
                "dist/**",
                "build/**",
                "__pycache__/**",
                "*.pyc",
                ".git/**",
            ],
            "include_patterns": [
                "**/*.py",
                "**/*.ts",
                "**/*.js",
                "**/*.tsx",
                "**/*.jsx",
                "**/*.go",
                "**/*.rs",
                "**/*.java",
                "**/*.cpp",
                "**/*.c",
                "**/*.h",
            ],
            "max_files_per_review": 50,
            "max_tokens": 4000,
            "temperature": 0.1,
        }
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        # API keys
        if os.getenv("ANTHROPIC_API_KEY"):
            config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        elif os.getenv("OPENAI_API_KEY"):
            config["api_key"] = os.getenv("OPENAI_API_KEY")
        elif os.getenv("GOOGLE_API_KEY"):
            config["api_key"] = os.getenv("GOOGLE_API_KEY")
        
        # Other environment variables
        env_mappings = {
            "REVIEWBOT_PROVIDER": "provider",
            "REVIEWBOT_MODEL": "model",
            "REVIEWBOT_PROMPT_TEMPLATE": "prompt_template",
            "REVIEWBOT_OUTPUT_DIR": "output_dir",
            "REVIEWBOT_MAX_TOKENS": ("max_tokens", int),
            "REVIEWBOT_TEMPERATURE": ("temperature", float),
            "REVIEWBOT_MAX_FILES": ("max_files_per_review", int),
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                if isinstance(config_key, tuple):
                    key, converter = config_key
                    try:
                        config[key] = converter(value)
                    except (ValueError, TypeError):
                        pass  # Skip invalid values
                else:
                    config[config_key] = value
        
        return config