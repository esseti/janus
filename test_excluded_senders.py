"""Test script for excluded senders functionality."""

from __future__ import annotations

from src.gmail_client import GmailClient


def test_excluded_patterns():
    """Test the excluded sender pattern matching."""
    # Create a mock client to test pattern matching
    client = GmailClient()

    # Test cases - will be tested against patterns in excluded_senders.txt
    test_cases = [
        # Substring matching (backward compatibility)
        ("newsletter@substack.com", True, "Substring: Direct match"),
        (
            "John Doe <newsletter@substack.com>",
            True,
            "Substring: Match in formatted email",
        ),
        ("notifications@linkedin.com", True, "Substring: Domain match"),
        # Wildcard patterns with *
        ("user-notify@test.com", True, "Wildcard *: *-notify@*.com pattern"),
        ("admin-notify@example.com", True, "Wildcard *: *-notify@*.com pattern"),
        (
            "newsletter-daily@substack.com",
            True,
            "Wildcard *: newsletter-*@substack.com",
        ),
        (
            "newsletter-weekly@substack.com",
            True,
            "Wildcard *: newsletter-*@substack.com",
        ),
        ("info@linkedin.com", True, "Wildcard *: *@linkedin.com"),
        ("jobs@linkedin.com", True, "Wildcard *: *@linkedin.com"),
        # Wildcard patterns with ?
        ("no-reply@test.com", True, "Wildcard ?: ?o-reply@*.com"),
        ("do-reply@example.com", True, "Wildcard ?: ?o-reply@*.com"),
        # Should NOT match
        ("user@example.com", False, "Should not match any pattern"),
        ("hello@gmail.com", False, "Should not match any pattern"),
        ("notify@test.com", False, "Missing prefix for *-notify pattern"),
        # Case insensitive
        ("NEWSLETTER@SUBSTACK.COM", True, "Case insensitive: uppercase"),
        ("User-NOTIFY@TEST.com", True, "Case insensitive: mixed case"),
    ]

    print("🧪 Testing excluded sender patterns\n")
    print(f"Loaded patterns: {client.excluded_senders}\n")

    passed = 0
    failed = 0

    for email, should_exclude, description in test_cases:
        is_excluded = client._is_excluded_sender(email)
        status = "✅" if is_excluded == should_exclude else "❌"

        if is_excluded == should_exclude:
            passed += 1
        else:
            failed += 1

        print(f"{status} {description}")
        print(f"   Email: {email}")
        print(f"   Expected: {should_exclude}, Got: {is_excluded}\n")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    test_excluded_patterns()
