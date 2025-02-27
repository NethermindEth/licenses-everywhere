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
import os
import shutil
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Callable
import github
from github import Github
from github.Repository import Repository
from github.Organization import Organization
from .config import config


class AuthProvider:
    """Base class for authentication providers."""
    
    def get_token(self) -> str:
        """
        Get authentication token.
        
        Returns:
            Authentication token as string.
            
        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_token method")
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if this authentication provider is available on the system.
        
        Returns:
            True if available, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement is_available method")


class GhCliAuthProvider(AuthProvider):
    """Authentication provider using GitHub CLI."""
    
    def get_token(self) -> str:
        """
        Get GitHub token from GitHub CLI.
        
        Returns:
            GitHub token as string.
            
        Raises:
            RuntimeError: If token retrieval fails.
        """
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
            
            # Verify the token is valid
            self._verify_token(token)
            
            return token
        except subprocess.CalledProcessError as e:
            if "re-authorize" in e.stderr or "authorization" in e.stderr:
                raise RuntimeError(
                    "GitHub CLI token needs reauthorization. Please run 'gh auth login' to refresh your authentication."
                ) from e
            raise RuntimeError(f"Failed to get GitHub token from gh CLI: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError("GitHub CLI (gh) not found. Please install it or provide a token manually.")
    
    def _verify_token(self, token: str) -> None:
        """
        Verify that the token is valid by making a simple API request.
        
        Args:
            token: GitHub token to verify.
            
        Raises:
            RuntimeError: If the token is invalid.
        """
        try:
            # Use a simple command to verify the token
            result = subprocess.run(
                ["gh", "api", "user"],
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "GH_TOKEN": token}
            )
            
            # If we get here, the token is valid
            return
        except subprocess.CalledProcessError as e:
            if "re-authorize" in e.stderr or "authorization" in e.stderr or "401" in e.stderr:
                raise RuntimeError(
                    "Your GitHub CLI authentication needs to be refreshed. Please run 'gh auth login' to reauthorize."
                ) from e
            elif "403" in e.stderr:
                raise RuntimeError(
                    "Your GitHub token has insufficient permissions. Please run 'gh auth login' with appropriate scopes."
                ) from e
            else:
                raise RuntimeError(f"Failed to verify GitHub token: {e.stderr}") from e
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if GitHub CLI is available.
        
        Returns:
            True if GitHub CLI is available, False otherwise.
        """
        return shutil.which("gh") is not None


class OnePasswordAuthProvider(AuthProvider):
    """Authentication provider using 1Password CLI."""
    
    def __init__(self, item_name: str = "GitHub"):
        """
        Initialize 1Password authentication provider.
        
        Args:
            item_name: Name of the item in 1Password containing the GitHub token.
        """
        self.item_name = item_name
    
    def get_token(self) -> str:
        """
        Get GitHub token from 1Password.
        
        Returns:
            GitHub token as string.
            
        Raises:
            RuntimeError: If token retrieval fails.
        """
        try:
            result = subprocess.run(
                ["op", "item", "get", self.item_name, "--fields", "token"],
                capture_output=True,
                text=True,
                check=True
            )
            token = result.stdout.strip()
            if not token:
                raise ValueError(f"Empty token returned from 1Password for item '{self.item_name}'")
            return token
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get GitHub token from 1Password: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError("1Password CLI (op) not found. Please install it or provide a token manually.")
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if 1Password CLI is available.
        
        Returns:
            True if 1Password CLI is available, False otherwise.
        """
        return shutil.which("op") is not None


class BitwArdenAuthProvider(AuthProvider):
    """Authentication provider using Bitwarden CLI."""
    
    def __init__(self, item_name: str = "GitHub"):
        """
        Initialize Bitwarden authentication provider.
        
        Args:
            item_name: Name of the item in Bitwarden containing the GitHub token.
        """
        self.item_name = item_name
    
    def get_token(self) -> str:
        """
        Get GitHub token from Bitwarden.
        
        Returns:
            GitHub token as string.
            
        Raises:
            RuntimeError: If token retrieval fails.
        """
        try:
            # First check if user is logged in
            status_result = subprocess.run(
                ["bw", "status"],
                capture_output=True,
                text=True,
                check=True
            )
            status = json.loads(status_result.stdout)
            
            if status.get("status") != "unlocked":
                raise RuntimeError("Bitwarden vault is locked. Please unlock it with 'bw unlock'")
            
            # Get the token
            result = subprocess.run(
                ["bw", "get", "password", self.item_name],
                capture_output=True,
                text=True,
                check=True
            )
            token = result.stdout.strip()
            if not token:
                raise ValueError(f"Empty token returned from Bitwarden for item '{self.item_name}'")
            return token
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get GitHub token from Bitwarden: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError("Bitwarden CLI (bw) not found. Please install it or provide a token manually.")
        except json.JSONDecodeError:
            raise RuntimeError("Failed to parse Bitwarden status output")
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if Bitwarden CLI is available.
        
        Returns:
            True if Bitwarden CLI is available, False otherwise.
        """
        return shutil.which("bw") is not None


class EnvVarAuthProvider(AuthProvider):
    """Authentication provider using environment variables."""
    
    def __init__(self, env_var: str = "GITHUB_TOKEN"):
        """
        Initialize environment variable authentication provider.
        
        Args:
            env_var: Name of the environment variable containing the GitHub token.
        """
        self.env_var = env_var
    
    def get_token(self) -> str:
        """
        Get GitHub token from environment variable.
        
        Returns:
            GitHub token as string.
            
        Raises:
            RuntimeError: If token retrieval fails.
        """
        token = os.environ.get(self.env_var)
        if not token:
            raise RuntimeError(f"Environment variable '{self.env_var}' not set or empty")
        return token
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if environment variable is available.
        
        Returns:
            True if environment variable is available, False otherwise.
        """
        return "GITHUB_TOKEN" in os.environ


class DirectTokenAuthProvider(AuthProvider):
    """Authentication provider using a directly provided token."""
    
    def __init__(self, token: str):
        """
        Initialize direct token authentication provider.
        
        Args:
            token: GitHub token.
        """
        self._token = token
    
    def get_token(self) -> str:
        """
        Get GitHub token.
        
        Returns:
            GitHub token as string.
        """
        return self._token
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if direct token is available.
        
        Returns:
            Always returns False as this provider requires a token to be provided.
        """
        return False


class GitHubClient:
    """
    Client for interacting with GitHub API.
    
    This class provides methods to:
    - Authenticate with GitHub (via token or various auth providers)
    - Get organization information
    - List public repositories
    - Check for license files
    - Get repository information
    - Create pull requests
    - Fork repositories when needed
    
    It implements robust error handling and multiple methods for license detection.
    """

    # List of authentication providers to try in order
    AUTH_PROVIDERS = [
        GhCliAuthProvider,
        OnePasswordAuthProvider,
        BitwArdenAuthProvider,
        EnvVarAuthProvider
    ]

    def __init__(self, token: Optional[str] = None, auth_provider: Optional[str] = None, auth_item: Optional[str] = None):
        """
        Initialize the GitHub client.
        
        Args:
            token: GitHub personal access token. If None, will attempt to get from auth providers.
            auth_provider: Name of the authentication provider to use. If None, will try all available providers.
            auth_item: Item name in the credential manager (for 1Password/Bitwarden).
        """
        self._token = token
        if not self._token:
            self._token = self._get_token_from_providers(auth_provider, auth_item)
        self._github = Github(self._token)
        self._username = self._get_authenticated_username()
    
    def _get_token_from_providers(self, provider_name: Optional[str] = None, auth_item: Optional[str] = None) -> str:
        """
        Get GitHub token from available authentication providers.
        
        Args:
            provider_name: Name of the provider to use. If None, will try all available providers.
            auth_item: Item name in the credential manager (for 1Password/Bitwarden).
            
        Returns:
            GitHub token as string.
            
        Raises:
            RuntimeError: If no authentication provider is available or all fail.
        """
        # If a specific provider is requested, try only that one
        if provider_name:
            provider_name = provider_name.lower()
            
            # Special case for 'direct' provider - this means the token was provided directly
            if provider_name == "direct":
                if not self._token:
                    raise RuntimeError("No token provided for direct authentication provider")
                return self._token
            
            # Map provider name to provider class
            provider_map = {
                "gh": GhCliAuthProvider,
                "1password": OnePasswordAuthProvider,
                "bitwarden": BitwArdenAuthProvider,
                "env": EnvVarAuthProvider
            }
            
            if provider_name not in provider_map:
                raise ValueError(f"Unknown authentication provider: {provider_name}")
            
            provider_class = provider_map[provider_name]
            
            # Check if provider is available
            if not provider_class.is_available():
                raise RuntimeError(f"Authentication provider '{provider_name}' is not available")
            
            # Initialize provider with auth_item if needed
            if provider_name in ["1password", "bitwarden"] and auth_item:
                provider = provider_class(auth_item)
            else:
                provider = provider_class()
            
            try:
                return provider.get_token()
            except Exception as e:
                raise RuntimeError(f"Failed to get token from {provider_name}: {str(e)}")
        
        # Try all available providers in order
        errors = []
        
        for provider_class in self.AUTH_PROVIDERS:
            if provider_class.is_available():
                try:
                    # Initialize provider with auth_item if needed
                    if provider_class in [OnePasswordAuthProvider, BitwArdenAuthProvider] and auth_item:
                        provider = provider_class(auth_item)
                    else:
                        provider = provider_class()
                    
                    return provider.get_token()
                except Exception as e:
                    errors.append(f"{provider_class.__name__}: {str(e)}")
        
        # If we get here, all providers failed
        error_msg = "\n".join(errors) if errors else "No authentication providers available"
        raise RuntimeError(f"Failed to authenticate with GitHub: {error_msg}")
    
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
    
    def get_authenticated_username(self) -> str:
        """
        Get the username of the authenticated user.
        
        Returns:
            Username of the authenticated user.
            
        Raises:
            RuntimeError: If getting the username fails.
        """
        return self._username
    
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
        Create a pull request.
        
        This method will try to use the PyGithub library first, and fall back to the GitHub CLI
        if that fails. This ensures that the provided token is used directly when possible.
        
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
        # First try to use PyGithub to create the PR
        try:
            # Parse the repo full name
            owner, repo_name = repo_full_name.split('/')
            
            # Get the repository
            repo = self._github.get_repo(repo_full_name)
            
            # Prepare the head parameter
            head_param = head or branch_name
            
            # Create the pull request
            pr = repo.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=head_param
            )
            
            return {
                "url": pr.html_url,
                "success": True,
                "message": f"Pull request created: {pr.html_url}"
            }
        except Exception as e:
            # Log the error but don't fail yet, try the CLI as fallback
            print(f"Failed to create PR using PyGithub: {str(e)}")
            
            # Fall back to using the GitHub CLI
            try:
                # Prepare the head parameter
                head_param = head or branch_name
                
                # If we have a token, use it with the gh CLI
                env = os.environ.copy()
                if self._token:
                    env["GH_TOKEN"] = self._token
                    
                    # Create a temporary git config to disable credential helper
                    temp_dir = tempfile.mkdtemp(prefix="gh_pr_")
                    temp_gitconfig = os.path.join(temp_dir, "temp_gitconfig")
                    with open(temp_gitconfig, "w") as f:
                        f.write("[credential]\n\thelper=\n")  # Empty helper disables credential storage
                    
                    # Add the config file to environment
                    env["GIT_CONFIG_GLOBAL"] = temp_gitconfig
                
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
                    check=True,
                    env=env
                )
                
                # Clean up temporary directory if created
                if self._token and 'temp_dir' in locals():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Extract PR URL from output
                pr_url = result.stdout.strip()
                
                return {
                    "url": pr_url,
                    "success": True,
                    "message": f"Pull request created: {pr_url}"
                }
            except subprocess.CalledProcessError as e:
                # Clean up temporary directory if created
                if self._token and 'temp_dir' in locals():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                return {
                    "success": False,
                    "message": f"Failed to create PR: {e.stderr}"
                } 