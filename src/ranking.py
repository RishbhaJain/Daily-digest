"""
Ranking function to compute relevance scores for messages.
Determines which messages should appear in a user's digest.
"""

import math
from datetime import datetime
from typing import Optional, Dict
from models import Message, UserProjectState


# Role-based sender priority
HIGH_PRIORITY_ROLES = {"pm", "engineering_lead"}
SENDER_ROLE_BOOST_HIGH = 2.0
SENDER_ROLE_BOOST_NORMAL = 1.0


def temporal_decay(timestamp: str, now: datetime = None) -> float:
    """
    Compute a recency score using exponential decay.

    Messages decay over 24 hours, with half-life of ~8 hours.

    Args:
        timestamp: ISO datetime string of the message.
        now: Current time (defaults to datetime.now()).

    Returns:
        Score between 0.0 and 1.0, where 1.0 is most recent.
    """
    if now is None:
        now = datetime.now()

    msg_time = datetime.fromisoformat(timestamp)
    hours_ago = (now - msg_time).total_seconds() / 3600

    # Exponential decay with half-life of 8 hours
    # After 24 hours, score is ~0.125
    decay_rate = math.log(2) / 8  # Half-life of 8 hours
    score = math.exp(-decay_rate * hours_ago)

    # Clamp between 0 and 1
    return max(0.0, min(1.0, score))


def compute_relevance(
    message: Message,
    project_state: Optional[UserProjectState],
    user_id: str,
    user_roles: Optional[Dict[str, str]] = None
) -> float:
    """
    Compute the relevance score for a message given user's project state.

    Scoring logic:
    - Phase gates filter out irrelevant messages
    - Base score from temporal decay
    - Boost for urgency, activity level, mentions, sender role
    - Penalty for "review" phase

    Args:
        message: The Message to score.
        project_state: User's state for this message's project (or None).
        user_id: The user ID for mention detection.
        user_roles: Optional dict mapping user_id -> role string.

    Returns:
        Relevance score (0.0 to ~4.0+).
    """
    # Unknown project - low priority
    if not project_state:
        return 0.3

    # Phase gate: done projects are filtered out
    if project_state.phase == "done":
        return 0.0

    # Phase gate: blocked projects only show blocker messages
    if project_state.phase == "blocked" and not message.is_blocker:
        return 0.1

    # Base recency score
    recency_score = temporal_decay(message.timestamp)

    # Urgency boost
    urgency_boost = 1.5 if message.is_urgent else 1.0

    # Blocker boost
    blocker_boost = 1.3 if message.is_blocker else 1.0

    # Mention boost - if user is mentioned, significantly boost relevance
    mention_boost = 1.8 if user_id in message.mentions else 1.0

    # Activity boost based on recent activity in this project
    # More active projects get slightly higher scores
    activity_boost = min(1.0 + (project_state.messages_past_week * 0.05), 1.5)

    # Sender role boost - prioritize messages from PMs and engineering leads
    sender_role_boost = SENDER_ROLE_BOOST_NORMAL
    if user_roles and message.sender in user_roles:
        sender_role = user_roles[message.sender]
        if sender_role in HIGH_PRIORITY_ROLES:
            sender_role_boost = SENDER_ROLE_BOOST_HIGH

    # Combine all factors
    final = (recency_score * urgency_boost * blocker_boost *
             mention_boost * activity_boost * sender_role_boost)

    # Review phase penalty - reduce priority for review projects
    if project_state.phase == "review":
        final *= 0.5

    return final
