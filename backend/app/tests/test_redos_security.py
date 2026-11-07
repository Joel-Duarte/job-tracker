import time

from app.services.compensation_parser import parse_compensation_text
from app.services.domain_resolver import clean_company_name
from app.services.file_parser import normalize_resume_text
from app.services.graph_nodes import _has_interleaved_plain_reply


def test_interleaved_reply_plain_redos_safety():
    # Pathological payload: quote followed by 50,000 newlines with no subsequent reply
    payload = ">\n" + "\n" * 50_000
    t0 = time.perf_counter()
    res = _has_interleaved_plain_reply(payload)
    duration = time.perf_counter() - t0
    assert res is False
    assert duration < 0.05, f"Expected <50ms execution, took {duration:.4f}s"

    # Genuine interleaved reply
    interleaved = "> Previous message\n\nMy actual inline reply"
    assert _has_interleaved_plain_reply(interleaved) is True

    # Pure quote block
    pure_quote = "> Quote line 1\n> Quote line 2\n"
    assert _has_interleaved_plain_reply(pure_quote) is False

    # Top-post reply followed by bottom quote
    top_post = "My reply at top\n\n> Quoted history at bottom"
    assert _has_interleaved_plain_reply(top_post) is False


def test_clean_company_name_redos_safety():
    # Pathological payload with 50,000 brackets and punctuation (verifies bounded time)
    pathological_large = "[" * 25_000 + "]" * 25_000
    t0 = time.perf_counter()
    _ = clean_company_name(pathological_large)
    duration = time.perf_counter() - t0
    assert duration < 0.02, f"Expected <20ms execution, took {duration:.4f}s"

    # Pathological payload within 512 char window
    pathological = "[" * 200 + "Stripe" + "]" * 200
    t0 = time.perf_counter()
    cleaned = clean_company_name(pathological)
    duration = time.perf_counter() - t0
    assert cleaned == "Stripe"
    assert duration < 0.02, f"Expected <20ms execution, took {duration:.4f}s"

    # Standard suffixes
    assert clean_company_name("Stripe, Inc.") == "Stripe"
    assert clean_company_name("Acme LLC") == "Acme"
    assert clean_company_name("Linear - Careers") == "Linear"
    assert clean_company_name("Datadog Jobs") == "Datadog"
    assert clean_company_name("TechCorp GmbH") == "TechCorp"
    assert clean_company_name("Global S.A.") == "Global"
    assert clean_company_name("Dutch B.V.") == "Dutch"
    assert clean_company_name("Company (UK) Ltd.") == "Company (UK)"
    assert clean_company_name("Cisco") == "Cisco"


def test_compensation_parser_redos_safety():
    # Pathological payload: 25,000 repetitions of '1.'
    pathological = "1." * 25_000 + "a"
    t0 = time.perf_counter()
    res = parse_compensation_text(pathological)
    duration = time.perf_counter() - t0
    assert res["salary_min"] is None
    assert duration < 0.05, f"Expected <50ms execution, took {duration:.4f}s"

    # Functional correctness
    r1 = parse_compensation_text("$120k - $150k")
    assert r1["salary_min"] == 120000.0
    assert r1["salary_max"] == 150000.0

    r2 = parse_compensation_text("Up to $180,000")
    assert r2["salary_max"] == 180000.0

    r3 = parse_compensation_text("120,000 EUR / year")
    assert r3["salary_min"] == 120000.0


def test_file_parser_redos_safety():
    # Pathological payload with 50,000 spaces
    spaces = " " * 50_000
    t0 = time.perf_counter()
    res = normalize_resume_text(spaces + "Experience\n- Engineer")
    duration = time.perf_counter() - t0
    assert "Engineer" in res
    assert duration < 0.05, f"Expected <50ms execution, took {duration:.4f}s"

    # Functional formatting
    sample = "San Francisco , CA ( Remote ) . Web-based application ."
    normalized = normalize_resume_text(sample)
    assert normalized == "San Francisco, CA (Remote). Web-based application."
