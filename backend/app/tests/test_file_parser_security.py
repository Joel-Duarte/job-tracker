from app.services.file_parser import normalize_resume_text


def test_long_single_line_resume_is_processed_in_bounded_segments():
    result = normalize_resume_text("Experience " + " " * 100_000 + "- Engineer")
    assert "Engineer" in result
    assert len(result) < 100_000


def test_resume_keeps_blank_lines():
    result = normalize_resume_text("Summary\n\nExperience")
    assert "Summary\n\nExperience" in result
