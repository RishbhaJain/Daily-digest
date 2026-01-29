"""
ProjectStateManager: Manages phase transitions and detects anomalies.
Handles the lifecycle of user project states.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from models import UserProjectState, Message


class ProjectStateManager:
    """Manages phase transitions and detects anomalies that re-activate projects."""

    def detect_phase(
        self,
        project_state: UserProjectState,
        user_messages: List[Message]
    ) -> str:
        """
        Infer the appropriate phase from activity patterns.

        Phase detection logic:
        1. If last_contributed > 2 weeks ago → "done"
        2. If messages_past_week == 0 and was "active" → "review"
        3. If messages_past_week >= 3 → "active"
        4. Otherwise → keep current phase

        Args:
            project_state: Current UserProjectState.
            user_messages: Recent messages from this user in this project.

        Returns:
            The recommended phase string.
        """
        now = datetime.now()
        last_contrib = datetime.fromisoformat(project_state.last_contributed)
        days_since_contrib = (now - last_contrib).days

        # Rule 1: No activity for 2+ weeks → done
        if days_since_contrib >= 14:
            return "done"

        # Rule 2: Was active but no messages this week → review
        if project_state.messages_past_week == 0 and project_state.phase == "active":
            return "review"

        # Rule 3: High activity (3+ messages/week) → active
        if project_state.messages_past_week >= 3:
            return "active"

        # Rule 4: Low activity (1-2 messages/week) → review
        if 0 < project_state.messages_past_week < 3:
            return "review"

        # Default: keep current phase
        return project_state.phase

    def check_anomalies(
        self,
        project_state: UserProjectState,
        new_messages: List[Message]
    ) -> bool:
        """
        Detect triggers that should re-activate a "done" project.

        Anomaly triggers:
        - User is @mentioned in the project
        - Message is urgent or a blocker
        - Someone is replying in a thread user participated in

        Args:
            project_state: The UserProjectState to check.
            new_messages: Recent messages from this project.

        Returns:
            True if an anomaly is detected (should re-activate), False otherwise.
        """
        # Only check if project is in "done" phase
        if project_state.phase != "done":
            return False

        user_id = project_state.user_id

        for message in new_messages:
            # Anomaly 1: User is mentioned
            if user_id in message.mentions:
                return True

            # Anomaly 2: Urgent or blocker message in this project
            if message.is_urgent or message.is_blocker:
                return True

        return False

    def transition(self, project_state: UserProjectState, new_phase: str) -> UserProjectState:
        """
        Apply a phase transition to a project state.

        Valid transitions:
        - active ↔ review ↔ done
        - active → blocked
        - blocked → active/review

        Args:
            project_state: The current UserProjectState.
            new_phase: The new phase to transition to.

        Returns:
            Updated UserProjectState object.
        """
        # Simple validation: ensure new_phase is valid
        valid_phases = {"active", "review", "done", "blocked"}
        if new_phase not in valid_phases:
            raise ValueError(f"Invalid phase: {new_phase}")

        # Create a new state object with updated phase
        return UserProjectState(
            user_id=project_state.user_id,
            project_id=project_state.project_id,
            phase=new_phase,
            channels=project_state.channels,
            last_contributed=project_state.last_contributed,
            messages_past_week=project_state.messages_past_week,
        )

    def create_state(
        self,
        user_id: str,
        project_id: str,
        trigger_message: Message,
        channels: List[str]
    ) -> UserProjectState:
        """
        Initialize a new UserProjectState when a user first encounters a project.

        Rules:
        - If user is @mentioned → start as "active"
        - If user sent the message → start as "active"
        - Otherwise → start as "review"

        Args:
            user_id: The user ID.
            project_id: The project ID.
            trigger_message: The message that triggered this project creation.
            channels: List of channels for this project.

        Returns:
            New UserProjectState object.
        """
        # Determine initial phase
        if user_id in trigger_message.mentions or trigger_message.sender == user_id:
            initial_phase = "active"
        else:
            initial_phase = "review"

        return UserProjectState(
            user_id=user_id,
            project_id=project_id,
            phase=initial_phase,
            channels=channels,
            last_contributed=trigger_message.timestamp,
            messages_past_week=1 if trigger_message.sender == user_id else 0,
        )

    def update_activity_counts(
        self,
        project_state: UserProjectState,
        recent_messages: List[Message]
    ) -> UserProjectState:
        """
        Update the activity counters for a project state based on recent messages.

        Args:
            project_state: Current state to update.
            recent_messages: Messages from the past week in this project.

        Returns:
            Updated UserProjectState with new counts.
        """
        user_id = project_state.user_id
        now = datetime.now()
        one_week_ago = now - timedelta(days=7)

        # Count messages from this user in the past week
        count = 0
        latest_timestamp = project_state.last_contributed

        for msg in recent_messages:
            if msg.sender != user_id:
                continue

            msg_time = datetime.fromisoformat(msg.timestamp)
            if msg_time >= one_week_ago:
                count += 1

            # Track most recent contribution
            if msg.timestamp > latest_timestamp:
                latest_timestamp = msg.timestamp

        return UserProjectState(
            user_id=project_state.user_id,
            project_id=project_state.project_id,
            phase=project_state.phase,
            channels=project_state.channels,
            last_contributed=latest_timestamp,
            messages_past_week=count,
        )
