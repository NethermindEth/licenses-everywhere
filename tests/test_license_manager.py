"""Tests for the license manager module."""

import pytest
from licenses_everywhere.license_manager import LicenseManager


def test_license_manager_initialization():
    """Test that the license manager can be initialized."""
    license_manager = LicenseManager()
    assert license_manager is not None


def test_get_available_licenses():
    """Test that the license manager returns available licenses."""
    license_manager = LicenseManager()
    licenses = license_manager.get_available_licenses()
    assert isinstance(licenses, list)
    assert len(licenses) > 0
    assert "MIT" in licenses


def test_get_license_content():
    """Test that the license manager can get license content."""
    license_manager = LicenseManager()
    content = license_manager.get_license_content("MIT", {"copyright_holder": "Test Company"})
    assert isinstance(content, str)
    assert "Test Company" in content
    assert "MIT License" in content


def test_get_license_info():
    """Test that the license manager can get license info."""
    license_manager = LicenseManager()
    info = license_manager.get_license_info("MIT")
    assert isinstance(info, dict)
    assert info["name"] == "MIT"
    assert "description" in info 