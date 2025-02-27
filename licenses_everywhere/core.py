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

    def __init__(self, token: Optional[str] = None, org_name: Optional[str] = None, 
                 auth_provider: Optional[str] = None, auth_item: Optional[str] = None,
                 use_ssh: Optional[bool] = None):
        """
        Initialize License Everywhere.
        
        Args:
            token: GitHub personal access token. If None, will attempt to get from auth providers.
            org_name: GitHub organization name. If None, will use from config or prompt.
            auth_provider: Authentication provider to use ('gh', '1password', 'bitwarden', 'env').
            auth_item: Item name in the credential manager (for 1Password/Bitwarden).
            use_ssh: If True, use SSH for Git operations instead of HTTPS. Defaults to config setting.
        """
        self.console = Console()
        self.github_client = GitHubClient(token, auth_provider, auth_item)
        self.license_manager = LicenseManager()
        # Use the provided value or fall back to the config setting
        use_ssh = use_ssh if use_ssh is not None else config.get("use_ssh", True)
        self.repo_handler = RepoHandler(github_client=self.github_client, use_ssh=use_ssh)
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
            
            # Provide specific guidance based on the error
            if "re-authorize" in auth_message or "reauthorize" in auth_message:
                self.console.print("\n[bold yellow]To fix this issue:[/bold yellow]")
                self.console.print("1. Run [bold]gh auth login[/bold] to refresh your GitHub CLI authentication")
                self.console.print("2. Follow the prompts to authenticate with GitHub")
                self.console.print("3. Run this command again")
                
                if not Confirm.ask("Continue anyway?", default=False):
                    return {"success": False, "message": "Authentication failed. Operation aborted."}
            else:
                self.console.print("[yellow]Please authenticate with GitHub before proceeding.[/yellow]")
                self.console.print("Use one of the available authentication providers or provide a token directly.")
                
                if not Confirm.ask("Continue anyway?", default=False):
                    return {"success": False, "message": "Authentication failed. Operation aborted."}
            
            self.console.print("[yellow]Continuing without authentication verification. This may cause errors later.[/yellow]")
        elif is_authenticated:
            self.console.print(f"[bold green]Authentication:[/bold green] {auth_message}")
        
        # Get repositories
        try:
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
        except Exception as e:
            error_msg = str(e)
            self.console.print(f"[bold red]Error fetching repositories:[/bold red] {error_msg}")
            
            # Check for authentication-related errors
            if "auth" in error_msg.lower() or "token" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                self.console.print("\n[bold yellow]This appears to be an authentication issue.[/bold yellow]")
                self.console.print("Please ensure you have valid GitHub authentication:")
                self.console.print("1. Run [bold]gh auth login[/bold] if using GitHub CLI")
                self.console.print("2. Or provide a valid token with [bold]--token YOUR_TOKEN[/bold]")
                self.console.print("3. Run [bold]licenses-everywhere auth-providers[/bold] to see all options")
            
            return {"success": False, "message": f"Failed to fetch repositories: {error_msg}"}
        
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
            branch_name = f"chore/add-{license_type.lower()}-license"
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

    def verify_company_name(self, org_name: Optional[str] = None, expected_name: str = "",
                           dry_run: bool = False, specific_repos: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Verify company names in license files and update them if needed.
        
        Args:
            org_name: GitHub organization name.
            expected_name: Expected company name.
            dry_run: If True, don't make any changes, just show what would be done.
            specific_repos: List of specific repositories to check.
            
        Returns:
            Dictionary with results.
        """
        if not expected_name:
            self.console.print("[bold red]Error:[/bold red] Expected company name is required.")
            return {"success": False, "message": "Expected company name is required"}
        
        # Use the provided org name or the one from initialization
        org_name = org_name or self.org_name
        
        if not org_name:
            self.console.print("[bold red]Error:[/bold red] Organization name is required.")
            return {"success": False, "message": "Organization name is required"}
        
        # Verify GitHub authentication
        auth_status, auth_message = self.repo_handler.verify_github_auth()
        if not auth_status:
            self.console.print(f"[bold red]Authentication Error:[/bold red] {auth_message}")
            return {"success": False, "message": auth_message}
        
        self.console.print(f"[green]{auth_message}[/green]")
        
        # Get organization
        try:
            org = self.github_client.get_organization(org_name)
        except Exception as e:
            self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return {"success": False, "message": str(e)}
        
        # Get repositories
        try:
            if specific_repos:
                repos = []
                for repo_name in specific_repos:
                    try:
                        # Handle both "org/repo" and "repo" formats
                        if "/" in repo_name:
                            full_name = repo_name
                        else:
                            full_name = f"{org_name}/{repo_name}"
                        
                        repo = self.github_client._github.get_repo(full_name)
                        repos.append(repo)
                    except Exception as e:
                        self.console.print(f"[bold red]Error getting repository {repo_name}:[/bold red] {str(e)}")
            else:
                repos = self.github_client.get_public_repos(org_name)
        except Exception as e:
            self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return {"success": False, "message": str(e)}
        
        self.console.print(f"Found [bold]{len(repos)}[/bold] repositories in {org_name}")
        
        # Track results
        results = {
            "total_repos": len(repos),
            "repos_with_license": 0,
            "repos_with_incorrect_name": 0,
            "repos_updated": 0,
            "repos_skipped": 0,
            "repos_with_errors": 0,
            "details": []
        }
        
        # Process each repository
        for repo in repos:
            self.console.print(f"\nChecking [bold]{repo.full_name}[/bold]...")
            
            # Check if repository has a license
            has_license = self.github_client.has_license(repo)
            
            if not has_license:
                self.console.print("  [yellow]No license file found[/yellow]")
                results["repos_skipped"] += 1
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "skipped",
                    "reason": "No license file found"
                })
                continue
            
            results["repos_with_license"] += 1
            
            # Get license content
            license_content = self.github_client.get_license_content(repo)
            if not license_content:
                self.console.print("  [yellow]Could not read license content[/yellow]")
                results["repos_skipped"] += 1
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "skipped",
                    "reason": "Could not read license content"
                })
                continue
            
            # Check if company name is correct
            is_correct = self.license_manager.verify_company_name(license_content, expected_name)
            
            if is_correct:
                self.console.print("  [green]Company name is correct[/green]")
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "correct",
                    "reason": "Company name is already correct"
                })
                continue
            
            results["repos_with_incorrect_name"] += 1
            
            # Detect the license type
            license_type = self.license_manager.detect_license_type(license_content)
            if not license_type:
                self.console.print("  [yellow]Could not detect license type[/yellow]")
                results["repos_skipped"] += 1
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "skipped",
                    "reason": "Could not detect license type"
                })
                continue
            
            self.console.print(f"  [yellow]Company name is incorrect in {license_type} license[/yellow]")
            
            # Extract the current company name from the license
            # This is a simplified approach and might need to be refined
            copyright_line = None
            for line in license_content.splitlines():
                if "copyright" in line.lower() or "©" in line.lower():
                    copyright_line = line
                    break
            
            if not copyright_line:
                self.console.print("  [yellow]Could not find copyright line[/yellow]")
                results["repos_skipped"] += 1
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "skipped",
                    "reason": "Could not find copyright line"
                })
                continue
            
            # Extract the current company name
            # This is a simplified approach and might need to be refined
            import re
            year_pattern = r"\d{4}"
            years = re.findall(year_pattern, copyright_line)
            
            if not years:
                self.console.print("  [yellow]Could not extract year from copyright line[/yellow]")
                results["repos_skipped"] += 1
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "skipped",
                    "reason": "Could not extract year from copyright line"
                })
                continue
            
            # Get the text after the year
            year = years[-1]  # Use the last year if multiple years are present
            current_name = copyright_line.split(year, 1)[1].strip()
            
            # Remove common prefixes
            for prefix in ["©", "Copyright", "copyright", "(c)", "(C)"]:
                if current_name.startswith(prefix):
                    current_name = current_name[len(prefix):].strip()
            
            # Remove leading punctuation
            current_name = current_name.lstrip(" ,;:-")
            
            self.console.print(f"  Current name: [yellow]{current_name}[/yellow]")
            self.console.print(f"  Expected name: [green]{expected_name}[/green]")
            
            if dry_run:
                self.console.print("  [yellow]Dry run mode - no changes will be made[/yellow]")
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "would_update",
                    "reason": "Company name is incorrect",
                    "current_name": current_name,
                    "expected_name": expected_name,
                    "license_type": license_type
                })
                continue
            
            # Update the license
            try:
                # Process the repository
                result = self._update_license(repo, license_content, current_name, expected_name, license_type)
                
                if result.get("success", False):
                    results["repos_updated"] += 1
                    self.console.print(f"  [bold green]Success![/bold green] {result['message']}")
                else:
                    results["repos_with_errors"] += 1
                    self.console.print(f"  [bold red]Error:[/bold red] {result['message']}")
                
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "updated" if result.get("success", False) else "error",
                    "reason": result["message"],
                    "current_name": current_name,
                    "expected_name": expected_name,
                    "license_type": license_type,
                    "pr_url": result.get("pr_url")
                })
            except Exception as e:
                results["repos_with_errors"] += 1
                self.console.print(f"  [bold red]Error:[/bold red] {str(e)}")
                results["details"].append({
                    "repo": repo.full_name,
                    "status": "error",
                    "reason": str(e),
                    "current_name": current_name,
                    "expected_name": expected_name,
                    "license_type": license_type
                })
        
        # Print summary
        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"Total repositories: {results['total_repos']}")
        self.console.print(f"Repositories with license: {results['repos_with_license']}")
        self.console.print(f"Repositories with incorrect company name: {results['repos_with_incorrect_name']}")
        self.console.print(f"Repositories updated: {results['repos_updated']}")
        self.console.print(f"Repositories skipped: {results['repos_skipped']}")
        self.console.print(f"Repositories with errors: {results['repos_with_errors']}")
        
        return {
            "success": True,
            "message": "Company name verification completed",
            "results": results
        }
    
    def _update_license(self, repo, license_content: str, current_name: str, 
                       expected_name: str, license_type: str) -> Dict[str, Any]:
        """
        Update the license file in a repository.
        
        Args:
            repo: Repository object.
            license_content: Current license content.
            current_name: Current company name.
            expected_name: Expected company name.
            license_type: License type.
            
        Returns:
            Dictionary with results.
        """
        # Get repository info
        repo_info = self.github_client.get_repo_info(repo)
        
        # Check if user has write access to the repository
        has_write_access = repo_info.get("has_write_access", False)
        
        # If user doesn't have write access, fork the repository
        forked_repo = None
        if not has_write_access:
            self.console.print("  [yellow]You don't have write access to this repository. Forking it to your account...[/yellow]")
            with self.console.status("  Forking repository..."):
                forked_repo = self.github_client.fork_repository(repo)
            self.console.print(f"  [green]Repository forked successfully: {forked_repo.full_name}[/green]")
            
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
        with self.console.status(f"  Cloning repository {repo_name}..."):
            repo_path = self.repo_handler.clone_repo(clone_url, repo_name)
        
        # Create branch
        branch_name = f"chore/update-{license_type.lower()}-license-company-name"
        with self.console.status(f"  Creating branch {branch_name}..."):
            self.repo_handler.create_branch(repo_path, branch_name)
        
        # Update license content
        updated_license = self.license_manager.update_company_name(license_content, current_name, expected_name)
        
        # Update license file
        try:
            with self.console.status("  Updating license file..."):
                license_path = self.repo_handler.update_license_file(
                    repo_path, 
                    updated_license, 
                    "LICENSE"  # Try with default name first
                )
        except FileNotFoundError:
            # If LICENSE file not found, try with other common names
            for filename in ["LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md", "COPYING.txt"]:
                try:
                    license_path = self.repo_handler.update_license_file(
                        repo_path, 
                        updated_license, 
                        filename
                    )
                    break
                except FileNotFoundError:
                    continue
            else:
                return {
                    "success": False,
                    "message": "Could not find license file to update"
                }
        
        # Commit changes
        commit_message = f"Update company name in {license_type} license"
        with self.console.status("  Committing changes..."):
            self.repo_handler.commit_changes(repo_path, commit_message)
        
        # Push changes
        with self.console.status("  Pushing changes..."):
            self.repo_handler.push_changes(repo_path, branch_name)
        
        # Create pull request
        pr_title = f"Update company name in {license_type} license"
        pr_body = f"This PR updates the company name in the {license_type} license from '{current_name}' to '{expected_name}'."
        
        with self.console.status("  Creating pull request..."):
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
            return {
                "success": True,
                "message": pr_result['message'],
                "pr_url": pr_result.get('url'),
                "license_type": license_type,
                "forked": forked_repo is not None
            }
        else:
            return {
                "success": False,
                "message": pr_result['message'],
                "license_type": license_type,
                "forked": forked_repo is not None
            } 