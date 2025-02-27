"""Tests for the config module."""

import pytest
from licenses_everywhere.config import Config


def test_config_initialization():
    """Test that the config can be initialized."""
    config = Config()
    assert config is not None


def test_config_default_values():
    """Test that the config has default values."""
    config = Config()
    assert config.get("default_license") == "MIT"
    assert config.get("license_filename") == "LICENSE"


def test_config_set_get():
    """Test that values can be set and retrieved."""
    config = Config()
    config.set("test_key", "test_value")
    assert config.get("test_key") == "test_value"


def test_config_update():
    """Test that the config can be updated with a dictionary."""
    config = Config()
    config.update({"test_key1": "test_value1", "test_key2": "test_value2"})
    assert config.get("test_key1") == "test_value1"
    assert config.get("test_key2") == "test_value2"


def test_config_as_dict():
    """Test that the config can be retrieved as a dictionary."""
    config = Config()
    config_dict = config.as_dict
    assert isinstance(config_dict, dict)
    assert "default_license" in config_dict 