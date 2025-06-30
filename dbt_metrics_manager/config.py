"""Application configuration."""

import os
from pathlib import Path
from typing import Dict, Any
import json

from .utils.constants import DEFAULT_CONFIG


class Config:
    """Application configuration management."""
    
    def __init__(self):
        self.app_dir = Path.home() / ".dbt-metrics-manager"
        self.config_file = self.app_dir / "config.json"
        self.db_file = self.app_dir / "app.db"
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    user_settings = json.load(f)
                return {**DEFAULT_CONFIG, **user_settings}
            except Exception:
                # Fall back to defaults if config is corrupted
                pass
        
        return DEFAULT_CONFIG.copy()
    
    def save_settings(self) -> None:
        """Save current settings to config file."""
        self.app_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get configuration value by dot notation key."""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value):
        """Set configuration value by dot notation key."""
        keys = key.split('.')
        target = self.settings
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value


_config_instance = None


def get_config() -> Config:
    """Get global config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance