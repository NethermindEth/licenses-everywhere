"""
Tests for the repository handler module.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from licenses_everywhere.repo_handler import RepoHandler


@pytest.fixture
def repo_handler():
    """Create a repository handler for testing."""
    return RepoHandler(temp_dir=tempfile.gettempdir())


@patch("subprocess.run")
def test_verify_github_auth_success(mock_run, repo_handler):
    """Test successful GitHub authentication verification."""
    # Mock successful authentication
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Logged in to github.com as username"
    mock_run.return_value = mock_process
    
    # Verify authentication
    is_authenticated, message = repo_handler.verify_github_auth()
    
    # Check results
    assert is_authenticated is True
    assert "verified successfully" in message
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_verify_github_auth_failure(mock_run, repo_handler):
    """Test failed GitHub authentication verification."""
    # Mock failed authentication
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stderr = "You are not logged in to github.com"
    mock_run.return_value = mock_process
    
    # Verify authentication
    is_authenticated, message = repo_handler.verify_github_auth()
    
    # Check results
    assert is_authenticated is False
    assert "GitHub authentication issue" in message
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_verify_github_auth_cli_not_found(mock_run, repo_handler):
    """Test GitHub CLI not found."""
    # Mock FileNotFoundError
    mock_run.side_effect = FileNotFoundError("No such file or directory: 'gh'")
    
    # Verify authentication
    is_authenticated, message = repo_handler.verify_github_auth()
    
    # Check results
    assert is_authenticated is False
    assert "GitHub CLI (gh) not found" in message
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_get_auth_help_message_oauth(mock_run, repo_handler):
    """Test getting help message for OAuth re-authorization."""
    error_message = "remote: To access this repository, you must re-authorize the OAuth Application 'Visual Studio Code'."
    help_message = repo_handler._get_auth_help_message(error_message)
    
    assert "re-authorize the OAuth Application" in help_message
    assert "gh auth login" in help_message


@patch("subprocess.run")
def test_get_auth_help_message_403(mock_run, repo_handler):
    """Test getting help message for 403 error."""
    error_message = "The requested URL returned error: 403"
    help_message = repo_handler._get_auth_help_message(error_message)
    
    assert "Access forbidden (403)" in help_message
    assert "run 'gh auth login'" in help_message


@patch("subprocess.run")
def test_clone_repo_auth_error(mock_run, repo_handler):
    """Test handling authentication error during repository cloning."""
    # Mock authentication error during clone
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stderr = "The requested URL returned error: 403"
    mock_run.return_value = mock_process
    
    # Attempt to clone repository
    with pytest.raises(RuntimeError) as excinfo:
        repo_handler.clone_repo("https://github.com/org/repo.git", "repo")
    
    # Check error message
    assert "GitHub authentication error" in str(excinfo.value)
    assert "Access forbidden (403)" in str(excinfo.value)
    mock_run.assert_called_once() 