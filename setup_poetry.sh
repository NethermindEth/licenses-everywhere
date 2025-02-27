#!/bin/bash
# Script to initialize the Poetry project

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Please install it first:"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Initialize Poetry environment
echo "Initializing Poetry environment..."
poetry install

# Create templates directory if it doesn't exist
mkdir -p licenses_everywhere/templates

# The license templates are automatically created by the license_manager.py module
# when it's first run, so we don't need to create them manually

echo "Setup complete! You can now use the licenses-everywhere tool."
echo "Try running: poetry run licenses-everywhere --help" 