"""Test script for keep_senders functionality."""

from __future__ import annotations

from src.gmail_client import GmailClient


def test_keep_senders_priority():
    """Test that keep_senders has priority over excluded_senders."""
    client = GmailClient()

    # Test cases to verify keep_senders overrides excluded_senders
    test_cases = [
        # These should be KEPT (in keep_senders, even if match excluded_senders)
        (
            "important@newsletter.com",
            False,
            "Keep: Specific newsletter in keep_senders",
        ),
        (
            "alerts@critical-domain.com",
            False,
            "Keep: Domain pattern *@critical-domain.com",
        ),
        (
            "vip-alerts@example.com",
            False,
            "Keep: Wildcard pattern vip-*@*.com",
        ),
        # These should be EXCLUDED (in excluded_senders, not in keep_senders)
        (
            "random-notify@chino.io",
            True,
            "Exclude: Matches *-notify@chino.io pattern",
        ),
        (
            "newsletter-daily@substack.com",
            True,
            "Exclude: Matches newsletter-*@*.com pattern",
        ),
        (
            "no-reply@example.com",
            True,
            "Exclude: Matches ?o-reply@example.com pattern",
        ),
        # These should be PROCESSED (not in either list)
        (
            "user@example.com",
            False,
            "Process: Not in any list",
        ),
        (
            "hello@gmail.com",
            False,
            "Process: Not in any list",
        ),
    ]

    print("🧪 Testing keep_senders priority over excluded_senders\n")
    print(f"Keep patterns: {client.keep_senders}")
    print(f"Excluded patterns: {client.excluded_senders}\n")

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
        print(f"   Expected excluded: {should_exclude}, Got: {is_excluded}\n")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"{'=' * 60}\n")

    if failed > 0:
        print("\n⚠️  Some tests failed. Check your keep_senders.txt configuration.")
    else:
        print("\n✅ All tests passed! keep_senders is working correctly.")


if __name__ == "__main__":
    test_keep_senders_priority()
