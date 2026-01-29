#!/bin/bash

echo "=================================================="
echo " Daily Digest Tool - Quick Start Guide"
echo "=================================================="
echo ""
echo "Choose an option:"
echo ""
echo "1. Run Web UI (Recommended)"
echo "2. Run CLI Test"
echo "3. Show Project Structure"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
  1)
    echo ""
    echo "Starting web server..."
    echo "Open your browser to: http://127.0.0.1:5001"
    echo ""
    ./venv/bin/python3 run_web_ui.py
    ;;
  2)
    echo ""
    echo "Running CLI test for user 'alice'..."
    echo ""
    ./venv/bin/python3 test_pipeline.py
    ;;
  3)
    echo ""
    tree -L 2 -I 'venv|__pycache__' || find . -maxdepth 2 -not -path '*/venv/*' -not -path '*/__pycache__/*' -not -path '*/.*' | sort
    ;;
  *)
    echo "Invalid choice"
    exit 1
    ;;
esac
