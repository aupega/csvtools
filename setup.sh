#!/bin/bash
# Setup script for macOS/Linux
# Installs Python, pip, and all dependencies for csv_compare_flask

if ! command -v python3 &>/dev/null; then
	echo "Python3 not found. Please install Python 3.8+ from https://www.python.org/downloads/"
	exit 1
fi

# Upgrade pip
python3 -m pip install --upgrade pip

# Install dependencies
python3 -m pip install -r requirements.txt

echo "Setup complete. You can now run: flask run"
