#!/bin/bash

# Run the Automated Video Production Pipeline
set -e

# Activate venv if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
  echo "Activated virtual environment."
else
  echo "No venv found. Using system Python."
fi

# Install requirements if needed
pip install -r requirements.txt

# Run the pipeline
python run.py "$@" 