"""
Command-line interface for License Everywhere.
"""

import sys
import click
from rich.console import Console
from .core import LicenseEverywhere
from .config import config
from . import __version__
import subprocess


@click.group()
@click.version_option(version=__version__)
def cli():
    """License Everywhere - Ensure all repositories have proper license files."""
    pass


@cli.command()
@click.option("--org", "-o", help="GitHub organization name")
@click.option("--license", "-l", help="Default license type to use")
@click.option("--copyright", "-c", help="Copyright holder name")
@click.option("--dry-run", "-d", is_flag=True, help="Don't make any changes, just show what would be done")
@click.option("--token", "-t", help="GitHub personal access token (uses auth providers if not provided)")
@click.option("--auth-provider", "-a", 
              type=click.Choice(["gh", "1password", "bitwarden", "env", "direct"], case_sensitive=False),
              help="Authentication provider to use for GitHub token. Note: 'gh' uses GitHub CLI's built-in authentication (which may use system keychain), while '1password' gets the token directly from 1Password CLI.")
@click.option("--auth-item", help="Item name in the credential manager (for 1Password/Bitwarden)")
@click.option("--repos", "-r", help="Comma-separated list of specific repositories to check (e.g., 'repo1,repo2')")
@click.option("--allow-skip", "-s", is_flag=True, help="Allow skipping license selection for repositories")
@click.option("--use-ssh/--no-ssh", default=None, help="Use SSH for Git operations (default: enabled). Use --no-ssh to disable and use HTTPS instead.")
def scan(org, license, copyright, dry_run, token, auth_provider, auth_item, repos, allow_skip, use_ssh):
    """Scan repositories and add licenses where missing."""
    console = Console()
    
    try:
        # If auth_provider is 'direct' but no token is provided, prompt for it
        if auth_provider == "direct" and not token:
            token = click.prompt("Enter GitHub token", hide_input=True)
        
        # Initialize License Everywhere
        try:
            license_everywhere = LicenseEverywhere(
                token=token, 
                org_name=org,
                auth_provider=auth_provider,
                auth_item=auth_item,
                use_ssh=use_ssh
            )
        except RuntimeError as e:
            # Handle authentication errors with more helpful messages
            error_msg = str(e)
            console.print(f"[bold red]Authentication Error:[/bold red] {error_msg}")
            
            # Provide specific guidance based on the error
            if "re-authorize" in error_msg or "reauthorize" in error_msg:
                console.print("\n[bold yellow]To fix this issue:[/bold yellow]")
                console.print("1. Run [bold]gh auth login[/bold] to refresh your GitHub CLI authentication")
                console.print("2. Follow the prompts to authenticate with GitHub")
                console.print("3. Run this command again")
            elif "provider" in error_msg.lower() and "not available" in error_msg.lower():
                console.print("\n[bold yellow]The specified authentication provider is not available.[/bold yellow]")
                
                if "1password" in error_msg.lower():
                    console.print("1Password CLI is not installed or not properly configured.")
                    console.print("To install 1Password CLI:")
                    console.print("  - Mac: [bold]brew install 1password-cli[/bold]")
                    console.print("  - Other: Visit https://1password.com/downloads/command-line/")
                    console.print("\nAlternatively, you can use a direct token:")
                    console.print("1. Create a token at https://github.com/settings/tokens")
                    console.print("2. Run with: [bold]--auth-provider direct --token YOUR_TOKEN[/bold]")
                elif "bitwarden" in error_msg.lower():
                    console.print("Bitwarden CLI is not installed or not properly configured.")
                    console.print("To install Bitwarden CLI: [bold]npm install -g @bitwarden/cli[/bold]")
                    console.print("\nAlternatively, you can use a direct token:")
                    console.print("1. Create a token at https://github.com/settings/tokens")
                    console.print("2. Run with: [bold]--auth-provider direct --token YOUR_TOKEN[/bold]")
                elif "gh" in error_msg.lower():
                    console.print("GitHub CLI is not installed or not properly configured.")
                    console.print("To install GitHub CLI:")
                    console.print("  - Mac: [bold]brew install gh[/bold]")
                    console.print("  - Other: Visit https://cli.github.com/")
                    console.print("\nAlternatively, you can use a direct token:")
                    console.print("1. Create a token at https://github.com/settings/tokens")
                    console.print("2. Run with: [bold]--auth-provider direct --token YOUR_TOKEN[/bold]")
                
                console.print("\nRun [bold]licenses-everywhere auth-providers[/bold] to see available authentication options")
            elif "token" in error_msg.lower() and "not found" in error_msg.lower():
                console.print("\n[bold yellow]To fix this issue:[/bold yellow]")
                console.print("1. Provide a token directly with [bold]--token YOUR_TOKEN[/bold]")
                console.print("2. Or set up one of the authentication providers:")
                console.print("   - GitHub CLI: Install and run [bold]gh auth login[/bold]")
                console.print("   - Environment: Set [bold]export GITHUB_TOKEN=your_token[/bold]")
                console.print("   - 1Password/Bitwarden: Install the CLI and store your token")
            
            console.print("\nRun [bold]licenses-everywhere auth-providers[/bold] to see available authentication options")
            sys.exit(1)
        
        # Parse specific repositories if provided
        specific_repos = None
        if repos:
            specific_repos = [repo.strip() for repo in repos.split(",")]
            console.print(f"Checking specific repositories: [bold]{', '.join(specific_repos)}[/bold]")
        
        # Run the workflow
        result = license_everywhere.run(
            org_name=org,
            license_type=license,
            copyright_holder=copyright,
            dry_run=dry_run,
            specific_repos=specific_repos,
            allow_skip=allow_skip
        )
        
        if result.get("success", False):
            sys.exit(0)
        else:
            console.print(f"[bold red]Error:[/bold red] {result.get('message', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
def licenses():
    """List available license types."""
    from .license_manager import LicenseManager
    
    console = Console()
    license_manager = LicenseManager()
    
    console.print("[bold]Available license types:[/bold]")
    
    for license_type in license_manager.get_available_licenses():
        license_info = license_manager.get_license_info(license_type)
        console.print(f"[bold]{license_type}[/bold]: {license_info['description']}")


@cli.command()
def auth_providers():
    """List available authentication providers."""
    from .github_client import GitHubClient
    
    console = Console()
    
    console.print("[bold]Available authentication providers:[/bold]")
    
    for provider_class in GitHubClient.AUTH_PROVIDERS:
        is_available = provider_class.is_available()
        status = "[green]Available[/green]" if is_available else "[red]Not available[/red]"
        console.print(f"[bold]{provider_class.__name__}[/bold]: {status}")
        
        # Add provider-specific instructions
        if provider_class.__name__ == "GhCliAuthProvider":
            if is_available:
                console.print("  Use with: [bold]--auth-provider gh[/bold]")
                console.print("  Requires GitHub CLI to be installed and authenticated.")
                console.print("  Run 'gh auth login' to authenticate.")
                console.print("  [yellow]Note:[/yellow] GitHub CLI may use your system keychain (macOS Keychain on Mac)")
                console.print("  To check where GitHub CLI stores credentials: [bold]gh auth status[/bold]")
            else:
                console.print("  GitHub CLI not found. Install with 'brew install gh' or visit https://cli.github.com/")
        
        elif provider_class.__name__ == "OnePasswordAuthProvider":
            if is_available:
                console.print("  Use with: [bold]--auth-provider 1password --auth-item ITEM_NAME[/bold]")
                console.print("  Requires 1Password CLI to be installed and authenticated.")
                console.print("  ITEM_NAME is the name of the item in 1Password containing the GitHub token.")
                console.print("  The token should be stored in a field named 'token'.")
                console.print("  [yellow]Note:[/yellow] This gets the token directly from 1Password, not through GitHub CLI")
                console.print("  To create a token: Visit https://github.com/settings/tokens and add it to 1Password")
            else:
                console.print("  1Password CLI not found. Install with 'brew install 1password-cli' or visit https://1password.com/downloads/command-line/")
                console.print("  After installation, run 'op signin' to set up the 1Password CLI")
        
        elif provider_class.__name__ == "BitwArdenAuthProvider":
            if is_available:
                console.print("  Use with: [bold]--auth-provider bitwarden --auth-item ITEM_NAME[/bold]")
                console.print("  Requires Bitwarden CLI to be installed and authenticated.")
                console.print("  ITEM_NAME is the name of the item in Bitwarden containing the GitHub token.")
                console.print("  The vault must be unlocked with 'bw unlock' before use.")
            else:
                console.print("  Bitwarden CLI not found. Install with 'npm install -g @bitwarden/cli' or visit https://bitwarden.com/help/cli/")
        
        elif provider_class.__name__ == "EnvVarAuthProvider":
            if is_available:
                console.print("  Use with: [bold]--auth-provider env[/bold]")
                console.print("  Requires GITHUB_TOKEN environment variable to be set.")
                console.print("  Set with 'export GITHUB_TOKEN=your_token' in your shell.")
            else:
                console.print("  GITHUB_TOKEN environment variable not set.")
                console.print("  To set: 'export GITHUB_TOKEN=your_token' (create token at https://github.com/settings/tokens)")
    
    # Add information about the direct provider
    console.print("\n[bold]Direct Token Provider[/bold]: [green]Always Available[/green]")
    console.print("  Use with: [bold]--auth-provider direct --token YOUR_TOKEN[/bold]")
    console.print("  Directly uses the token provided on the command line.")
    console.print("  If no token is provided, you will be prompted to enter one.")
    console.print("  To create a token: Visit https://github.com/settings/tokens")
    console.print("  [yellow]Note:[/yellow] This is the most reliable method but requires manual token management.")
    
    console.print("\n[bold yellow]To use 1Password instead of system keychain:[/bold yellow]")
    console.print("1. Create a GitHub token at https://github.com/settings/tokens")
    console.print("2. Save it in 1Password with a field named 'token'")
    console.print("3. Run with: [bold]--auth-provider 1password --auth-item \"Your Item Name\"[/bold]")


@cli.command()
@click.option("--auth-provider", "-a", 
              type=click.Choice(["gh", "1password", "bitwarden", "env", "direct"], case_sensitive=False),
              help="Authentication provider to check")
@click.option("--auth-item", help="Item name in the credential manager (for 1Password/Bitwarden)")
@click.option("--token", "-t", help="GitHub token (required for direct provider)")
@click.option("--use-ssh/--no-ssh", default=None, help="Check SSH authentication (default: enabled). Use --no-ssh to check HTTPS authentication instead.")
def auth_status(auth_provider, auth_item, token, use_ssh):
    """Check the current authentication status."""
    from .github_client import GitHubClient
    from .repo_handler import RepoHandler
    
    console = Console()
    
    try:
        # If using SSH, check SSH authentication
        if use_ssh is None:
            # Use the default from config
            use_ssh = config.get("use_ssh", True)
            
        if use_ssh:
            console.print("[bold]Checking SSH authentication with GitHub...[/bold]")
            
            # Test SSH connection to GitHub
            result = subprocess.run(
                ["ssh", "-T", "git@github.com"],
                capture_output=True,
                text=True,
                check=False  # Don't raise an exception if command fails
            )
            
            # GitHub's SSH server always returns exit code 1 even when authentication succeeds
            # It will contain "Hi username!" in the output if successful
            if "Hi " in result.stderr and "You've successfully authenticated" in result.stderr:
                # Extract username from the message
                username = result.stderr.split("Hi ")[1].split("!")[0]
                console.print(f"[bold green]SSH Authentication:[/bold green] Successful as [bold]{username}[/bold]")
                console.print("You can use [bold]--use-ssh[/bold] with scan commands to use SSH for Git operations")
                return
            else:
                console.print("[bold red]SSH Authentication Failed[/bold red]")
                console.print(f"Error: {result.stderr.strip()}")
                console.print("\n[bold yellow]To set up SSH authentication with GitHub:[/bold yellow]")
                console.print("1. Generate an SSH key: [bold]ssh-keygen -t ed25519 -C \"your_email@example.com\"[/bold]")
                console.print("2. Start the SSH agent: [bold]eval \"$(ssh-agent -s)\"[/bold]")
                console.print("3. Add your key: [bold]ssh-add ~/.ssh/id_ed25519[/bold]")
                console.print("4. Add the key to GitHub: https://github.com/settings/keys")
                console.print("5. Test with: [bold]ssh -T git@github.com[/bold]")
                return
        
        # If auth_provider is 'direct' but no token is provided, prompt for it
        if auth_provider == "direct" and not token:
            token = click.prompt("Enter GitHub token", hide_input=True)
        
        # Initialize GitHub client with specified provider
        github_client = GitHubClient(
            token=token,
            auth_provider=auth_provider,
            auth_item=auth_item
        )
        
        # Create repo handler
        repo_handler = RepoHandler(github_client=github_client, use_ssh=use_ssh)
        
        # Check authentication status
        is_authenticated, auth_message = repo_handler.verify_github_auth()
        
        if is_authenticated:
            console.print(f"[bold green]Authentication Status:[/bold green] {auth_message}")
            
            # Show additional information
            console.print("\n[bold]GitHub User Information:[/bold]")
            username = github_client.get_authenticated_username()
            console.print(f"Username: [bold]{username}[/bold]")
            
            # Show which provider was used
            if auth_provider:
                console.print(f"Using authentication provider: [bold]{auth_provider}[/bold]")
                
                # Show provider-specific information
                if auth_provider == "direct":
                    console.print("Using directly provided token")
                elif auth_provider == "1password" and auth_item:
                    console.print(f"Using 1Password item: [bold]{auth_item}[/bold]")
                elif auth_provider == "bitwarden" and auth_item:
                    console.print(f"Using Bitwarden item: [bold]{auth_item}[/bold]")
            else:
                console.print("Using default authentication provider chain")
            
            # If using GitHub CLI, show more details
            if auth_provider == "gh" or (not auth_provider and github_client._token):
                console.print("\n[bold]GitHub CLI Status:[/bold]")
                try:
                    result = subprocess.run(
                        ["gh", "auth", "status"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split("\n"):
                            console.print(f"  {line}")
                    else:
                        console.print(f"  [yellow]GitHub CLI status check failed:[/yellow] {result.stderr.strip()}")
                except Exception as e:
                    console.print(f"  [yellow]Failed to check GitHub CLI status:[/yellow] {str(e)}")
        else:
            console.print(f"[bold red]Authentication Failed:[/bold red] {auth_message}")
            
            # Provide guidance based on the error
            if "re-authorize" in auth_message or "reauthorize" in auth_message:
                console.print("\n[bold yellow]To fix this issue:[/bold yellow]")
                console.print("1. Run [bold]gh auth login[/bold] to refresh your GitHub CLI authentication")
                console.print("2. Follow the prompts to authenticate with GitHub")
                console.print("3. Run this command again")
            
            console.print("\nRun [bold]licenses-everywhere auth-providers[/bold] to see available authentication options")
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        
        # Provide guidance based on the error
        if "provider" in str(e).lower() and "not available" in str(e).lower():
            console.print("\n[bold yellow]The specified authentication provider is not available.[/bold yellow]")
            console.print("Run [bold]licenses-everywhere auth-providers[/bold] to see available providers")
            
            # Suggest direct token as an alternative
            console.print("\nAlternatively, you can use a direct token:")
            console.print("1. Create a token at https://github.com/settings/tokens")
            console.print("2. Run with: [bold]--auth-provider direct --token YOUR_TOKEN[/bold]")
        elif "token" in str(e).lower():
            console.print("\n[bold yellow]Authentication token issue:[/bold yellow]")
            console.print("1. Check if your token is valid and has the necessary permissions")
            console.print("2. For GitHub CLI: Run [bold]gh auth login[/bold] to refresh your authentication")
            console.print("3. For 1Password/Bitwarden: Ensure the token is stored correctly")
            console.print("4. For environment variables: Check if GITHUB_TOKEN is set correctly")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main() 