"""
DigestGenerator: Transforms ranked messages into a readable digest.
Groups messages by urgency and project phase, with AI summaries.
"""

import os
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
from models import Message, UserProjectState, Digest, DigestItem, ProjectGroup

# OpenAI import (optional - will work without it)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    print("✓ OpenAI package imported successfully")
except ImportError as e:
    OPENAI_AVAILABLE = False
    print(f"✗ OpenAI package import failed: {e}")


class DigestGenerator:
    """Generates a formatted digest from ranked messages with AI summaries."""

    def __init__(self, max_items: int = 20, use_ai_summaries: bool = True):
        """
        Initialize the generator.

        Args:
            max_items: Maximum total items to include in digest.
            use_ai_summaries: Whether to use OpenAI for summaries (requires API key).
        """
        self.max_items = max_items
        self.use_ai_summaries = use_ai_summaries and OPENAI_AVAILABLE

        if self.use_ai_summaries:
            try:
                self.client = OpenAI()  # Uses OPENAI_API_KEY env var
                print("✓ OpenAI client initialized successfully")
            except Exception as e:
                print(f"✗ OpenAI client initialization failed: {e}")
                self.use_ai_summaries = False
                self.client = None
        else:
            self.client = None
            print("AI summaries disabled (use_ai_summaries=False)")

    def generate(
        self,
        ranked_messages: List[Tuple[Message, UserProjectState, float]],
        user_id: str,
        project_names: Dict[str, str] = None
    ) -> Digest:
        """
        Generate a digest from ranked messages.

        Args:
            ranked_messages: List of (Message, UserProjectState, relevance_score) tuples,
                           sorted by relevance descending.
            user_id: The user this digest is for.
            project_names: Dict mapping project_id to project name.

        Returns:
            Digest object with messages grouped by project.
        """
        now = datetime.now()
        project_names = project_names or {}

        # Categorize messages
        urgent_msgs = defaultdict(list)
        active_msgs = defaultdict(list)
        review_msgs = defaultdict(list)

        for message, project_state, score in ranked_messages[:self.max_items]:
            # Create digest item
            item = self._create_digest_item(message, project_state, score)
            project_id = project_state.project_id if project_state else "unknown"

            # Categorize
            if message.is_urgent or message.is_blocker:
                urgent_msgs[project_id].append((item, message))
            elif project_state and project_state.phase == "active":
                active_msgs[project_id].append((item, message))
            elif project_state and project_state.phase == "review":
                review_msgs[project_id].append((item, message))
            else:
                # Default to active
                active_msgs[project_id].append((item, message))

        # Create project groups with summaries
        urgent_groups = self._create_project_groups(urgent_msgs, project_names, "urgent")
        active_groups = self._create_project_groups(active_msgs, project_names, "active")
        review_groups = self._create_project_groups(review_msgs, project_names, "review")

        # Create digest
        digest = Digest(
            generated_at=now.isoformat(),
            user_id=user_id,
            urgent=urgent_groups,
            active=active_groups,
            review=review_groups,
        )

        return digest

    def _create_project_groups(
        self,
        messages_by_project: Dict[str, List[Tuple[DigestItem, Message]]],
        project_names: Dict[str, str],
        section_type: str
    ) -> List[ProjectGroup]:
        """
        Create ProjectGroup objects from categorized messages.

        Args:
            messages_by_project: Dict of project_id -> list of (DigestItem, Message) tuples.
            project_names: Dict mapping project_id to project name.
            section_type: Type of section ("urgent", "active", or "review").

        Returns:
            List of ProjectGroup objects.
        """
        groups = []

        for project_id, items_and_msgs in messages_by_project.items():
            items = [item for item, _ in items_and_msgs]
            messages = [msg for _, msg in items_and_msgs]

            project_name = project_names.get(project_id, project_id.replace("-", " ").title())

            # Generate AI summary
            summary = self._generate_ai_summary(messages, project_name, section_type)

            group = ProjectGroup(
                project_id=project_id,
                project_name=project_name,
                summary=summary,
                items=items,
                message_count=len(items)
            )
            groups.append(group)

        # Sort groups by message count (descending)
        groups.sort(key=lambda g: g.message_count, reverse=True)

        return groups

    def _generate_ai_summary(
        self,
        messages: List[Message],
        project_name: str,
        section_type: str
    ) -> str:
        """
        Generate an AI summary for a group of messages.

        Args:
            messages: List of messages to summarize.
            project_name: Name of the project.
            section_type: Type of section.

        Returns:
            Summary string.
        """
        if not messages:
            return "No messages"

        if len(messages) == 1:
            return self._summarize_message(messages[0])

        # If AI is not available, fall back to simple summary
        if not self.use_ai_summaries:
            return self._simple_summary(messages, project_name)

        # Use OpenAI to generate summary
        try:
            # Prepare message context
            msg_texts = []
            for i, msg in enumerate(messages[:10], 1):  # Limit to 10 messages
                msg_texts.append(f"{i}. From {msg.sender}: {msg.text[:200]}")

            context = "\n".join(msg_texts)

            prompt = f"""Summarize these {len(messages)} Slack messages from the "{project_name}" project. Focus on the key updates, decisions, or blockers.

Messages:
{context}

Summary:"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()
            return summary

        except Exception as e:
            # Fall back to simple summary if AI fails
            print(f"AI summary failed: {e}")
            return self._simple_summary(messages, project_name)

    def _simple_summary(self, messages: List[Message], project_name: str) -> str:
        """
        Create a simple summary without AI.

        Args:
            messages: List of messages.
            project_name: Name of the project.

        Returns:
            Summary string.
        """
        count = len(messages)
        senders = set(msg.sender for msg in messages)
        sender_list = ", ".join(list(senders)[:3])
        if len(senders) > 3:
            sender_list += f" and {len(senders) - 3} others"

        # Count urgency indicators
        blocker_count = sum(1 for m in messages if m.is_blocker)
        urgent_count = sum(1 for m in messages if m.is_urgent)

        parts = [f"{count} messages from {sender_list}"]

        if blocker_count > 0:
            parts.append(f"{blocker_count} blocker{'s' if blocker_count > 1 else ''}")
        if urgent_count > 0:
            parts.append(f"{urgent_count} urgent")

        return " - ".join(parts)

    def _create_digest_item(
        self,
        message: Message,
        project_state: UserProjectState,
        relevance_score: float
    ) -> DigestItem:
        """
        Create a DigestItem from a message.

        Args:
            message: The source message.
            project_state: User's project state.
            relevance_score: Computed relevance score.

        Returns:
            DigestItem object.
        """
        # Create a simple summary (truncate long messages)
        summary = self._summarize_message(message)

        return DigestItem(
            message_id=message.id,
            project_id=project_state.project_id if project_state else "unknown",
            summary=summary,
            relevance_score=relevance_score,
            sender=message.sender,
            channel=message.channel,
            timestamp=message.timestamp,
            is_urgent=message.is_urgent,
            is_blocker=message.is_blocker,
        )

    def _summarize_message(self, message: Message) -> str:
        """
        Create a one-line summary of a message.

        Args:
            message: The Message to summarize.

        Returns:
            Summary string.
        """
        max_length = 150

        # Remove newlines and extra whitespace
        text = " ".join(message.text.split())

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."

        return text
