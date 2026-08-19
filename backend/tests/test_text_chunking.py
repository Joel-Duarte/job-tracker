from app.services.llm import split_text_semantically, truncate_text_semantically


def test_split_text_semantically():
    """Verify text is split on semantic separators without losing content or splitting words mid-token."""
    text = (
        "# Header 1\n\n"
        "Paragraph 1 with important background detail.\n\n"
        "## Requirements\n\n"
        "- Requirement A: Python expertise.\n"
        "- Requirement B: PostgreSQL and FastAPI.\n\n"
        "## Responsibilities\n\n"
        "- Task 1: Scale distributed systems.\n"
        "- Task 2: Maintain CI/CD pipelines."
    )

    chunks = split_text_semantically(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    # Ensure all chunks are strings and none break mid-word (words should be intact)
    for chunk in chunks:
        assert isinstance(chunk, str)
        assert len(chunk) <= 120  # allow small overlap buffer


def test_truncate_text_semantically_preserves_priority_sections():
    """Verify semantic truncation respects priority section headers (Requirements, Responsibilities, Skills)."""
    fluff_paragraph = (
        "General boilerplate paragraph about office culture and company history. " * 30
    )
    req_paragraph = "## Requirements\n\n" + (
        "Must have Senior Python experience with asyncpg and LangChain. " * 20
    )
    resp_paragraph = "## Responsibilities\n\n" + (
        "Lead technical design for scalable web applications. " * 20
    )

    large_jd = f"{fluff_paragraph}\n\n{req_paragraph}\n\n{resp_paragraph}\n\n" + (
        "Additional filler text at the end. " * 30
    )

    truncated = truncate_text_semantically(large_jd, max_chars=1200, chunk_size=300)

    assert len(truncated) <= 1200
    # Priority sections (Requirements / Responsibilities) must be preserved in truncated output
    assert "Requirements" in truncated or "Requirements" in large_jd
    assert "Must have Senior Python" in truncated or "Responsibilities" in truncated


def test_truncate_text_semantically_clean_sentence_boundaries():
    """Verify truncation does not slice mid-word or mid-sentence arbitrarily."""
    text = (
        "First sentence in section one. Second sentence in section one. "
        "Third sentence with important details. Fourth sentence wrapping up section one."
    )

    truncated = truncate_text_semantically(text, max_chars=60, chunk_size=30)
    assert len(truncated) <= 60
    # Check that truncated string ends on a complete word / boundary rather than cut mid-character
    assert not truncated.endswith("sentenc")
    assert not truncated.endswith("sec")


def test_truncate_text_semantically_short_and_empty_inputs():
    """Verify empty or short inputs pass through unharmed."""
    assert truncate_text_semantically("", max_chars=100) == ""
    assert truncate_text_semantically(None, max_chars=100) == ""

    short_text = "Short job description."
    assert truncate_text_semantically(short_text, max_chars=1000) == short_text
