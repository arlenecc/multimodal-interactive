"""Tests for configuration management module."""
import json
import os
import tempfile

import pytest

from src.config import AppConfig


class TestAppConfig:
    """Test AppConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AppConfig()
        assert config.base_url == ""
        assert config.api_key == ""
        assert config.model_name == ""
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.stream_enabled is True

    def test_custom_values(self):
        """Test setting custom configuration values."""
        config = AppConfig(
            base_url="https://api.example.com/v1",
            api_key="sk-test-key",
            model_name="gpt-4o",
            max_tokens=2048,
            temperature=0.5,
            stream_enabled=False,
        )
        assert config.base_url == "https://api.example.com/v1"
        assert config.api_key == "sk-test-key"
        assert config.model_name == "gpt-4o"
        assert config.max_tokens == 2048
        assert config.temperature == 0.5
        assert config.stream_enabled is False

    def test_save_and_load(self, tmp_path):
        """Test saving and loading configuration."""
        config_file = str(tmp_path / "config.json")
        config = AppConfig(
            base_url="https://api.example.com/v1",
            api_key="sk-test-key",
            model_name="gpt-4o",
        )
        config.save(config_file)

        loaded = AppConfig.load(config_file)
        assert loaded.base_url == config.base_url
        assert loaded.api_key == config.api_key
        assert loaded.model_name == config.model_name

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from a nonexistent file returns defaults."""
        config_file = str(tmp_path / "nonexistent.json")
        config = AppConfig.load(config_file)
        assert config.base_url == ""
        assert config.api_key == ""

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = AppConfig(
            base_url="https://api.example.com/v1",
            api_key="sk-test-key",
        )
        d = config.to_dict()
        assert isinstance(d, dict)
        assert d["base_url"] == "https://api.example.com/v1"
        assert d["api_key"] == "sk-test-key"

    def test_from_dict(self):
        """Test creating config from dictionary."""
        d = {
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-test-key",
            "model_name": "gpt-4o-mini",
            "max_tokens": 1024,
            "temperature": 0.3,
            "stream_enabled": False,
        }
        config = AppConfig.from_dict(d)
        assert config.base_url == "https://api.example.com/v1"
        assert config.model_name == "gpt-4o-mini"
        assert config.max_tokens == 1024
        assert config.stream_enabled is False

    def test_validate_valid_config(self):
        """Test validation with valid config."""
        config = AppConfig(
            base_url="https://api.example.com/v1",
            api_key="sk-test-key",
            model_name="gpt-4o",
        )
        is_valid, errors = config.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_base_url(self):
        """Test validation catches missing base_url."""
        config = AppConfig(api_key="sk-test-key", model_name="gpt-4o")
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("base_url" in e.lower() or "base url" in e.lower() or "服务地址" in e for e in errors)

    def test_validate_missing_api_key(self):
        """Test validation catches missing api_key."""
        config = AppConfig(base_url="https://api.example.com/v1", model_name="gpt-4o")
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("api" in e.lower() or "key" in e.lower() for e in errors)

    def test_validate_missing_model_name(self):
        """Test validation catches missing model_name."""
        config = AppConfig(
            base_url="https://api.example.com/v1",
            api_key="sk-test-key",
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("model" in e.lower() or "模型" in e for e in errors)

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is normalized."""
        config = AppConfig(base_url="https://api.example.com/v1/")
        assert config.base_url == "https://api.example.com/v1"

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directories if needed."""
        config_file = str(tmp_path / "subdir" / "config.json")
        config = AppConfig(base_url="https://api.example.com/v1")
        config.save(config_file)
        assert os.path.exists(config_file)

    def test_roundtrip_preserves_all_fields(self, tmp_path):
        """Test save/load roundtrip preserves all fields."""
        config = AppConfig(
            base_url="https://api.example.com/v1",
            api_key="sk-roundtrip-test",
            model_name="gpt-4-vision",
            max_tokens=8192,
            temperature=0.9,
            stream_enabled=False,
        )
        config_file = str(tmp_path / "config.json")
        config.save(config_file)
        loaded = AppConfig.load(config_file)
        assert loaded.to_dict() == config.to_dict()
