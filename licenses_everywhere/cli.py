"""
Command-line interface for License Everywhere.
"""

import sys
import click
from rich.console import Console
from .core import LicenseEverywhere
from .config import config
from . import __version__


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
@click.option("--token", "-t", help="GitHub personal access token (uses gh CLI auth if not provided)")
@click.option("--repos", "-r", help="Comma-separated list of specific repositories to check (e.g., 'repo1,repo2')")
@click.option("--allow-skip", "-s", is_flag=True, help="Allow skipping license selection for repositories")
def scan(org, license, copyright, dry_run, token, repos, allow_skip):
    """Scan repositories and add licenses where missing."""
    console = Console()
    
    try:
        # Initialize License Everywhere
        license_everywhere = LicenseEverywhere(token=token, org_name=org)
        
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


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main() 