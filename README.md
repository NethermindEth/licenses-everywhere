# License Everywhere

A command-line tool to ensure all public repositories in a GitHub organization have proper license files.

## Features

- Scan GitHub organizations for repositories without license files
- Add appropriate license files to repositories via pull requests
- Support for multiple license types (MIT, Apache 2.0, GPL, etc.)
- Customizable copyright holder information
- Dry-run mode to preview changes without making them
- Support for multiple authentication providers (GitHub CLI, 1Password, Bitwarden, environment variables)
- Uses SSH by default for Git operations (avoids keychain access issues)
- Ability to fork repositories when you don't have write access

## Authentication

License Everywhere supports multiple authentication methods:

1. **SSH** - Default method for Git operations (clone, push) - avoids keychain access issues
2. **GitHub CLI** - Uses the GitHub CLI's authentication (for GitHub API operations)
3. **1Password** - Retrieves tokens from 1Password CLI
4. **Bitwarden** - Retrieves tokens from Bitwarden CLI
5. **Environment Variables** - Uses the `GITHUB_TOKEN` environment variable
6. **Direct Token** - Provide a token directly via the `--token` option or interactive prompt

You can specify which authentication provider to use with the `--auth-provider` option:

```bash
# Use SSH for Git operations (default) with GitHub CLI for API operations
licenses-everywhere scan --org myorg --auth-provider gh

# Use SSH for Git operations with 1Password for API authentication
licenses-everywhere scan --org myorg --auth-provider 1password --auth-item "GitHub Token"

# Use SSH for Git operations with Bitwarden for API authentication
licenses-everywhere scan --org myorg --auth-provider bitwarden --auth-item "GitHub Token"

# Use SSH for Git operations with environment variable for API authentication
licenses-everywhere scan --org myorg --auth-provider env

# Use SSH for Git operations with direct token for API authentication
licenses-everywhere scan --org myorg --auth-provider direct --token ghp_your_token_here
# Or without providing the token on the command line (you'll be prompted)
licenses-everywhere scan --org myorg --auth-provider direct

# Disable SSH and use HTTPS with token authentication instead
licenses-everywhere scan --org myorg --auth-provider direct --token ghp_your_token_here --no-ssh
```

To see which authentication providers are available on your system:

```bash
licenses-everywhere auth-providers
```

To check your current authentication status:

```bash
licenses-everywhere auth-status
# Or with a specific provider
licenses-everywhere auth-status --auth-provider gh
licenses-everywhere auth-status --auth-provider 1password --auth-item "GitHub Token"
licenses-everywhere auth-status --auth-provider direct --token ghp_your_token_here
# Check HTTPS authentication instead of SSH
licenses-everywhere auth-status --no-ssh
```

### Authentication Provider Details

#### SSH Authentication (Default)
- Uses SSH keys instead of HTTPS for Git operations
- Completely bypasses the need for tokens or keychain for Git operations
- Requires SSH keys to be set up with GitHub
- To set up:
  1. Generate an SSH key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
  2. Start the SSH agent: `eval "$(ssh-agent -s)"`
  3. Add your key: `ssh-add ~/.ssh/id_ed25519`
  4. Add the key to GitHub: https://github.com/settings/keys
  5. Test with: `ssh -T git@github.com`
- **Note**: This still requires a token for GitHub API operations, but not for Git operations
- To disable SSH and use HTTPS instead: `--no-ssh`

#### GitHub CLI (`gh`)
- Uses the GitHub CLI's built-in authentication mechanism
- On macOS, this typically uses the system keychain
- Requires the GitHub CLI to be installed and authenticated
- To set up: `gh auth login`
- To check status: `gh auth status`

#### 1Password
- Retrieves tokens directly from 1Password using the 1Password CLI
- Requires the 1Password CLI (`op`) to be installed and configured
- To set up: 
  1. Install 1Password CLI: `brew install 1password-cli` (macOS)
  2. Sign in: `op signin`
  3. Store your GitHub token in 1Password with a field named "token"

#### Bitwarden
- Retrieves tokens directly from Bitwarden using the Bitwarden CLI
- Requires the Bitwarden CLI (`bw`) to be installed and configured
- To set up:
  1. Install Bitwarden CLI: `npm install -g @bitwarden/cli`
  2. Log in: `bw login`
  3. Unlock the vault: `bw unlock`
  4. Store your GitHub token in Bitwarden

#### Environment Variables
- Uses the `GITHUB_TOKEN` environment variable
- To set up: `export GITHUB_TOKEN=your_token_here`

#### Direct Token
- Most reliable method as it doesn't depend on external tools
- Provide a token directly via the `--token` option
- If no token is provided, you'll be prompted to enter one
- Tokens are not stored between runs for security reasons
- When using the direct token provider, the token is used for:
  - All GitHub API operations
  - Git clone and push operations (embedded in the URL)
  - Pull request creation
- This avoids the need to use the system keychain or GitHub CLI's OAuth application
- **Important**: This method explicitly disables Git's credential helper to prevent macOS keychain access
- For users experiencing issues with keychain prompts, this is the recommended authentication method

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

1. **SSH Key Issues**:
   - Ensure your SSH key is added to GitHub: https://github.com/settings/keys
   - Check if your SSH agent is running: `eval "$(ssh-agent -s)"`
   - Add your key to the agent: `ssh-add ~/.ssh/id_ed25519`
   - Test your SSH connection: `ssh -T git@github.com`

2. **Re-authenticate with GitHub CLI**:
   ```bash
   gh auth login
   ```

3. **Check Token Permissions**:
   Ensure your token has the necessary permissions listed above.

4. **OAuth Application Re-authorization**:
   If you see a message about re-authorizing an OAuth application, visit GitHub and approve the authorization request.

5. **Keychain Access Issues on macOS**:
   If you're experiencing issues with macOS keychain prompts:
   - SSH is used by default and should avoid these issues
   - If you've disabled SSH with `--no-ssh`, try using direct token authentication: `--auth-provider direct --token YOUR_TOKEN`
   - If you still see keychain prompts, try running: `git config --global credential.helper ""`
   - To restore normal Git behavior later: `git config --global credential.helper osxkeychain`
   - Switch back to using SSH: remove the `--no-ssh` flag (SSH is the default) 