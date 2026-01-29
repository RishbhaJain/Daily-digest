"""
Quick test script to verify the digest pipeline works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from digest_pipeline import DigestPipeline

def test_digest():
    """Test digest generation for a user."""
    pipeline = DigestPipeline()

    # Test with alice
    print("Testing digest generation for 'alice'...")
    try:
        digest = pipeline.generate_digest("alice", hours_back=24)

        print(f"\n✓ Digest generated successfully!")
        print(f"  - Urgent items: {len(digest.urgent)}")
        print(f"  - Active items: {len(digest.active)}")
        print(f"  - Review items: {len(digest.review)}")
        print(f"  - Total items: {len(digest.urgent) + len(digest.active) + len(digest.review)}")

        if digest.urgent:
            print(f"\nFirst urgent item:")
            print(f"  {digest.urgent[0].summary}")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_digest()
    sys.exit(0 if success else 1)
