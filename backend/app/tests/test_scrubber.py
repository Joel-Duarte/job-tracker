import pytest
from app.services.scrubber import programmatic_scrub_cv


def test_programmatic_scrub_cv_emails_phones_urls():
    sample_cv = (
        "Alice Walker\n"
        "Email: alice.walker@gmail.com | Phone: +1 (555) 234-5678\n"
        "LinkedIn: https://www.linkedin.com/in/alice-walker-dev\n"
        "GitHub: https://github.com/alicewalker\n"
        "Address: 742 Evergreen Terrace, Springfield OR 97477\n\n"
        "Summary:\n"
        "Senior Backend Engineer with 8 years of experience building Python and FastAPI distributed systems.\n"
        "Led architecture of billing pipelines processing $10M/month."
    )

    scrubbed, stats = programmatic_scrub_cv(sample_cv)

    # Assertions
    assert "alice.walker@gmail.com" not in scrubbed
    assert "[Email Redacted]" in scrubbed
    assert "+1 (555) 234-5678" not in scrubbed
    assert "[Phone Redacted]" in scrubbed
    assert "linkedin.com/in/alice-walker-dev" not in scrubbed
    assert "[Profile Link Redacted]" in scrubbed
    assert "742 Evergreen Terrace" not in scrubbed
    assert "[Address Redacted]" in scrubbed
    assert "Alice Walker" not in scrubbed
    assert "[Candidate Name]" in scrubbed

    # Check stats
    assert stats["emails"] >= 1
    assert stats["phones"] >= 1
    assert stats["urls"] >= 2
    assert stats["addresses"] >= 1
    assert stats["header_name"] == 1

    # Ensure technical skills and metrics are preserved untouched
    assert "Senior Backend Engineer with 8 years of experience" in scrubbed
    assert "FastAPI distributed systems" in scrubbed
    assert "$10M/month" in scrubbed


def test_programmatic_scrub_cv_empty():
    scrubbed, stats = programmatic_scrub_cv("")
    assert scrubbed == ""
    assert stats["emails"] == 0
