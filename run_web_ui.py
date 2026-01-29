#!/usr/bin/env python3
"""
Launcher script for the Daily Digest Web UI.
Run this to start the Flask web server.
"""

import sys
from pathlib import Path

# Add web directory to path
web_dir = Path(__file__).parent / "web"
sys.path.insert(0, str(web_dir))

# Import and run the Flask app
from app import app

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" Daily Digest Tool - Web Interface")
    print("=" * 70)
    print("\n Server starting at: http://127.0.0.1:5001")
    print(" Press Ctrl+C to stop the server\n")
    print("=" * 70 + "\n")

    app.run(debug=True, host="127.0.0.1", port=5001)
