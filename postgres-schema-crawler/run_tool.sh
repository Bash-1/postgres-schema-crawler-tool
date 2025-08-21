#!/bin/bash

echo "========================================"
echo "PostgreSQL Schema Crawler - Launcher"
echo "========================================"
echo ""
echo "Starting the complete tool..."
echo ""

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Run the Python script
python3 run_tool.py

echo ""
echo "Tool execution completed." 