#!/bin/bash
# Quick run script for the Preparation Agent

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "../venv" ]; then
    echo "Using parent venv..."
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    echo "Using local venv..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from env.example..."
    cp env.example .env
    echo "⚠️  Please edit .env with your API credentials before running!"
    exit 1
fi

# Run the agent
if [ -f "example_input_multiple.json" ]; then
    echo "Running preparation agent with example_input_multiple.json..."
    python preparation_agent.py --json-file example_input_multiple.json
else
    echo "Usage: $0"
    echo ""
    echo "Or run directly:"
    echo "  python preparation_agent.py --json-file example_input_multiple.json"
    echo "  python preparation_agent.py --json '{\"loan_id\":\"...\",\"document_types\":[\"W-2\"]}'"
fi




