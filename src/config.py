"""Configuration management module."""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, List


@dataclass
class AppConfig:
    """Application configuration."""

    base_url: str = ""
    api_key: str = ""
    model_name: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    stream_enabled: bool = True

    def __post_init__(self):
        # Normalize base_url: remove trailing slash
        if self.base_url and self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream_enabled": self.stream_enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AppConfig":
        """Create config from dictionary."""
        return cls(
            base_url=d.get("base_url", ""),
            api_key=d.get("api_key", ""),
            model_name=d.get("model_name", ""),
            max_tokens=d.get("max_tokens", 4096),
            temperature=d.get("temperature", 0.7),
            stream_enabled=d.get("stream_enabled", True),
        )

    def save(self, filepath: str):
        """Save configuration to file."""
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> "AppConfig":
        """Load configuration from file. Returns defaults if file doesn't exist."""
        if not os.path.exists(filepath):
            return cls()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return cls()

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate configuration. Returns (is_valid, list_of_errors)."""
        errors = []
        if not self.base_url or not self.base_url.strip():
            errors.append("服务地址 (Base URL) 不能为空")
        if not self.api_key or not self.api_key.strip():
            errors.append("API Key 不能为空")
        if not self.model_name or not self.model_name.strip():
            errors.append("模型名称 (Model) 不能为空")
        if self.max_tokens <= 0:
            errors.append("Max Tokens 必须大于 0")
        if not (0.0 <= self.temperature <= 2.0):
            errors.append("Temperature 必须在 0.0 到 2.0 之间")
        return len(errors) == 0, errors
