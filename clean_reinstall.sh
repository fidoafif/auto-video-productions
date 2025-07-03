#!/bin/bash

# Clean outputs, caches, and reinstall dependencies
set -e

# Remove outputs
echo "Removing outputs..."
rm -rf outputs

# Remove all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} +

# Remove venv
echo "Removing virtual environment..."
rm -rf venv

# Recreate venv and reinstall requirements
echo "Recreating virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Clean and reinstall complete." 