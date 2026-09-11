from app.services.benchmark_service import (
    check_factual_grounding,
    detect_repetitive_loops,
    validate_benchmark_quality,
)


def test_detect_repetitive_loops():
    normal_text = (
        "Alex Morgan is a staff distributed systems engineer with deep expertise in Python, "
        "FastAPI, Kafka, and PostgreSQL. He has scaled transaction pipelines to 45,000 req/sec."
    )
    assert not detect_repetitive_loops(normal_text)

    # 15+ words with repeating 3-grams
    looping_text = (
        "Alex Morgan is a staff engineer. "
        "The system crashed. The system crashed. The system crashed. The system crashed. "
        "The system crashed. The system crashed. The system crashed. The system crashed."
    )
    assert detect_repetitive_loops(looping_text)


def test_check_factual_grounding():
    skills = ["Python", "FastAPI", "Kafka", "PostgreSQL"]
    text_with_skill = (
        "The candidate has built scalable APIs using Python and PostgreSQL."
    )
    assert check_factual_grounding(text_with_skill, skills)

    text_without_skill = (
        "The candidate has built scalable APIs using Java and Oracle DB."
    )
    assert not check_factual_grounding(text_without_skill, skills)


def test_validate_benchmark_quality_clean_json():
    skills = ["Python", "FastAPI", "Kafka"]
    raw_output = """{
        "company": "CloudScale Infrastructure",
        "position": "Staff Distributed Systems Engineer",
        "fit_score": 90,
        "match_summary": "Strong candidate with Python and FastAPI experience.",
        "matching_skills": ["Python", "FastAPI"]
    }"""
    result = validate_benchmark_quality(raw_output, skills)
    assert result["passed"] is True
    assert result["schema_valid"] is True
    assert result["is_grounded"] is True
    assert result["is_loop"] is False
    assert result["parsed_json"]["company"] == "CloudScale Infrastructure"


def test_validate_benchmark_quality_markdown_fenced_json():
    skills = ["Python", "FastAPI", "Kafka"]
    raw_output = """Here is the structured assessment:
```json
{
    "company": "CloudScale Infrastructure",
    "position": "Staff Distributed Systems Engineer",
    "fit_score": 85,
    "match_summary": "Matches required stack in Python and Kafka."
}
```
Hope this helps!"""
    result = validate_benchmark_quality(raw_output, skills)
    assert result["passed"] is True
    assert result["schema_valid"] is True
    assert result["is_grounded"] is True
    assert result["is_loop"] is False


def test_validate_benchmark_quality_with_thinking_tags():
    skills = ["Python", "Kafka"]
    raw_output = """<think>
Evaluating Alex Morgan against CloudScale JD.
Candidate has 8.5 years experience with Python and Kafka.
Fit score is 88%.
</think>
```json
{
    "company": "CloudScale Infrastructure",
    "position": "Staff Systems Engineer",
    "fit_score": 88,
    "match_summary": "Extensive experience with Python and Kafka."
}
```"""
    result = validate_benchmark_quality(raw_output, skills)
    assert result["passed"] is True
    assert result["schema_valid"] is True
    assert result["is_grounded"] is True
    assert result["is_loop"] is False


def test_validate_benchmark_quality_invalid_json():
    skills = ["Python"]
    raw_output = "The candidate is a great match for the role because of Python skills."
    result = validate_benchmark_quality(raw_output, skills)
    assert result["passed"] is False
    assert result["schema_valid"] is False
    assert result["is_grounded"] is True
