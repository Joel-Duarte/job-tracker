"""Export and PII-scrub real postings, assessments, Q&A, and emails from local Postgres for golden dataset review.

Writes strictly to git-ignored `backend/data/golden_staging/real_db_candidates.json`.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.tests.golden.pii_scrubber import find_residual_pii, scrub_nested, scrub_pii

DEFAULT_OUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "golden_staging"
    / "real_db_candidates.json"
)


def _resolve_dsn() -> str:
    env_url = os.getenv("DATABASE_URL") or os.getenv("GOLDEN_DB_DSN")
    if env_url:
        return env_url.replace("postgresql+asyncpg://", "postgresql://")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "10556")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def _audit_match_row(row: dict[str, Any]) -> dict[str, Any]:
    """Flag potential heuristic/LLM mismatch anomalies in stored application assessments."""
    payload = row.get("match_analysis_payload") or {}
    if not isinstance(payload, dict):
        return {"audit_flags": ["invalid_payload"]}

    score = payload.get("fit_score")
    if score is None:
        score = payload.get("overall_match")
    if score is None:
        score = payload.get("match_score")
    prog_score = payload.get("programmatic_match_score")
    rec = str(payload.get("recommendation") or "")
    critical_risks = payload.get("critical_risks") or []
    flags: list[str] = []

    if isinstance(score, (int, float)):
        if score >= 75 and rec in ("NO_FIT", "SKIP", "WEAK_FIT", "DO_NOT_APPLY"):
            flags.append(f"score_rec_conflict:{score}_vs_{rec}")
        if score < 45 and rec in ("STRONG_FIT", "APPLY", "MUST_APPLY", "STRONG_MATCH"):
            flags.append(f"score_rec_conflict:{score}_vs_{rec}")
        if isinstance(prog_score, (int, float)) and abs(score - prog_score) > 35:
            flags.append(f"ai_vs_algo_delta:{score}_vs_{prog_score}")
    for r in critical_risks:
        txt = str(r).lower()
        if any(
            p in txt for p in ("none", "no critical risk", "verified prerequisites")
        ):
            flags.append(f"pseudo_risk:{str(r)[:60]}")

    return {
        "score": score,
        "programmatic_match_score": prog_score,
        "recommendation": rec,
        "critical_risks_count": len(critical_risks),
        "audit_flags": flags,
    }


def export_candidates(
    limit_per_band: int = 4, out_path: Path = DEFAULT_OUT_PATH
) -> dict[str, Any]:
    """Query local Postgres, scrub PII, audit match quality, and write staging review JSON."""
    dsn = _resolve_dsn()
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        cur = conn.cursor()

        # 1. Load active anonymized CV (never export raw_text)
        cur.execute(
            """
            SELECT id, anonymized_text, extracted_skills, years_of_experience,
                   domain_expertise, domain_experience, spoken_languages
            FROM candidate_cvs
            ORDER BY id DESC
            LIMIT 1
            """
        )
        cv_row = cur.fetchone()
        scrubbed_cv = ""
        if cv_row:
            scrubbed_cv, _ = scrub_pii(cv_row.get("anonymized_text") or "")

        # 2. Sample real job postings joined with applications & match assessments
        cur.execute(
            """
            SELECT
                a.id AS application_id,
                c.name AS company_name,
                a.position,
                a.status,
                a.match_analysis_payload,
                a.cover_letter_text,
                a.application_questions,
                jp.description_markdown,
                jp.structured_spec,
                jp.required_skills,
                jp.salary_min,
                jp.salary_max,
                jp.currency,
                jp.location,
                jp.work_model
            FROM applications a
            JOIN companies c ON c.id = a.company_id
            JOIN job_postings jp ON jp.application_id = a.id
            WHERE jp.description_markdown IS NOT NULL
              AND length(jp.description_markdown) > 200
              AND a.match_analysis_payload IS NOT NULL
            ORDER BY a.id DESC
            LIMIT 120
            """
        )
        rows = cur.fetchall()

        high_band: list[dict[str, Any]] = []
        mid_band: list[dict[str, Any]] = []
        low_band: list[dict[str, Any]] = []
        audit_anomalies = 0

        for idx, row in enumerate(rows, start=1):
            audit = _audit_match_row(row)
            if audit["audit_flags"]:
                audit_anomalies += 1
            score = audit.get("score")
            if not isinstance(score, (int, float)):
                continue

            extra_terms = [row.get("company_name") or ""]
            jd_scrubbed, jd_counts = scrub_pii(
                row.get("description_markdown") or "", extra_terms=extra_terms
            )
            cl_scrubbed, _ = scrub_pii(
                row.get("cover_letter_text") or "", extra_terms=extra_terms
            )
            residual = find_residual_pii(jd_scrubbed) + find_residual_pii(cl_scrubbed)

            entry = {
                "sample_id": f"db_posting_{row['application_id']}",
                "company_alias": f"Company_{idx}",
                "position": scrub_pii(
                    row.get("position") or "", extra_terms=extra_terms
                )[0],
                "location": row.get("location"),
                "work_model": row.get("work_model"),
                "salary_min": row.get("salary_min"),
                "salary_max": row.get("salary_max"),
                "currency": row.get("currency"),
                "description_markdown": jd_scrubbed[:5000],
                "structured_spec": scrub_nested(
                    row.get("structured_spec") or {}, extra_terms=extra_terms
                ),
                "required_skills": row.get("required_skills") or [],
                "match_audit": audit,
                "stored_match_summary": scrub_nested(
                    {
                        "score": score,
                        "recommendation": audit["recommendation"],
                        "matching_skills": (
                            row.get("match_analysis_payload") or {}
                        ).get("matching_skills", []),
                        "missing_skills": (row.get("match_analysis_payload") or {}).get(
                            "missing_skills", []
                        ),
                        "critical_risks": (row.get("match_analysis_payload") or {}).get(
                            "critical_risks", []
                        ),
                    },
                    extra_terms=extra_terms,
                ),
                "has_cover_letter": bool(cl_scrubbed.strip()),
                "cover_letter_excerpt": cl_scrubbed[:1200] if cl_scrubbed else None,
                "pii_scrub_stats": jd_counts,
                "residual_pii": residual,
            }

            if score >= 75 and len(high_band) < limit_per_band:
                high_band.append(entry)
            elif 50 <= score < 75 and len(mid_band) < limit_per_band:
                mid_band.append(entry)
            elif score < 50 and len(low_band) < limit_per_band:
                low_band.append(entry)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "total_scanned_rows": len(rows),
        "audit_anomalies_detected": audit_anomalies,
        "candidate_cv": {
            "anonymized_text": scrubbed_cv[:4500],
            "extracted_skills": (cv_row or {}).get("extracted_skills") or [],
            "years_of_experience": (cv_row or {}).get("years_of_experience"),
            "spoken_languages": (cv_row or {}).get("spoken_languages") or [],
            "residual_pii": find_residual_pii(scrubbed_cv),
        },
        "samples": {
            "high_fit": high_band,
            "mid_fit": mid_band,
            "low_fit": low_band,
        },
    }
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    args = parser.parse_args()
    res = export_candidates(limit_per_band=args.limit, out_path=args.out)
    print(
        json.dumps(
            {
                "written_to": str(args.out),
                "total_scanned_rows": res["total_scanned_rows"],
                "audit_anomalies_detected": res["audit_anomalies_detected"],
                "band_counts": {k: len(v) for k, v in res["samples"].items()},
                "cv_residual_pii": res["candidate_cv"]["residual_pii"],
            },
            indent=2,
        )
    )
