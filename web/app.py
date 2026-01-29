"""
Flask Web UI for Daily Digest Tool.
Provides a simple interface to generate and view digests.
"""

import sys
from pathlib import Path

# Add parent directory to path to import from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime

from digest_pipeline import DigestPipeline
from storage import Storage

app = Flask(__name__)

# Initialize components
storage = Storage()
pipeline = DigestPipeline(storage)


@app.route("/")
def home():
    """Home page with user dropdown."""
    # Load users from data/users.json
    data_dir = Path(__file__).parent.parent / "data"
    users_file = data_dir / "users.json"

    users = []
    if users_file.exists():
        with open(users_file, "r") as f:
            users = json.load(f)

    return render_template("index.html", users=users)


@app.route("/digest")
def digest():
    """Generate and display digest for a user."""
    user_id = request.args.get("user_id")

    if not user_id:
        return "Error: user_id parameter required", 400

    # Generate digest
    try:
        digest_obj = pipeline.generate_digest(user_id, hours_back=24)

        # Get user info
        data_dir = Path(__file__).parent.parent / "data"
        users_file = data_dir / "users.json"
        user_name = user_id

        if users_file.exists():
            with open(users_file, "r") as f:
                users = json.load(f)
                for user in users:
                    if user["user_id"] == user_id:
                        user_name = user["name"]
                        break

        # Get project names for display
        projects = storage.load_projects()
        project_names = {p.project_id: p.name for p in projects}

        return render_template(
            "digest.html",
            user_id=user_id,
            user_name=user_name,
            digest=digest_obj,
            project_names=project_names,
            generated_at=datetime.fromisoformat(digest_obj.generated_at).strftime("%B %d, %Y at %I:%M %p")
        )

    except Exception as e:
        return f"Error generating digest: {str(e)}", 500


@app.route("/api/digest/<user_id>")
def api_digest(user_id):
    """API endpoint to get digest as JSON."""
    try:
        digest_obj = pipeline.generate_digest(user_id, hours_back=24)

        # Convert to dict for JSON response
        digest_dict = {
            "generated_at": digest_obj.generated_at,
            "user_id": digest_obj.user_id,
            "urgent": [
                {
                    "message_id": item.message_id,
                    "project_id": item.project_id,
                    "summary": item.summary,
                    "sender": item.sender,
                    "channel": item.channel,
                    "timestamp": item.timestamp,
                    "is_urgent": item.is_urgent,
                    "is_blocker": item.is_blocker,
                }
                for item in digest_obj.urgent
            ],
            "active": [
                {
                    "message_id": item.message_id,
                    "project_id": item.project_id,
                    "summary": item.summary,
                    "sender": item.sender,
                    "channel": item.channel,
                    "timestamp": item.timestamp,
                }
                for item in digest_obj.active
            ],
            "review": [
                {
                    "message_id": item.message_id,
                    "project_id": item.project_id,
                    "summary": item.summary,
                    "sender": item.sender,
                    "channel": item.channel,
                    "timestamp": item.timestamp,
                }
                for item in digest_obj.review
            ],
        }

        return jsonify(digest_dict)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Daily Digest Tool - Web Interface")
    print("=" * 60)
    print("\nStarting server at http://127.0.0.1:5001")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, host="127.0.0.1", port=5001)
