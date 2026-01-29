#!/usr/bin/env python3
"""
Test script to verify AI-powered summarization works.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from digest_pipeline import DigestPipeline

def test_ai_digest():
    """Test digest generation with AI summaries."""

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set - will use simple summaries instead of AI")
        print("   To enable AI summaries, set your OpenAI API key:")
        print("   export OPENAI_API_KEY='your-key-here'\n")
    else:
        print("✓ OpenAI API key found - AI summaries enabled\n")

    pipeline = DigestPipeline()

    print("Testing digest generation with grouped summaries for 'alice'...\n")

    try:
        digest = pipeline.generate_digest("alice", hours_back=24)

        print(f"\n✓ Digest generated successfully!")
        print(f"  - Urgent: {len(digest.urgent)} project groups")
        print(f"  - Active: {len(digest.active)} project groups")
        print(f"  - Review: {len(digest.review)} project groups")

        # Show sample summaries
        if digest.urgent:
            print(f"\n📌 Sample Urgent Group:")
            group = digest.urgent[0]
            print(f"  Project: {group.project_name}")
            print(f"  Messages: {group.message_count}")
            print(f"  Summary: {group.summary}")
            print(f"  Individual items: {len(group.items)}")

        if digest.active:
            print(f"\n📌 Sample Active Group:")
            group = digest.active[0]
            print(f"  Project: {group.project_name}")
            print(f"  Messages: {group.message_count}")
            print(f"  Summary: {group.summary}")
            print(f"  Individual items: {len(group.items)}")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ai_digest()
    sys.exit(0 if success else 1)
