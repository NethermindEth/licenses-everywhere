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

The system is composed of the following components:

1. **CLI Interface** (`cli.py`): Handles command-line arguments and user interaction.
2. **Core Module** (`core.py`): Orchestrates the overall process and workflow.
3. **GitHub API Client** (`github_client.py`): Manages interactions with the GitHub API.
4. **License Manager** (`license_manager.py`): Handles license template management.
5. **Repository Handler** (`repo_handler.py`): Manages repository operations.
6. **Configuration Manager** (`config.py`): Manages user configuration.

## Data Flow

1. User invokes the CLI with organization name and options (including specific repositories if desired)
2. CLI parses arguments and passes them to the Core module
3. Core module initializes the GitHub client and Repository handler
4. **Authentication verification is performed to ensure GitHub access**
5. GitHub client fetches all public repositories for the organization (or filters to specific repositories if requested)
6. Repository handler identifies repositories without licenses
7. License manager provides appropriate license templates
8. For each repository without a license:
   - User can select a license type or skip the repository (if --allow-skip is enabled)
   - **System checks if the user has write access to the repository**
   - **If the user doesn't have write access, the repository is forked to the user's account**
   - Repository handler creates branches, adds license files, and creates pull requests
9. Results are reported back to the user via the CLI

## Technical Decisions

### GitHub API Access
- Uses PyGithub library for API interactions
- Falls back to GitHub CLI for authentication if token not provided
- Implements robust error handling for API calls, particularly for license detection
- Uses multiple methods to detect licenses (API-reported licenses and file-based detection)

### Repository Forking and Access Control
- Automatically detects if the user has write access to a repository
- Forks repositories to the user's account when they don't have write access
- Creates pull requests from the user's fork to the original repository
- Handles cross-repository pull requests with proper head branch specification
- Reuses existing forks if the user has already forked the repository

### License Template Management
- Templates stored in a dedicated directory
- Default templates created automatically if not present
- Supports multiple license types (MIT, Apache 2.0)
- Templates can be customized by the user

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
   - Changes are made on a new branch
   - A pull request is created within the same repository
3. If the user doesn't have write access:
   - The system checks if the user has already forked the repository
   - If a fork exists, it is used; otherwise, a new fork is created
   - Changes are made on a new branch in the forked repository
   - A pull request is created from the user's fork to the original repository

This approach ensures that the tool can work with any repository, regardless of the user's access level, while following GitHub's best practices for contributions.

## Future Enhancements

- Support for additional license types
- Integration with CI/CD pipelines
- Batch processing for large organizations
- License compliance reporting
- Custom license template variables

## Dependencies

- PyGithub: GitHub API client
- Click: Command-line interface
- Jinja2: Template rendering
- PyYAML: Configuration file parsing

## Requirements

- Python 3.8.1+
- GitHub CLI (gh) for authentication (optional)
- GitHub Personal Access Token (if not using GitHub CLI) 