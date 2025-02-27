# License Everywhere - System Architecture

## Overview

License Everywhere is a command-line tool designed to ensure that all public repositories in a GitHub organization have proper license files. The tool identifies repositories without licenses, adds appropriate license files based on configuration, and creates pull requests for the changes.

## Project Structure

```
licenses-everywhere/
├── LICENSE                 # Project license file
├── README.md               # Project documentation
├── ARCHITECTURE.md         # This architecture document
├── pyproject.toml          # Poetry configuration
├── poetry.lock             # Poetry lock file
├── licenses_everywhere/    # Main package
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── core.py             # Core functionality
│   ├── github_client.py    # GitHub API client
│   ├── license_manager.py  # License template management
│   ├── repo_handler.py     # Repository operations
│   └── templates/          # License templates
│       ├── apache-2.0.txt  # Apache 2.0 license template
│       └── mit.txt         # MIT license template
└── tests/                  # Test directory
    ├── __init__.py         # Test package initialization
    ├── conftest.py         # Pytest configuration
    ├── test_config.py      # Tests for config module
    └── test_license_manager.py # Tests for license manager
```

## Component Architecture

### Core Components

1. **LicenseEverywhere** (`core.py`): The main orchestrator class that coordinates the workflow between other components.

2. **GitHubClient** (`github_client.py`): Handles interactions with the GitHub API, including:
   - Fetching repositories
   - Checking for license files
   - Creating pull requests
   - Forking repositories
   - Authentication with multiple providers

3. **LicenseManager** (`license_manager.py`): Manages license templates and generation, including:
   - Loading license templates
   - Generating license content with proper placeholders
   - Providing license metadata

4. **RepoHandler** (`repo_handler.py`): Handles Git operations, including:
   - Cloning repositories
   - Creating branches
   - Adding license files
   - Committing and pushing changes
   - Authentication verification

5. **CLI** (`cli.py`): Provides the command-line interface using Click.

### Authentication System

The authentication system is designed to be flexible, secure, and user-friendly:

1. **Multiple Authentication Providers**:
   - We implemented a plugin-based authentication system with a common interface
   - Each provider implements the `AuthProvider` base class
   - Providers are tried in a priority order until one succeeds
   - Users can specify which provider to use via the CLI

2. **Authentication Provider Implementation**:
   - **GitHub CLI** (`GhCliAuthProvider`): Uses the GitHub CLI's authentication, which is secure and handles token refresh automatically
   - **1Password** (`OnePasswordAuthProvider`): Retrieves tokens from 1Password, allowing secure storage of tokens
   - **Bitwarden** (`BitwArdenAuthProvider`): Retrieves tokens from Bitwarden, providing an open-source alternative
   - **Environment Variables** (`EnvVarAuthProvider`): Uses the `GITHUB_TOKEN` environment variable for CI/CD pipelines
   - **Direct Token** (`DirectTokenAuthProvider`): Allows providing a token directly via the CLI

3. **Provider Selection Logic**:
   - If a specific provider is requested, only that one is tried
   - If no provider is specified, all available providers are tried in order
   - Providers check their own availability before attempting to retrieve a token
   - Detailed error messages are provided if authentication fails

4. **Security Considerations**:
   - Tokens are never stored by the application
   - Integration with secure credential managers (1Password, Bitwarden) keeps tokens secure
   - GitHub CLI integration leverages its secure token storage and refresh mechanisms

## Data Flow

1. **User Input**: The user provides input via the CLI, including:
   - Organization name
   - License type preference
   - Authentication provider preference
   - Other options

2. **Repository Discovery**: The GitHubClient fetches repositories from the specified organization.

3. **License Check**: Each repository is checked for an existing license file.

4. **License Selection**: For repositories without licenses, the user selects a license type.

5. **Repository Processing**:
   - The repository is cloned
   - A new branch is created
   - The license file is added
   - Changes are committed and pushed

6. **Pull Request Creation**: A pull request is created to add the license file.

7. **Result Reporting**: Results are reported back to the user.

## Technical Decisions

### GitHub API Access
- Uses PyGithub library for API interactions
- Falls back to GitHub CLI for authentication if token not provided
- Implements robust error handling for API calls, particularly for license detection
- Uses multiple methods to detect licenses (API-reported licenses and file-based detection)

### Repository Forking

For repositories where the user doesn't have write access:

1. The system automatically forks the repository to the user's account
2. Changes are made in the forked repository
3. A pull request is created from the fork to the original repository

This approach follows GitHub's best practices for contributions and allows users to contribute to repositories they don't directly own.

### License Template Management

License templates are stored as Jinja2 templates with placeholders for:

1. Copyright holder name
2. Current year
3. Project-specific information

This allows for flexible and customizable license generation while maintaining compliance with standard license formats.

### Repository Operations
- Non-destructive approach using pull requests
- Respects repository settings and branch protection rules
- Handles various edge cases (forks, archived repositories, etc.)

### Configuration
- Uses a combination of command-line arguments and configuration file
- Supports organization-wide default license type
- Allows per-repository overrides

### CLI Interface

- Provides a user-friendly command-line interface
- Supports both basic and advanced usage patterns
- Allows targeting specific repositories with the `--repos` option
- Enables skipping repositories during the workflow with the `--allow-skip` option
- Provides clear feedback and progress indicators

### GitHub Authentication

- Verifies authentication status before performing operations
- Provides clear error messages for authentication failures
- Supports multiple authentication methods:
  - GitHub CLI (gh) for seamless authentication
  - Personal access tokens for direct API access
- Implements robust error handling for authentication issues
- Detects and provides guidance for common authentication problems:
  - Expired tokens
  - OAuth application re-authorization
  - Permission issues
  - Repository access restrictions

## License Detection and Handling

The GitHub client implements a robust approach to license detection:
1. First attempts to use the GitHub API's `get_license()` method with proper error handling
2. Falls back to checking for common license filenames if the API method fails
3. Safely extracts license information for reporting purposes

This multi-layered approach ensures reliable license detection even when the GitHub API response structure changes or when repositories have non-standard license files.

## Repository Access and Forking Workflow

The system implements a sophisticated workflow for handling repositories with different access levels:

1. For each repository, the system checks if the authenticated user has write access
2. If the user has write access:
   - The repository is cloned directly
   - Changes are made on a new branch prefixed with `chore/` (e.g., `chore/add-mit-license`)
   - A pull request is created within the same repository
3. If the user doesn't have write access:
   - The system checks if the user has already forked the repository
   - If a fork exists, it is used; otherwise, a new fork is created
   - Changes are made on a new branch in the forked repository prefixed with `chore/`
   - A pull request is created from the user's fork to the original repository

This approach ensures that the tool can work with any repository, regardless of the user's access level, while following GitHub's best practices for contributions.

## Future Enhancements

1. **Additional Authentication Providers**:
   - Support for other credential managers (LastPass, KeePass, etc.)
   - Support for OAuth web flow authentication
   - Support for GitHub App authentication

2. **Enhanced License Management**:
   - Support for custom license templates
   - License compliance checking
   - License compatibility analysis

3. **Improved Repository Handling**:
   - Batch processing of repositories
   - Scheduled scanning for new repositories
   - Integration with CI/CD pipelines

## Current Features

1. **License Addition**: Adds license files to repositories that don't have them.

2. **Company Name Verification**: 
   - Scans all repositories to ensure the company name in license files is correct
   - Identifies licenses with incorrect or outdated company names
   - Creates pull requests to update license files with the correct company name
   - Supports all license types managed by the system
   - Provides reporting on which repositories needed updates

## Dependencies

- PyGithub: GitHub API client
- Click: Command-line interface
- Jinja2: Template rendering
- PyYAML: Configuration file parsing

## Requirements

- Python 3.8.1+
- GitHub CLI (gh) for authentication (optional)
- GitHub Personal Access Token (if not using GitHub CLI) 