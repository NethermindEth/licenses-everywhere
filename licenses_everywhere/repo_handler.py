"""
Repository handler for License Everywhere.
Handles cloning, modifying, and creating pull requests for repositories.
"""

import os
import tempfile
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import shutil
from .config import config


class RepoHandler:
    """Handler for repository operations."""

    def __init__(self, temp_dir: Optional[str] = None, github_client=None, use_ssh: bool = False):
        """
        Initialize the repository handler.
        
        Args:
            temp_dir: Directory to use for temporary clones. If None, uses system default.
            github_client: GitHubClient instance to use for authentication.
            use_ssh: If True, use SSH for Git operations instead of HTTPS.
        """
        self._temp_dir = temp_dir or config.get("temp_dir")
        self._github_client = github_client
        self._use_ssh = use_ssh
    
    def verify_github_auth(self) -> Tuple[bool, str]:
        """
        Verify GitHub authentication status.
        
        Returns:
            Tuple of (is_authenticated, message)
        """
        # If we have a GitHub client, use it to verify authentication
        if self._github_client:
            try:
                # Try to get the authenticated user
                username = self._github_client.get_authenticated_username()
                if username:
                    return True, f"Authenticated as {username}"
                else:
                    return False, "Failed to get authenticated user"
            except Exception as e:
                return False, f"GitHub authentication issue: {str(e)}"
        
        # Fallback to gh CLI check if no GitHub client
        try:
            # Check if gh CLI is authenticated
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False  # Don't raise an exception if command fails
            )
            
            if result.returncode == 0:
                return True, "GitHub authentication verified successfully"
            else:
                # Extract the error message
                return False, f"GitHub authentication issue: {result.stderr.strip()}"
        except FileNotFoundError:
            return False, "GitHub CLI (gh) not found. Please install it or provide a token manually."
    
    def clone_repo(self, repo_url: str, repo_name: str) -> str:
        """
        Clone a repository to a temporary directory.
        
        Args:
            repo_url: URL of the repository to clone.
            repo_name: Name of the repository.
            
        Returns:
            Path to the cloned repository.
            
        Raises:
            RuntimeError: If cloning fails.
        """
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"{repo_name}_", dir=self._temp_dir)
        
        try:
            # If using SSH, convert the URL to SSH format
            if self._use_ssh:
                # Convert HTTPS URL to SSH URL
                # From: https://github.com/owner/repo.git
                # To:   git@github.com:owner/repo.git
                if repo_url.startswith("https://github.com/"):
                    repo_path = repo_url.replace("https://github.com/", "")
                    if repo_path.endswith(".git"):
                        repo_path = repo_path[:-4]
                    repo_url = f"git@github.com:{repo_path}.git"
            
            # If we have a GitHub client with a token, set up git credentials
            if not self._use_ssh and self._github_client and hasattr(self._github_client, '_token') and self._github_client._token:
                # Set up environment with the token
                env = os.environ.copy()
                env["GIT_ASKPASS"] = "echo"
                env["GIT_USERNAME"] = "x-access-token"
                env["GIT_PASSWORD"] = self._github_client._token
                
                # Disable credential helper to prevent keychain access
                # First create a temporary git config
                temp_gitconfig = os.path.join(temp_dir, "temp_gitconfig")
                with open(temp_gitconfig, "w") as f:
                    f.write("[credential]\n\thelper=\n")  # Empty helper disables credential storage
                
                # Clone the repository using the environment variables for auth and custom config
                result = subprocess.run(
                    ["git", "-c", f"include.path={temp_gitconfig}", "clone", repo_url, temp_dir],
                    capture_output=True,
                    text=True,
                    check=False,  # Handle errors manually for better messages
                    env=env
                )
            else:
                # No token available or using SSH, use normal clone
                result = subprocess.run(
                    ["git", "clone", repo_url, temp_dir],
                    capture_output=True,
                    text=True,
                    check=False  # Handle errors manually for better messages
                )
            
            if result.returncode != 0:
                # Clean up on failure
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Check for authentication errors
                if "403" in result.stderr or "Authentication failed" in result.stderr:
                    auth_message = self._get_auth_help_message(result.stderr)
                    raise RuntimeError(f"GitHub authentication error: {auth_message}")
                else:
                    raise RuntimeError(f"Failed to clone repository: {result.stderr}")
            
            return temp_dir
        except Exception as e:
            # Clean up on any exception
            shutil.rmtree(temp_dir, ignore_errors=True)
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Failed to clone repository: {str(e)}") from e
    
    def _get_auth_help_message(self, error_message: str) -> str:
        """
        Extract helpful authentication error messages.
        
        Args:
            error_message: The error message from git or GitHub.
            
        Returns:
            A user-friendly help message.
        """
        # Check for common authentication issues
        if "re-authorize the OAuth Application" in error_message:
            return (
                "You need to re-authorize the OAuth Application. "
                "Please visit GitHub and approve the authorization request, "
                "or use one of the available authentication providers."
            )
        elif "The requested URL returned error: 403" in error_message:
            return (
                "Access forbidden (403). This could be due to: "
                "1. Expired credentials - try reauthenticating "
                "2. Insufficient permissions for this repository "
                "3. Repository access restrictions"
            )
        elif "The requested URL returned error: 401" in error_message:
            return "Authentication failed. Please check your credentials or try a different authentication provider."
        else:
            return (
                f"{error_message}\n"
                "To fix authentication issues, try:\n"
                "1. Use a different authentication provider\n"
                "2. Check your token permissions and expiration\n"
                "3. Verify you have access to the repository"
            )
    
    def add_license_file(self, repo_path: str, license_content: str, 
                         filename: str = "LICENSE") -> str:
        """
        Add a license file to a repository.
        
        Args:
            repo_path: Path to the repository.
            license_content: Content of the license file.
            filename: Name of the license file.
            
        Returns:
            Path to the license file.
            
        Raises:
            IOError: If writing the file fails.
        """
        license_path = os.path.join(repo_path, filename)
        
        with open(license_path, "w") as f:
            f.write(license_content)
        
        return license_path
    
    def create_branch(self, repo_path: str, branch_name: str) -> None:
        """
        Create a new branch in a repository.
        
        Args:
            repo_path: Path to the repository.
            branch_name: Name of the branch to create.
            
        Raises:
            RuntimeError: If branch creation fails.
        """
        try:
            # Create and checkout a new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create branch: {e.stderr}") from e
    
    def commit_changes(self, repo_path: str, message: str) -> None:
        """
        Commit changes to a repository.
        
        Args:
            repo_path: Path to the repository.
            message: Commit message.
            
        Raises:
            RuntimeError: If committing fails.
        """
        try:
            # Add all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to commit changes: {e.stderr}") from e
    
    def push_changes(self, repo_path: str, branch_name: str) -> None:
        """
        Push changes to a remote repository.
        
        Args:
            repo_path: Path to the repository.
            branch_name: Name of the branch to push.
            
        Raises:
            RuntimeError: If pushing fails.
        """
        try:
            # Set up environment with the token if available
            env = os.environ.copy()
            git_cmd = ["git", "push", "origin", branch_name]
            
            # Only use token authentication if not using SSH
            if not self._use_ssh and self._github_client and hasattr(self._github_client, '_token') and self._github_client._token:
                env["GIT_ASKPASS"] = "echo"
                env["GIT_USERNAME"] = "x-access-token"
                env["GIT_PASSWORD"] = self._github_client._token
                
                # Disable credential helper to prevent keychain access
                git_cmd = ["git", "-c", "credential.helper=", "push", "origin", branch_name]
            
            # Push changes
            result = subprocess.run(
                git_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,  # Handle errors manually for better messages
                env=env
            )
            
            if result.returncode != 0:
                # Check for authentication errors
                if "403" in result.stderr or "Authentication failed" in result.stderr:
                    auth_message = self._get_auth_help_message(result.stderr)
                    raise RuntimeError(f"GitHub authentication error: {auth_message}")
                else:
                    raise RuntimeError(f"Failed to push changes: {result.stderr}")
                
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Failed to push changes: {str(e)}") from e
    
    def cleanup(self, repo_path: str) -> None:
        """
        Clean up a temporary repository.
        
        Args:
            repo_path: Path to the repository.
        """
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True) 