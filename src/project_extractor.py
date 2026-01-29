"""
ProjectExtractor: Identifies which project a message belongs to.
Uses channel matching, keyword matching, and semantic analysis.
"""

from typing import List, Optional
from models import Project, Message


class ProjectExtractor:
    """Identifies which project a message belongs to."""

    def __init__(self, projects: List[Project]):
        """
        Initialize the extractor with known projects.

        Args:
            projects: List of Project objects to match against.
        """
        self.projects = projects
        self.personal_project = Project(
            project_id="personal",
            name="Personal",
            channels=[],
            keywords=["promotion", "1:1", "career", "feedback", "review", "performance"]
        )

    def extract_project(self, message: Message) -> Optional[str]:
        """
        Extract the project_id for a given message.

        Extraction logic:
        1. Channel match - if message.channel in any project.channels
        2. Keyword match - check message text against project.keywords
        3. DM handling - match to project or personal

        Args:
            message: The Message object to analyze.

        Returns:
            project_id string, or None if no match found.
        """
        # Step 1: Channel match (most reliable)
        if message.channel:
            for project in self.projects:
                if message.channel in project.channels:
                    return project.project_id

        # Step 2: Keyword matching
        # Convert message text to lowercase for case-insensitive matching
        text_lower = message.text.lower()

        # Try each project's keywords
        for project in self.projects:
            for keyword in project.keywords:
                if keyword.lower() in text_lower:
                    return project.project_id

        # Step 3: DM handling
        if message.is_dm:
            # Check if DM content matches personal keywords
            for keyword in self.personal_project.keywords:
                if keyword.lower() in text_lower:
                    return self.personal_project.project_id

            # If DM doesn't match personal, try project keywords again
            # (already done above, so if we reach here, no match)
            return self.personal_project.project_id  # Default for unmatched DMs

        # No match found
        return None

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """
        Get a Project object by its ID.

        Args:
            project_id: The project ID to lookup.

        Returns:
            Project object or None if not found.
        """
        if project_id == "personal":
            return self.personal_project

        for project in self.projects:
            if project.project_id == project_id:
                return project

        return None
