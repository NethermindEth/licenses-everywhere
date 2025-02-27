# License Everywhere

A command-line tool to ensure all public repositories in a GitHub organization have proper license files.

## Features

- Scans all public repositories in a GitHub organization
- Identifies repositories missing license files
- Interactive license selection for each repository
- Automatically creates pull requests to add licenses
- Supports multiple license types
- Clean and intuitive command-line interface
- Automatically forks repositories when you don't have write access

## Installation

### Prerequisites

- Python 3.8.1+
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management
- GitHub CLI (`gh`) installed and authenticated
- GitHub personal access token with appropriate permissions

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/licenses-everywhere.git
cd licenses-everywhere

# Quick setup using the provided script
./setup_poetry.sh

# Or manually install with Poetry
poetry install

# Ensure you have the GitHub CLI (gh) installed
# For macOS:
brew install gh

# For other platforms, see: https://github.com/cli/cli#installation

# Authenticate with GitHub CLI
gh auth login
```

### Install from PyPI (coming soon)

```bash
# Install with Poetry (once the package is published to PyPI)
poetry add licenses-everywhere

# Or with pip
pip install licenses-everywhere
```

## Usage

### Basic Usage

```bash
# Scan all public repositories in an organization
licenses-everywhere scan --org your-organization

# Specify a default license type
licenses-everywhere scan --org your-organization --license MIT

# Dry run (don't make any changes)
licenses-everywhere scan --org your-organization --dry-run

# List available license types
licenses-everywhere licenses
```

### Advanced Options

```bash
# Specify specific repositories to check
licenses-everywhere scan --org your-organization --repos repo1,repo2,repo3

# Allow skipping license selection for repositories
licenses-everywhere scan --org your-organization --allow-skip

# Combine multiple options
licenses-everywhere scan --org your-organization --repos repo1,repo2 --license MIT --allow-skip --dry-run
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--org` | `-o` | GitHub organization name |
| `--license` | `-l` | Default license type to use |
| `--copyright` | `-c` | Copyright holder name |
| `--dry-run` | `-d` | Don't make any changes, just show what would be done |
| `--token` | `-t` | GitHub personal access token (uses gh CLI auth if not provided) |
| `--repos` | `-r` | Comma-separated list of specific repositories to check |
| `--allow-skip` | `-s` | Allow skipping license selection for repositories |

## Configuration

You can configure default settings by creating a `.licenses-everywhere.yaml` file in your home directory:

```yaml
default_license: MIT
default_organization: your-organization
copyright_holder: Your Company Name
```

## License Types Supported

- MIT
- Apache 2.0
- GPL v3
- BSD 3-Clause
- Mozilla Public License 2.0
- And more...

## How It Works

License Everywhere follows this workflow for each repository:

1. Checks if the repository already has a license file
2. If no license is found, prompts you to select a license type
3. **Checks if you have write access to the repository**
4. **If you don't have write access, it automatically forks the repository to your account**
5. Creates a new branch for the license changes
6. Adds the appropriate license file
7. Commits and pushes the changes
8. Creates a pull request to the original repository
9. Provides a link to the created pull request

This approach ensures that you can contribute license files to any repository, even if you don't have direct write access.

## Development

This project uses Poetry for dependency management and packaging.

```bash
# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Format code
poetry run black licenses_everywhere
poetry run isort licenses_everywhere

# Type checking
poetry run mypy licenses_everywhere
```

## Project Structure

```
licenses-everywhere/
├── LICENSE                 # MIT License for this project
├── README.md               # This file
├── ARCHITECTURE.md         # Detailed architecture documentation
├── pyproject.toml          # Poetry configuration
├── pytest.ini              # Pytest configuration
├── setup_poetry.sh         # Setup script for Poetry
├── licenses_everywhere/    # Main package
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── core.py             # Core functionality
│   ├── github_client.py    # GitHub API client
│   ├── license_manager.py  # License template management
│   ├── repo_handler.py     # Repository operations
│   └── templates/          # License templates
│       ├── mit.txt
│       ├── apache-2.0.txt
│       └── ...
└── tests/                  # Test suite
    ├── __init__.py
    ├── test_config.py
    ├── test_license_manager.py
    └── ...
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## GitHub Authentication

The tool requires GitHub authentication to:
1. Fetch repository information
2. Clone repositories
3. Create branches and push changes
4. Submit pull requests
5. Fork repositories when needed

### Authentication Methods

1. **GitHub CLI (Recommended)**:
   ```bash
   gh auth login
   ```
   Follow the prompts to authenticate with your GitHub account.

2. **Personal Access Token**:
   You can provide a token directly using the `--token` option:
   ```bash
   licenses-everywhere scan --org your-organization --token YOUR_TOKEN
   ```

### Required Permissions

For the tool to work properly, your GitHub token needs these permissions:
- `repo` (Full control of private repositories)
- `workflow` (If you need to update GitHub Actions)
- `read:org` (To list organization repositories)

### Troubleshooting Authentication Issues

If you encounter authentication errors:

1. **Re-authenticate with GitHub CLI**:
   ```bash
   gh auth login
   ```

2. **Check Token Permissions**:
   Ensure your token has the necessary permissions listed above.

3. **OAuth Application Re-authorization**:
   If you see a message about re-authorizing an OAuth application, visit GitHub and approve the authorization request. 