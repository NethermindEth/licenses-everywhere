"""
GitHub API client for License Everywhere.
Handles interactions with the GitHub API.

This module provides a client for interacting with the GitHub API,
with specific functionality for checking and retrieving license information
from repositories. It implements robust error handling and multiple methods
for license detection to ensure reliability.
"""

import subprocess
import json
from typing import List, Dict, Any, Optional, Tuple
import github
from github import Github
from github.Repository import Repository
from github.Organization import Organization
from .config import config


class GitHubClient:
    """
    Client for interacting with GitHub API.
    
    This class provides methods to:
    - Authenticate with GitHub (via token or gh CLI)
    - Get organization information
    - List public repositories
    - Check for license files
    - Get repository information
    - Create pull requests
    - Fork repositories when needed
    
    It implements robust error handling and multiple methods for license detection.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub client.
        
        Args:
            token: GitHub personal access token. If None, will attempt to get from gh CLI.
        """
        self._token = token or self._get_token_from_gh_cli()
        self._github = Github(self._token)
        self._username = self._get_authenticated_username()
    
    def _get_token_from_gh_cli(self) -> str:
        """Get GitHub token from gh CLI."""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True
            )
            token = result.stdout.strip()
            if not token:
                raise ValueError("Empty token returned from gh CLI")
            return token
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get GitHub token from gh CLI: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError("GitHub CLI (gh) not found. Please install it or provide a token manually.")
    
    def _get_authenticated_username(self) -> str:
        """Get the username of the authenticated user."""
        try:
            # Get the authenticated user
            user = self._github.get_user()
            return user.login
        except github.GithubException as e:
            raise RuntimeError(f"Failed to get authenticated user: {e.data.get('message', str(e))}") from e
    
    def get_organization(self, org_name: str) -> Organization:
        """
        Get a GitHub organization by name.
        
        Args:
            org_name: Name of the organization.
            
        Returns:
            Organization object.
            
        Raises:
            github.UnknownObjectException: If the organization doesn't exist.
        """
        return self._github.get_organization(org_name)
    
    def get_public_repos(self, org_name: str) -> List[Repository]:
        """
        Get all public repositories for an organization.
        
        Args:
            org_name: Name of the organization.
            
        Returns:
            List of Repository objects.
        """
        org = self.get_organization(org_name)
        return list(org.get_repos(type="public"))
    
    def has_license(self, repo: Repository) -> bool:
        """
        Check if a repository has a license file.
        
        This method uses multiple approaches to detect licenses:
        1. First tries to use the GitHub API's get_license() method
        2. If that fails, checks for common license filenames
        
        This multi-layered approach ensures reliable license detection even when
        the GitHub API response structure changes or when repositories have
        non-standard license files.
        
        Args:
            repo: Repository object to check.
            
        Returns:
            True if the repository has a license, False otherwise.
        """
        # First check if GitHub API reports a license
        try:
            # Use get_license() method instead of license attribute
            license_content = repo.get_license()
            if license_content:
                return True
        except (github.GithubException, AttributeError):
            # Continue to check for license files if get_license() fails
            pass
        
        # Also check for common license filenames
        license_filenames = [
            "LICENSE", "LICENSE.md", "LICENSE.txt", 
            "COPYING", "COPYING.md", "COPYING.txt"
        ]
        
        for filename in license_filenames:
            try:
                repo.get_contents(filename)
                return True
            except github.GithubException:
                continue
        
        return False
    
    def get_repo_info(self, repo: Repository) -> Dict[str, Any]:
        """
        Get information about a repository.
        
        This method safely extracts license information using error handling
        to prevent attribute errors when the license structure changes.
        
        Args:
            repo: Repository object.
            
        Returns:
            Dictionary with repository information.
        """
        # Get license info safely
        license_info = None
        try:
            license_content = repo.get_license()
            if license_content and hasattr(license_content, 'license'):
                license_info = license_content.license
        except (github.GithubException, AttributeError):
            pass
        
        # Safely get attributes that might not exist in all PyGithub versions
        is_disabled = False
        try:
            is_disabled = repo.disabled
        except AttributeError:
            # The 'disabled' attribute might not exist in all PyGithub versions
            pass
            
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "url": repo.html_url,
            "default_branch": repo.default_branch,
            "has_license": self.has_license(repo),
            "license": license_info,
            "private": repo.private,
            "fork": repo.fork,
            "archived": repo.archived,
            "disabled": is_disabled,
            "has_write_access": self.has_write_access(repo),
        }
    
    def has_write_access(self, repo: Repository) -> bool:
        """
        Check if the authenticated user has write access to the repository.
        
        Args:
            repo: Repository object.
            
        Returns:
            True if the user has write access, False otherwise.
        """
        try:
            # Try to get the permissions for the authenticated user
            permissions = repo.permissions
            return permissions.push if permissions else False
        except (github.GithubException, AttributeError):
            # If we can't get permissions, assume no write access
            return False
    
    def fork_repository(self, repo: Repository) -> Repository:
        """
        Fork a repository to the authenticated user's account.
        
        Args:
            repo: Repository object to fork.
            
        Returns:
            The forked repository object.
            
        Raises:
            RuntimeError: If forking fails.
        """
        try:
            # Check if the repository is already forked by the user
            user = self._github.get_user()
            user_repos = list(user.get_repos())
            
            # Look for an existing fork
            for user_repo in user_repos:
                if user_repo.fork and user_repo.parent and user_repo.parent.full_name == repo.full_name:
                    return user_repo
            
            # If no existing fork is found, create a new one
            forked_repo = repo.create_fork()
            return forked_repo
        except github.GithubException as e:
            raise RuntimeError(f"Failed to fork repository: {e.data.get('message', str(e))}") from e
    
    def create_pull_request(self, repo_full_name: str, branch_name: str, 
                           title: str, body: str, base_branch: str = "main",
                           head: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a pull request using gh CLI.
        
        Args:
            repo_full_name: Full name of the repository (owner/repo).
            branch_name: Name of the branch to create PR from.
            title: PR title.
            body: PR description.
            base_branch: Base branch to create PR against.
            head: Head branch in format username:branch_name for cross-repo PRs.
                  If None, uses branch_name from the same repo.
            
        Returns:
            Dictionary with PR information.
        """
        try:
            # Prepare the head parameter
            head_param = head or branch_name
            
            cmd = [
                "gh", "pr", "create",
                "--repo", repo_full_name,
                "--head", head_param,
                "--base", base_branch,
                "--title", title,
                "--body", body
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Extract PR URL from output
            pr_url = result.stdout.strip()
            
            return {
                "url": pr_url,
                "success": True,
                "message": f"Pull request created: {pr_url}"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": f"Failed to create PR: {e.stderr}"
            } 