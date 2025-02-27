"""
Tests for the core module.
"""

import pytest
from unittest.mock import MagicMock, patch
from licenses_everywhere.core import LicenseEverywhere


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    mock = MagicMock()
    
    # Create mock repositories
    repo1 = MagicMock()
    repo1.name = "repo1"
    repo1.full_name = "org/repo1"
    repo1.clone_url = "https://github.com/org/repo1.git"
    repo1.default_branch = "main"
    
    repo2 = MagicMock()
    repo2.name = "repo2"
    repo2.full_name = "org/repo2"
    repo2.clone_url = "https://github.com/org/repo2.git"
    repo2.default_branch = "main"
    
    repo3 = MagicMock()
    repo3.name = "repo3"
    repo3.full_name = "org/repo3"
    repo3.clone_url = "https://github.com/org/repo3.git"
    repo3.default_branch = "main"
    
    # Set up mock methods
    mock.get_public_repos.return_value = [repo1, repo2, repo3]
    
    # repo1 and repo3 don't have licenses, repo2 does
    mock.has_license.side_effect = lambda repo: repo.name == "repo2"
    
    # Mock get_repo_info
    mock.get_repo_info.return_value = {
        "name": "test-repo",
        "full_name": "org/test-repo",
        "description": "Test repository",
        "url": "https://github.com/org/test-repo",
        "default_branch": "main",
        "has_license": False,
        "license": None,
        "private": False,
        "fork": False,
        "archived": False,
        "disabled": False,
        "has_write_access": True,
    }
    
    # Mock username
    mock._username = "test-user"
    
    # Mock get_authenticated_username
    mock.get_authenticated_username.return_value = "test-user"
    
    return mock


@pytest.fixture
def mock_license_manager():
    """Create a mock license manager."""
    mock = MagicMock()
    mock.get_available_licenses.return_value = ["MIT", "Apache-2.0"]
    mock.get_license_info.return_value = {
        "name": "MIT License",
        "description": "A permissive license"
    }
    mock.get_license_content.return_value = "MIT License Content"
    return mock


@pytest.fixture
def mock_repo_handler():
    """Create a mock repository handler."""
    mock = MagicMock()
    mock.clone_repo.return_value = "/tmp/repo"
    mock.verify_github_auth.return_value = (True, "GitHub authentication verified successfully")
    return mock


@patch("licenses_everywhere.core.GitHubClient")
@patch("licenses_everywhere.core.Prompt")
@patch("licenses_everywhere.core.Confirm")
@patch("licenses_everywhere.core.Progress")
def test_specific_repos(mock_progress, mock_confirm, mock_prompt, mock_github_client_class, mock_github_client, mock_license_manager, mock_repo_handler):
    """Test specifying specific repositories."""
    # Set up mocks
    mock_prompt.ask.return_value = "MIT"
    mock_confirm.ask.return_value = True
    
    # Mock Progress context manager
    progress_instance = MagicMock()
    mock_progress.return_value.__enter__.return_value = progress_instance
    progress_instance.add_task.return_value = 1
    
    # Set up GitHubClient mock
    mock_github_client_class.return_value = mock_github_client
    
    # Create LicenseEverywhere instance with mocks
    license_everywhere = LicenseEverywhere()
    license_everywhere.license_manager = mock_license_manager
    license_everywhere.repo_handler = mock_repo_handler
    license_everywhere.console = MagicMock()
    
    # Mock _process_repo to avoid complex mocking
    license_everywhere._process_repo = MagicMock()
    license_everywhere._process_repo.return_value = {
        "repo": "org/repo1",
        "success": True,
        "message": "License added",
        "license": "MIT"
    }
    
    # Run with specific repos
    result = license_everywhere.run(
        org_name="org",
        specific_repos=["repo1", "repo3"]
    )
    
    # Verify results
    assert result["success"] is True
    
    # Verify that _process_repo was called for both repo1 and repo3
    assert license_everywhere._process_repo.call_count == 2


@patch("licenses_everywhere.core.GitHubClient")
@patch("licenses_everywhere.core.Prompt")
@patch("licenses_everywhere.core.Confirm")
@patch("licenses_everywhere.core.Progress")
def test_allow_skip(mock_progress, mock_confirm, mock_prompt, mock_github_client_class, mock_github_client, mock_license_manager, mock_repo_handler):
    """Test skipping license selection."""
    # Set up mocks
    mock_prompt.ask.side_effect = ["skip", "MIT"]
    mock_confirm.ask.return_value = True
    
    # Mock Progress context manager
    progress_instance = MagicMock()
    mock_progress.return_value.__enter__.return_value = progress_instance
    progress_instance.add_task.return_value = 1
    
    # Set up GitHubClient mock
    mock_github_client_class.return_value = mock_github_client
    
    # Create LicenseEverywhere instance with mocks
    license_everywhere = LicenseEverywhere()
    license_everywhere.license_manager = mock_license_manager
    license_everywhere.repo_handler = mock_repo_handler
    license_everywhere.console = MagicMock()
    
    # Mock _process_repo to return different results for each call
    license_everywhere._process_repo = MagicMock()
    license_everywhere._process_repo.side_effect = [
        {
            "repo": "org/repo1",
            "success": False,
            "message": "Skipped by user"
        },
        {
            "repo": "org/repo3",
            "success": True,
            "message": "License added",
            "license": "MIT"
        }
    ]
    
    # Run with allow_skip enabled
    result = license_everywhere.run(
        org_name="org",
        allow_skip=True
    )
    
    # Verify results
    assert result["success"] is True
    assert license_everywhere._process_repo.call_count == 2
    
    # Verify that allow_skip was passed to _process_repo
    call_args = license_everywhere._process_repo.call_args_list[0]
    # Check if allow_skip was passed as a positional or keyword argument
    # The call signature is _process_repo(repo, default_license_type, dry_run, allow_skip)
    # So allow_skip should be the 4th positional argument or a keyword argument
    if len(call_args[0]) >= 4:  # If passed as positional argument
        assert call_args[0][3] is True
    else:  # If passed as keyword argument
        assert call_args[1].get("allow_skip") is True 