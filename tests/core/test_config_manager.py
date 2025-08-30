"""Tests for ConfigManager."""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from core.config_manager import ConfigManager
from models.types import ReviewConfig, Provider


class TestConfigManager:
    """Test ConfigManager functionality."""
    
    @pytest.mark.asyncio
    async def test_init_config(self, temp_dir: Path):
        """Test configuration initialization."""
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager()
            await manager.init_config()
            
            config_file = temp_dir / "config.yaml"
            assert config_file.exists()
            
            # Load and verify default config
            config_data = yaml.safe_load(config_file.read_text())
            assert config_data["provider"] == "claude"
            assert config_data["output_dir"] == "reviews"
            assert config_data["max_files_per_review"] == 50
    
    @pytest.mark.asyncio
    async def test_load_config_yaml(self, temp_dir: Path):
        """Test loading YAML configuration."""
        config_file = temp_dir / "config.yaml"
        config_data = {
            "provider": "claude",
            "model": "claude-3-5-sonnet-20241022",
            "api_key": "test-key",
            "output_dir": "custom-reviews",
            "max_files_per_review": 25,
            "temperature": 0.2
        }
        config_file.write_text(yaml.dump(config_data))
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager()
            config = await manager.load_config()
            
            assert config.provider == Provider.CLAUDE
            assert config.model == "claude-3-5-sonnet-20241022"
            assert config.api_key == "test-key"
            assert config.output_dir == Path("custom-reviews")
            assert config.max_files_per_review == 25
            assert config.temperature == 0.2
    
    @pytest.mark.asyncio
    async def test_load_config_json(self, temp_dir: Path):
        """Test loading JSON configuration."""
        config_file = temp_dir / "config.json"
        config_data = {
            "provider": "chatgpt",
            "model": "gpt-4",
            "api_key": "openai-key",
            "output_dir": "reviews",
            "auto_review": {
                "on_commit": True,
                "on_push": False
            }
        }
        config_file.write_text(json.dumps(config_data))
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager()
            config = await manager.load_config()
            
            assert config.provider == Provider.CHATGPT
            assert config.model == "gpt-4"
            assert config.api_key == "openai-key"
            assert config.auto_review["on_commit"] is True
            assert config.auto_review["on_push"] is False
    
    @pytest.mark.asyncio
    async def test_load_config_with_environment_variables(self, temp_dir: Path):
        """Test loading configuration with environment variable override."""
        config_file = temp_dir / "config.yaml"
        config_data = {
            "provider": "claude",
            "api_key": "file-key"
        }
        config_file.write_text(yaml.dump(config_data))
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key'}):
                manager = ConfigManager()
                config = await manager.load_config()
                
                # Environment variable should override file value
                assert config.api_key == "env-key"
    
    @pytest.mark.asyncio
    async def test_save_config_yaml(self, temp_dir: Path):
        """Test saving configuration as YAML."""
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager()
            
            config_data = {
                "provider": "gemini",
                "model": "gemini-pro",
                "api_key": "google-key",
                "temperature": 0.3
            }
            
            await manager.save_config(config_data)
            
            config_file = temp_dir / "config.yaml"
            assert config_file.exists()
            
            loaded_data = yaml.safe_load(config_file.read_text())
            assert loaded_data["provider"] == "gemini"
            assert loaded_data["model"] == "gemini-pro"
            assert loaded_data["api_key"] == "google-key"
            assert loaded_data["temperature"] == 0.3
    
    @pytest.mark.asyncio
    async def test_save_config_json(self, temp_dir: Path):
        """Test saving configuration as JSON."""
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager(config_format="json")
            
            config_data = {
                "provider": "claude",
                "max_tokens": 150000
            }
            
            await manager.save_config(config_data)
            
            config_file = temp_dir / "config.json"
            assert config_file.exists()
            
            loaded_data = json.loads(config_file.read_text())
            assert loaded_data["provider"] == "claude"
            assert loaded_data["max_tokens"] == 150000
    
    @pytest.mark.asyncio
    async def test_global_config(self, temp_dir: Path):
        """Test global configuration handling."""
        global_dir = temp_dir / "global"
        global_dir.mkdir()
        
        with patch('core.config_manager.ConfigManager._get_global_config_dir', return_value=global_dir):
            manager = ConfigManager()
            
            # Save global config
            global_config = {"provider": "claude", "api_key": "global-key"}
            await manager.save_config(global_config, global_config=True)
            
            # Verify global config file exists
            global_config_file = global_dir / "config.yaml"
            assert global_config_file.exists()
            
            # Load should use global config when local doesn't exist
            config = await manager.load_config()
            assert config.api_key == "global-key"
    
    @pytest.mark.asyncio
    async def test_config_validation_error(self, temp_dir: Path):
        """Test configuration validation errors."""
        config_file = temp_dir / "config.yaml"
        invalid_config = {
            "provider": "invalid-provider",  # Invalid enum value
            "temperature": 2.0,  # Invalid range
            "max_files_per_review": -1  # Invalid range
        }
        config_file.write_text(yaml.dump(invalid_config))
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager()
            
            with pytest.raises(ValueError) as exc_info:
                await manager.load_config()
            
            assert "Configuration validation error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_config_file_not_found(self, temp_dir: Path):
        """Test behavior when config file doesn't exist."""
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            with patch('core.config_manager.ConfigManager._get_global_config_dir', return_value=temp_dir / "global"):
                manager = ConfigManager()
                
                # Should return default config when no files exist
                config = await manager.load_config()
                
                assert config.provider == Provider.CLAUDE
                assert config.output_dir == Path("reviews")
                assert config.max_files_per_review == 50
    
    @pytest.mark.asyncio
    async def test_invalid_yaml_file(self, temp_dir: Path):
        """Test handling of invalid YAML files."""
        config_file = temp_dir / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager()
            
            with pytest.raises(ValueError) as exc_info:
                await manager.load_config()
            
            assert "Invalid YAML format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invalid_json_file(self, temp_dir: Path):
        """Test handling of invalid JSON files."""
        config_file = temp_dir / "config.json"
        config_file.write_text('{"invalid": "json"')
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=temp_dir):
            manager = ConfigManager()
            
            with pytest.raises(ValueError) as exc_info:
                await manager.load_config()
            
            assert "Invalid JSON format" in str(exc_info.value)
    
    def test_get_config_dir_default(self):
        """Test default config directory resolution."""
        manager = ConfigManager()
        config_dir = manager._get_config_dir()
        
        assert config_dir.name == ".review-bot"
        assert config_dir.is_absolute()
    
    def test_get_global_config_dir(self):
        """Test global config directory resolution."""
        manager = ConfigManager()
        global_dir = manager._get_global_config_dir()
        
        assert global_dir.name == ".review-bot"
        assert global_dir.is_absolute()
        assert str(global_dir).startswith(str(Path.home()))
    
    @pytest.mark.asyncio
    async def test_merge_configs(self, temp_dir: Path):
        """Test configuration merging from multiple sources."""
        # Create global config
        global_dir = temp_dir / "global"
        global_dir.mkdir()
        global_config_file = global_dir / "config.yaml"
        global_config = {
            "provider": "claude",
            "api_key": "global-key",
            "temperature": 0.1,
            "auto_review": {"on_commit": True}
        }
        global_config_file.write_text(yaml.dump(global_config))
        
        # Create local config
        local_dir = temp_dir / "local"
        local_dir.mkdir()
        local_config_file = local_dir / "config.yaml"
        local_config = {
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.2,  # Should override global
            "auto_review": {"on_push": True}  # Should merge with global
        }
        local_config_file.write_text(yaml.dump(local_config))
        
        with patch('core.config_manager.ConfigManager._get_config_dir', return_value=local_dir):
            with patch('core.config_manager.ConfigManager._get_global_config_dir', return_value=global_dir):
                manager = ConfigManager()
                config = await manager.load_config()
                
                # Should use global provider and api_key
                assert config.provider == Provider.CLAUDE
                assert config.api_key == "global-key"
                
                # Should use local model and temperature
                assert config.model == "claude-3-5-sonnet-20241022"
                assert config.temperature == 0.2
                
                # Should merge auto_review settings
                assert config.auto_review["on_commit"] is True
                assert config.auto_review["on_push"] is True