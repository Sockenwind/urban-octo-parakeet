#!/bin/bash
set -e

# Install dependencies
pip install -r requirements.txt

# Clean previous builds
rm -rf build dist

# Build the app
# --onefile: create a single executable
# --windowed: no console window (for GUI)
# --name: name of the app
# --add-data: add any non-code files if needed (none here)
pyinstaller --noconfirm --onefile --windowed --name "CleanDrive" src/main.py

echo "Build complete. The app is located in dist/CleanDrive.app"
