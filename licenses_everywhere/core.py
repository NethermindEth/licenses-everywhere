"""
Core module for License Everywhere.
Orchestrates the workflow between other components.
"""

import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from github.Repository import Repository
from .config import config
from .github_client import GitHubClient
from .license_manager import LicenseManager
from .repo_handler import RepoHandler


class LicenseEverywhere:
    """Main class for License Everywhere."""

    def __init__(self, token: Optional[str] = None, org_name: Optional[str] = None):
        """
        Initialize License Everywhere.
        
        Args:
            token: GitHub personal access token. If None, will attempt to get from gh CLI.
            org_name: GitHub organization name. If None, will use from config or prompt.
        """
        self.console = Console()
        self.github_client = GitHubClient(token)
        self.license_manager = LicenseManager()
        self.repo_handler = RepoHandler()
        self.org_name = org_name or config.get("default_organization")
    
    def run(self, org_name: Optional[str] = None, license_type: Optional[str] = None,
            copyright_holder: Optional[str] = None, dry_run: bool = False,
            specific_repos: Optional[List[str]] = None, allow_skip: bool = False) -> Dict[str, Any]:
        """
        Run the License Everywhere workflow.
        
        Args:
            org_name: GitHub organization name. Overrides the one set in __init__.
            license_type: Default license type to use.
            copyright_holder: Copyright holder name.
            dry_run: If True, don't make any changes.
            specific_repos: List of specific repository names to check. If provided, only these repos will be checked.
            allow_skip: If True, allows skipping license selection for repositories.
            
        Returns:
            Dictionary with results.
        """
        # Use provided org_name or the one set in __init__
        org_name = org_name or self.org_name
        
        # If still no org_name, prompt for it
        if not org_name:
            org_name = Prompt.ask("Enter GitHub organization name")
        
        # Set copyright holder if provided
        if copyright_holder:
            config.set("copyright_holder", copyright_holder)
        
        # If no copyright holder in config, prompt for it
        if not config.get("copyright_holder"):
            copyright_holder = Prompt.ask("Enter copyright holder name (e.g., 'Your Company, Inc.')")
            config.set("copyright_holder", copyright_holder)
        
        # Verify GitHub authentication before proceeding
        self.console.print("Verifying GitHub authentication...")
        is_authenticated, auth_message = self.repo_handler.verify_github_auth()
        
        if not is_authenticated and not dry_run:
            self.console.print(f"[bold red]Authentication Error:[/bold red] {auth_message}")
            self.console.print("[yellow]Please authenticate with GitHub before proceeding.[/yellow]")
            self.console.print("Run 'gh auth login' to authenticate with GitHub CLI.")
            
            if not Confirm.ask("Continue anyway?", default=False):
                return {"success": False, "message": "Authentication failed. Operation aborted."}
            
            self.console.print("[yellow]Continuing without authentication verification. This may cause errors later.[/yellow]")
        elif is_authenticated:
            self.console.print(f"[bold green]Authentication:[/bold green] {auth_message}")
        
        # Get repositories
        self.console.print(f"Fetching repositories for organization: [bold]{org_name}[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Fetching repositories...", total=None)
            all_repos = self.github_client.get_public_repos(org_name)
            progress.update(task, total=len(all_repos), completed=len(all_repos))
        
        # Filter repositories if specific ones are requested
        if specific_repos:
            repos = [repo for repo in all_repos if repo.name in specific_repos]
            if len(repos) < len(specific_repos):
                found_repos = [repo.name for repo in repos]
                missing_repos = [name for name in specific_repos if name not in found_repos]
                self.console.print(f"[bold yellow]Warning:[/bold yellow] Could not find the following repositories: {', '.join(missing_repos)}")
        else:
            repos = all_repos
        
        # Filter out repositories that already have licenses
        repos_without_license = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Checking for licenses...", total=len(repos))
            
            for repo in repos:
                progress.update(task, advance=1, description=f"Checking {repo.name}...")
                if not self.github_client.has_license(repo):
                    repos_without_license.append(repo)
        
        # Print summary
        self.console.print(f"\nFound [bold]{len(repos)}[/bold] public repositories.")
        self.console.print(f"[bold]{len(repos_without_license)}[/bold] repositories don't have a license.")
        
        if not repos_without_license:
            self.console.print("[bold green]All repositories have licenses! Nothing to do.[/bold green]")
            return {"success": True, "message": "All repositories have licenses"}
        
        # Process repositories without licenses
        results = []
        
        for repo in repos_without_license:
            result = self._process_repo(repo, license_type, dry_run, allow_skip)
            results.append(result)
            
            # Add a small delay between repositories to avoid rate limiting
            time.sleep(1)
        
        # Print final summary
        successful = sum(1 for r in results if r.get("success", False))
        skipped = sum(1 for r in results if r.get("message") == "Skipped by user")
        
        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"- Total repositories checked: [bold]{len(repos)}[/bold]")
        self.console.print(f"- Repositories without license: [bold]{len(repos_without_license)}[/bold]")
        self.console.print(f"- Licenses added: [bold]{successful}[/bold]")
        if skipped > 0:
            self.console.print(f"- Repositories skipped: [bold]{skipped}[/bold]")
        
        return {
            "success": True,
            "total_repos": len(repos),
            "repos_without_license": len(repos_without_license),
            "licenses_added": successful,
            "skipped": skipped,
            "results": results
        }
    
    def _process_repo(self, repo: Repository, default_license_type: Optional[str] = None,
                     dry_run: bool = False, allow_skip: bool = False) -> Dict[str, Any]:
        """
        Process a single repository.
        
        Args:
            repo: Repository object.
            default_license_type: Default license type to use.
            dry_run: If True, don't make any changes.
            allow_skip: If True, allows skipping license selection for the repository.
            
        Returns:
            Dictionary with result information.
        """
        self.console.print(f"\nProcessing repository: [bold]{repo.full_name}[/bold]")
        
        # Get repository info
        repo_info = self.github_client.get_repo_info(repo)
        
        # Select license type
        available_licenses = self.license_manager.get_available_licenses()
        default_license = default_license_type or config.get("default_license", "MIT")
        
        if default_license not in available_licenses:
            default_license = "MIT"
        
        # Add skip option if allowed
        choices = available_licenses.copy()
        if allow_skip:
            choices.append("skip")
            self.console.print("[italic]You can type 'skip' to skip this repository[/italic]")
        
        license_type = Prompt.ask(
            "Select license type",
            choices=choices,
            default=default_license
        )
        
        # Handle skip option
        if license_type.lower() == "skip":
            self.console.print("[yellow]Skipping this repository[/yellow]")
            return {
                "repo": repo.full_name,
                "success": False,
                "message": "Skipped by user"
            }
        
        # Get license info
        license_info = self.license_manager.get_license_info(license_type)
        self.console.print(f"Selected license: [bold]{license_info['name']}[/bold] - {license_info['description']}")
        
        # Confirm action
        if not Confirm.ask("Add this license to the repository?", default=True):
            return {
                "repo": repo.full_name,
                "success": False,
                "message": "Skipped by user"
            }
        
        if dry_run:
            self.console.print("[yellow]Dry run mode - no changes will be made[/yellow]")
            return {
                "repo": repo.full_name,
                "success": True,
                "message": "Would add license (dry run)",
                "license": license_type
            }
        
        try:
            # Check if user has write access to the repository
            has_write_access = repo_info.get("has_write_access", False)
            
            # If user doesn't have write access, fork the repository
            forked_repo = None
            if not has_write_access:
                self.console.print("[yellow]You don't have write access to this repository. Forking it to your account...[/yellow]")
                with self.console.status("Forking repository..."):
                    forked_repo = self.github_client.fork_repository(repo)
                self.console.print(f"[green]Repository forked successfully: {forked_repo.full_name}[/green]")
                
                # Use the forked repository URL for cloning
                clone_url = forked_repo.clone_url
                repo_name = forked_repo.name
                original_repo_full_name = repo.full_name
            else:
                # Use the original repository URL for cloning
                clone_url = repo.clone_url
                repo_name = repo.name
                original_repo_full_name = repo.full_name
            
            # Clone repository
            with self.console.status(f"Cloning repository {repo_name}..."):
                repo_path = self.repo_handler.clone_repo(clone_url, repo_name)
            
            # Create branch
            branch_name = f"add-{license_type.lower()}-license"
            with self.console.status(f"Creating branch {branch_name}..."):
                self.repo_handler.create_branch(repo_path, branch_name)
            
            # Generate license content
            license_content = self.license_manager.get_license_content(license_type)
            
            # Add license file
            with self.console.status("Adding license file..."):
                license_path = self.repo_handler.add_license_file(
                    repo_path, 
                    license_content, 
                    config.get("license_filename", "LICENSE")
                )
            
            # Commit changes
            commit_message = config.get("commit_message", "Add license file")
            with self.console.status("Committing changes..."):
                self.repo_handler.commit_changes(repo_path, commit_message)
            
            # Push changes
            with self.console.status("Pushing changes..."):
                self.repo_handler.push_changes(repo_path, branch_name)
            
            # Create pull request
            pr_title = config.get("pr_title", "Add license file")
            pr_body = config.get("pr_body", f"This PR adds a {license_type} license file to the repository.")
            
            with self.console.status("Creating pull request..."):
                # If we're working with a fork, we need to specify the head branch differently
                if forked_repo:
                    # Format: username:branch_name
                    head = f"{self.github_client._username}:{branch_name}"
                    pr_result = self.github_client.create_pull_request(
                        original_repo_full_name,  # PR to the original repo
                        branch_name,
                        pr_title,
                        pr_body,
                        repo.default_branch,
                        head=head  # Specify the head branch with username
                    )
                else:
                    # Regular PR within the same repo
                    pr_result = self.github_client.create_pull_request(
                        original_repo_full_name,
                        branch_name,
                        pr_title,
                        pr_body,
                        repo.default_branch
                    )
            
            # Clean up
            self.repo_handler.cleanup(repo_path)
            
            if pr_result.get("success", False):
                self.console.print(f"[bold green]Success![/bold green] {pr_result['message']}")
                return {
                    "repo": repo.full_name,
                    "success": True,
                    "message": pr_result['message'],
                    "pr_url": pr_result.get('url'),
                    "license": license_type,
                    "forked": forked_repo is not None
                }
            else:
                self.console.print(f"[bold red]Error creating PR:[/bold red] {pr_result['message']}")
                return {
                    "repo": repo.full_name,
                    "success": False,
                    "message": pr_result['message'],
                    "license": license_type,
                    "forked": forked_repo is not None
                }
                
        except Exception as e:
            self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return {
                "repo": repo.full_name,
                "success": False,
                "message": str(e),
                "license": license_type
            } 