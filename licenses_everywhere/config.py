"""
Configuration manager for License Everywhere.
Handles loading user configuration from files and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager for License Everywhere."""

    DEFAULT_CONFIG = {
        "default_license": "MIT",
        "default_organization": None,
        "copyright_holder": None,
        "temp_dir": None,  # Uses system default if None
        "commit_message": "Add license file",
        "pr_title": "Add license file",
        "pr_body": "This PR adds a license file to the repository.",
        "license_filename": "LICENSE",
        "use_ssh": True,  # Default to using SSH for Git operations
    }

    def __init__(self):
        self._config = self.DEFAULT_CONFIG.copy()
        self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        config_paths = [
            Path.home() / ".licenses-everywhere.yaml",
            Path.home() / ".licenses-everywhere.yml",
            Path.cwd() / ".licenses-everywhere.yaml",
            Path.cwd() / ".licenses-everywhere.yml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        file_config = yaml.safe_load(f)
                        if file_config and isinstance(file_config, dict):
                            self._config.update(file_config)
                except (yaml.YAMLError, IOError) as e:
                    print(f"Warning: Could not load config from {config_path}: {e}")

        # Override with environment variables if set
        env_prefix = "LICENSES_EVERYWHERE_"
        for key in self._config:
            env_key = f"{env_prefix}{key.upper()}"
            if env_key in os.environ:
                self._config[key] = os.environ[env_key]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config[key] = value

    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration with values from a dictionary."""
        self._config.update(config_dict)

    @property
    def as_dict(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self._config.copy()


# Global configuration instance
config = Config() 