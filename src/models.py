"""
Data models for the Daily Digest Tool.
Defines all core dataclasses used throughout the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class UserProjectState:
    """
    Track a user's involvement phase in a project.

    Phase meanings:
    - active: Show all messages, high priority
    - review: Show summaries only, medium priority
    - done: Filter out or minimal visibility
    - blocked: Show blocker-related messages only
    """
    user_id: str
    project_id: str
    phase: str  # "active", "review", "done", "blocked"
    channels: List[str]
    last_contributed: str  # ISO datetime string
    messages_past_week: int


@dataclass
class Project:
    """
    Define a project and its associated channels/keywords.
    """
    project_id: str
    name: str
    channels: List[str]
    keywords: List[str]


@dataclass
class Message:
    """
    Represents a Slack message with extracted metadata.
    """
    id: str
    channel: Optional[str]  # None if DM
    thread_id: Optional[str]
    sender: str
    text: str
    timestamp: str  # ISO datetime string
    mentions: List[str]
    is_dm: bool
    is_urgent: bool
    is_blocker: bool


@dataclass
class DigestItem:
    """
    A single item in the digest output.
    """
    message_id: str
    project_id: str
    summary: str
    relevance_score: float
    sender: str
    channel: Optional[str]
    timestamp: str
    is_urgent: bool
    is_blocker: bool


@dataclass
class ProjectGroup:
    """
    A group of messages from the same project with an AI summary.
    """
    project_id: str
    project_name: str
    summary: str  # AI-generated summary
    items: List[DigestItem]
    message_count: int


@dataclass
class Digest:
    """
    The final digest output structure.
    """
    generated_at: str  # ISO datetime string
    user_id: str
    urgent: List[ProjectGroup] = field(default_factory=list)
    active: List[ProjectGroup] = field(default_factory=list)
    review: List[ProjectGroup] = field(default_factory=list)
