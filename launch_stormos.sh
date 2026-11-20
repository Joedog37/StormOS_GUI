#!/bin/bash
# StormOS Launcher Script for Linux/macOS
# This script checks dependencies and launches StormOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "⚡ Starting StormOS..."

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "Error: Python 3.13+ is required but not found."
    echo "Please install Python from https://www.python.org/downloads/"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
REQUIRED="3.13"

echo "Detected Python version: $PYTHON_VERSION"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
fi

# Check if requirements are installed
$PYTHON -c "import PySide6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    $PYTHON -m pip install -r requirements.txt
fi

# Launch StormOS
$PYTHON main.py

# Handle exit
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "StormOS exited cleanly."
else
    echo "StormOS exited with code $exit_code"
fi

exit $exit_code
