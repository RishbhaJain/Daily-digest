"""
Storage layer for the Daily Digest Tool.
Handles loading and persisting data from/to local JSON files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from models import Project, Message, UserProjectState, Digest


class Storage:
    """Handles all data persistence operations using local JSON files."""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.digests_dir = self.data_dir / "digests"
        self.digests_dir.mkdir(exist_ok=True)

    def load_projects(self) -> List[Project]:
        """Load all projects from projects.json."""
        path = self.data_dir / "projects.json"
        if not path.exists():
            return []

        with open(path, "r") as f:
            data = json.load(f)

        return [Project(**proj) for proj in data]

    def load_messages(self, since: datetime = None) -> List[Message]:
        """
        Load messages from messages.json.

        Args:
            since: If provided, only return messages after this datetime.

        Returns:
            List of Message objects, sorted by timestamp descending.
        """
        path = self.data_dir / "messages.json"
        if not path.exists():
            return []

        with open(path, "r") as f:
            data = json.load(f)

        messages = [Message(**msg) for msg in data]

        # Filter by time if specified
        if since:
            messages = [
                msg for msg in messages
                if datetime.fromisoformat(msg.timestamp) >= since
            ]

        # Sort by timestamp descending (most recent first)
        messages.sort(key=lambda m: m.timestamp, reverse=True)

        return messages

    def load_user_states(self, user_id: str) -> List[UserProjectState]:
        """
        Load UserProjectState entries for a specific user.

        Args:
            user_id: The user to load states for.

        Returns:
            List of UserProjectState objects for this user.
        """
        path = self.data_dir / "user_project_states.json"
        if not path.exists():
            return []

        with open(path, "r") as f:
            data = json.load(f)

        return [
            UserProjectState(**state)
            for state in data
            if state["user_id"] == user_id
        ]

    def load_users(self) -> Dict[str, Dict[str, str]]:
        """
        Load all users and return as a lookup dictionary.

        Returns:
            Dict mapping user_id to user data dict with 'name' and 'role'.
            Returns empty dict if users.json doesn't exist.
        """
        path = self.data_dir / "users.json"
        if not path.exists():
            return {}

        with open(path, "r") as f:
            users_list = json.load(f)

        # Convert list to dict for O(1) lookup
        return {user["user_id"]: user for user in users_list}

    def save_user_states(self, states: List[UserProjectState]):
        """
        Save updated UserProjectState entries.

        This merges with existing states - updates existing entries and adds new ones.

        Args:
            states: List of UserProjectState objects to save.
        """
        path = self.data_dir / "user_project_states.json"

        # Load existing states
        existing = []
        if path.exists():
            with open(path, "r") as f:
                existing = json.load(f)

        # Create a dict for fast lookup
        existing_dict = {
            (s["user_id"], s["project_id"]): s
            for s in existing
        }

        # Update with new states
        for state in states:
            key = (state.user_id, state.project_id)
            existing_dict[key] = {
                "user_id": state.user_id,
                "project_id": state.project_id,
                "phase": state.phase,
                "channels": state.channels,
                "last_contributed": state.last_contributed,
                "messages_past_week": state.messages_past_week,
            }

        # Save back to file
        with open(path, "w") as f:
            json.dump(list(existing_dict.values()), f, indent=2)

    def save_digest(self, digest: Digest):
        """
        Save a generated digest to the digests directory.

        Args:
            digest: The Digest object to save.
        """
        # Create filename: {user_id}_{date}.json
        timestamp = datetime.fromisoformat(digest.generated_at)
        date_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{digest.user_id}_{date_str}.json"
        path = self.digests_dir / filename

        # Helper to convert ProjectGroup to dict
        def group_to_dict(group):
            return {
                "project_id": group.project_id,
                "project_name": group.project_name,
                "summary": group.summary,
                "message_count": group.message_count,
                "items": [
                    {
                        "message_id": item.message_id,
                        "project_id": item.project_id,
                        "summary": item.summary,
                        "relevance_score": item.relevance_score,
                        "sender": item.sender,
                        "channel": item.channel,
                        "timestamp": item.timestamp,
                        "is_urgent": item.is_urgent,
                        "is_blocker": item.is_blocker,
                    }
                    for item in group.items
                ]
            }

        # Convert digest to dict
        digest_dict = {
            "generated_at": digest.generated_at,
            "user_id": digest.user_id,
            "urgent": [group_to_dict(group) for group in digest.urgent],
            "active": [group_to_dict(group) for group in digest.active],
            "review": [group_to_dict(group) for group in digest.review],
        }

        with open(path, "w") as f:
            json.dump(digest_dict, f, indent=2)

    def load_latest_digest(self, user_id: str) -> Digest:
        """
        Load the most recent digest for a user.

        Args:
            user_id: The user to load digest for.

        Returns:
            The most recent Digest object, or None if no digests exist.
        """
        # Find all digest files for this user
        pattern = f"{user_id}_*.json"
        digest_files = list(self.digests_dir.glob(pattern))

        if not digest_files:
            return None

        # Get the most recent one
        latest_file = max(digest_files, key=lambda p: p.stat().st_mtime)

        with open(latest_file, "r") as f:
            data = json.load(f)

        # Convert back to Digest object
        from models import DigestItem, ProjectGroup

        def dict_to_group(group_data):
            return ProjectGroup(
                project_id=group_data["project_id"],
                project_name=group_data["project_name"],
                summary=group_data["summary"],
                message_count=group_data["message_count"],
                items=[DigestItem(**item) for item in group_data["items"]]
            )

        digest = Digest(
            generated_at=data["generated_at"],
            user_id=data["user_id"],
            urgent=[dict_to_group(group) for group in data.get("urgent", [])],
            active=[dict_to_group(group) for group in data.get("active", [])],
            review=[dict_to_group(group) for group in data.get("review", [])],
        )

        return digest
