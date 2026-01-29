"""
Digest Pipeline: Orchestrates the entire digest generation process.
Main entry point for generating user digests.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict

from models import Message, UserProjectState, Digest, Project
from storage import Storage
from project_extractor import ProjectExtractor
from project_state_manager import ProjectStateManager
from ranking import compute_relevance
from digest_generator import DigestGenerator


class DigestPipeline:
    """Main pipeline for generating daily digests."""

    def __init__(self, storage: Storage = None):
        """
        Initialize the pipeline.

        Args:
            storage: Storage instance (creates default if None).
        """
        self.storage = storage or Storage()
        self.state_manager = ProjectStateManager()
        self.digest_generator = DigestGenerator(max_items=20)

    def generate_digest(self, user_id: str, hours_back: int = 24) -> Digest:
        """
        Generate a digest for a user.

        This is the main entry point that orchestrates all components.

        Args:
            user_id: The user to generate digest for.
            hours_back: How many hours of messages to consider.

        Returns:
            Generated Digest object.
        """
        print(f"\n=== Generating digest for {user_id} ===")

        # Step 1: Fetch messages from past N hours
        since = datetime.now() - timedelta(hours=hours_back)
        messages = self.storage.load_messages(since=since)
        print(f"Loaded {len(messages)} messages from past {hours_back} hours")

        # Step 2: Load projects and user's project states
        projects = self.storage.load_projects()
        user_states = self.storage.load_user_states(user_id)
        users = self.storage.load_users()
        user_roles = {uid: u["role"] for uid, u in users.items()}
        print(f"Loaded {len(projects)} projects, {len(user_states)} user states, {len(users)} users")

        # Create project extractor
        project_extractor = ProjectExtractor(projects)

        # Step 3: Update project states based on activity
        user_states = self._update_project_states(
            user_id,
            user_states,
            messages,
            project_extractor
        )
        print(f"Updated project states")

        # Step 4: Filter and rank messages
        ranked_messages = self._filter_and_rank_messages(
            user_id,
            messages,
            user_states,
            project_extractor,
            user_roles
        )
        print(f"Ranked {len(ranked_messages)} relevant messages")

        # Step 5: Generate digest
        project_names = {p.project_id: p.name for p in projects}
        digest = self.digest_generator.generate(ranked_messages, user_id, project_names)
        print(f"Generated digest: {len(digest.urgent)} urgent, "
              f"{len(digest.active)} active, {len(digest.review)} review")

        # Step 6: Persist updated states and digest
        self.storage.save_user_states(user_states)
        self.storage.save_digest(digest)
        print(f"Saved digest and updated states")

        return digest

    def _update_project_states(
        self,
        user_id: str,
        user_states: List[UserProjectState],
        messages: List[Message],
        project_extractor: ProjectExtractor
    ) -> List[UserProjectState]:
        """
        Update project states based on recent activity.

        Args:
            user_id: The user ID.
            user_states: Current user states.
            messages: Recent messages.
            project_extractor: ProjectExtractor instance.

        Returns:
            Updated list of UserProjectState objects.
        """
        # Group messages by project
        messages_by_project = defaultdict(list)
        for msg in messages:
            project_id = project_extractor.extract_project(msg)
            if project_id:
                messages_by_project[project_id].append(msg)

        # Create a dict for quick state lookup
        states_dict = {state.project_id: state for state in user_states}
        updated_states = []

        # Update existing states
        for project_id, state in states_dict.items():
            project_messages = messages_by_project.get(project_id, [])

            # Update activity counts
            state = self.state_manager.update_activity_counts(state, project_messages)

            # Detect phase changes
            user_messages = [msg for msg in project_messages if msg.sender == user_id]
            new_phase = self.state_manager.detect_phase(state, user_messages)

            # Check for anomalies (re-activation)
            if self.state_manager.check_anomalies(state, project_messages):
                new_phase = "review"  # Re-activate done projects to review

            # Apply transition if phase changed
            if new_phase != state.phase:
                state = self.state_manager.transition(state, new_phase)
                print(f"  {project_id}: {state.phase} -> {new_phase}")

            updated_states.append(state)

        # Create states for new projects
        for project_id, project_messages in messages_by_project.items():
            if project_id not in states_dict:
                # Find a message that involves this user
                trigger_msg = None
                for msg in project_messages:
                    if user_id in msg.mentions or msg.sender == user_id:
                        trigger_msg = msg
                        break

                if not trigger_msg and project_messages:
                    trigger_msg = project_messages[0]

                if trigger_msg:
                    project = project_extractor.get_project_by_id(project_id)
                    channels = project.channels if project else []
                    new_state = self.state_manager.create_state(
                        user_id, project_id, trigger_msg, channels
                    )
                    updated_states.append(new_state)
                    print(f"  Created new state for {project_id}: {new_state.phase}")

        return updated_states

    def _filter_and_rank_messages(
        self,
        user_id: str,
        messages: List[Message],
        user_states: List[UserProjectState],
        project_extractor: ProjectExtractor,
        user_roles: Dict[str, str]
    ) -> List[Tuple[Message, UserProjectState, float]]:
        """
        Filter and rank messages by relevance.

        Args:
            user_id: The user ID.
            messages: All messages to consider.
            user_states: User's project states.
            project_extractor: ProjectExtractor instance.
            user_roles: Dict mapping user_id to role string.

        Returns:
            List of (Message, UserProjectState, score) tuples, sorted by score descending.
        """
        # Create state lookup dict
        states_dict = {state.project_id: state for state in user_states}

        # Score each message
        scored_messages = []
        for message in messages:
            # Extract project
            project_id = project_extractor.extract_project(message)

            # Get user's state for this project (if exists)
            project_state = states_dict.get(project_id)

            # Compute relevance
            score = compute_relevance(message, project_state, user_id, user_roles)

            # Only include if score > 0
            if score > 0:
                scored_messages.append((message, project_state, score))

        # Sort by score descending
        scored_messages.sort(key=lambda x: x[2], reverse=True)

        return scored_messages
