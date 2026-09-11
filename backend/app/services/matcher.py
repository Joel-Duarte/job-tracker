import re

from rapidfuzz import fuzz

SKILL_ALIASES = {
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "py": "python",
    "python": "python",
    "react": "react",
    "reactjs": "react",
    "vue": "vue",
    "vuejs": "vue",
    "golang": "go",
    "aws": "amazon web services",
    "gcp": "google cloud",
    "azure": "microsoft azure",
    "ts": "typescript",
    "js": "javascript",
    "node": "node.js",
    "nodejs": "node.js",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "docker": "docker",
    "graphql": "graphql",
    "kafka": "apache kafka",
    "redis": "redis",
    "mongodb": "mongodb",
    "sql": "sql",
    "nosql": "nosql",
    "ci/cd": "ci/cd",
    "cicd": "ci/cd",
    "llm": "large language models",
    "llms": "large language models",
    "langchain": "langchain",
    "langgraph": "langgraph",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
}


def _normalize_token(token: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\+\#\/\.\-]", "", token).lower()
    return SKILL_ALIASES.get(cleaned, cleaned)


# Unrelated technical skills that must NEVER match via substring containment or token overlap
UNRELATED_SKILL_PAIRS = {
    ("java", "javascript"),
    ("java", "typescript"),
    ("c", "c++"),
    ("c", "c#"),
    ("go", "django"),
    ("r", "rust"),
    ("r", "ruby"),
}


def _are_unrelated_skills(skill_a: str, skill_b: str) -> bool:
    a_lower = skill_a.lower().strip()
    b_lower = skill_b.lower().strip()
    return (a_lower, b_lower) in UNRELATED_SKILL_PAIRS or (
        b_lower,
        a_lower,
    ) in UNRELATED_SKILL_PAIRS


def _find_matched_candidate_skill(
    jd_skill: str,
    normalized_candidate: dict[str, str],
    fuzzy_threshold: float = 85.0,
) -> str | None:
    """Finds and returns the candidate's matching skill name, guarding against false substring matches."""
    norm_jd = _normalize_token(jd_skill)
    jd_clean = jd_skill.lower().strip()

    # Pass 1: Exact normalized token or exact string match
    for cand_orig, cand_norm in normalized_candidate.items():
        if not cand_norm:
            continue
        if norm_jd == cand_norm or jd_clean == cand_orig.lower().strip():
            return cand_orig

    # Pass 2: Substring / phrase containment for multi-word or compound skills (excluding unrelated pairs)
    for cand_orig, cand_norm in normalized_candidate.items():
        if (
            not cand_norm
            or _are_unrelated_skills(norm_jd, cand_norm)
            or _are_unrelated_skills(jd_clean, cand_orig)
        ):
            continue
        if len(norm_jd) >= 3 and len(cand_norm) >= 3:
            if norm_jd in cand_norm or cand_norm in norm_jd:
                return cand_orig

    # Pass 3: RapidFuzz token matching
    for cand_orig, cand_norm in normalized_candidate.items():
        if (
            not cand_norm
            or _are_unrelated_skills(norm_jd, cand_norm)
            or _are_unrelated_skills(jd_clean, cand_orig)
        ):
            continue
        if len(norm_jd) >= 4 and len(cand_norm) >= 4:
            if fuzz.ratio(norm_jd, cand_norm) >= fuzzy_threshold:
                return cand_orig
            if fuzz.token_set_ratio(jd_clean, cand_orig.lower()) >= fuzzy_threshold:
                return cand_orig

    return None


def _is_skill_matched(
    jd_skill: str,
    normalized_candidate: dict[str, str],
    fuzzy_threshold: float = 85.0,
) -> bool:
    """Checks if a JD required skill matches any skill in the candidate's CV profile."""
    return (
        _find_matched_candidate_skill(
            jd_skill, normalized_candidate, fuzzy_threshold=fuzzy_threshold
        )
        is not None
    )


def compute_programmatic_skill_match(
    candidate_skills: list[str],
    jd_text: str,
    jd_required_skills: list[str] | None = None,
    fuzzy_threshold: float = 85.0,
) -> dict:
    """
    Computes Job Requirement Coverage Ratio between candidate CV skills and the JD's required skills.
    Formula: (Matched JD Skills / Total JD Required Skills) * 100.
    E.g., if the role requires 20 skills and the candidate matches 10, the score is 50%.

    Returns:
      - programmatic_score: int (0 - 100) or None if no required skills identified
      - matching_skills: list of JD required skills possessed by the candidate
      - missing_skills: list of JD required skills not found on the candidate profile
      - matched_count: number of matched skills
      - total_required_count: total number of required skills in JD
      - candidate_total_skills: total skills in candidate profile
    """
    cand_skills = candidate_skills or []
    normalized_candidate = {
        s: _normalize_token(s) for s in cand_skills if s and s.strip()
    }

    # 1. Determine target JD skills list (combining explicit JD skills and taxonomy extraction)
    target_jd_skills: list[str] = []
    seen = set()

    if jd_required_skills:
        for s in jd_required_skills:
            clean = s.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                target_jd_skills.append(clean)

    if jd_text:
        # Deterministic regex taxonomy scan to supplement or identify skills
        from app.services.skill_normalizer import extract_skills_from_text

        for s in extract_skills_from_text(jd_text):
            clean = s.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                target_jd_skills.append(clean)

    # 2. Fallback: Only if NO skills were identified in the JD text via taxonomy,
    # scan if any candidate skills appear as distinct whole words in the JD
    if not target_jd_skills and jd_text:
        found_in_jd: list[str] = []
        for orig_skill, norm_skill in normalized_candidate.items():
            if not norm_skill:
                continue
            # Single-letter skills (C, R) require exact uppercase whole-word match
            if len(orig_skill.strip()) == 1:
                pattern = r"\b" + re.escape(orig_skill.strip()) + r"\b"
                if re.search(pattern, jd_text):
                    found_in_jd.append(orig_skill)
            elif orig_skill.strip().lower() == "go":
                # Avoid matching the common English verb 'go'
                pattern = r"\bGo\b"
                if re.search(pattern, jd_text):
                    found_in_jd.append(orig_skill)
            else:
                pattern = r"\b" + re.escape(norm_skill) + r"\b"
                if re.search(pattern, jd_text, re.IGNORECASE):
                    found_in_jd.append(orig_skill)
        target_jd_skills = found_in_jd

    # If no required skills identified in JD even after fallback
    if not target_jd_skills:
        return {
            "programmatic_score": None,
            "matching_skills": [],
            "missing_skills": [],
            "matched_count": 0,
            "total_required_count": 0,
            "candidate_total_skills": len(cand_skills),
        }

    # 3. Partition into matching and missing JD skills
    matching_skills: list[str] = []
    missing_skills: list[str] = []

    for jd_skill in target_jd_skills:
        matched_cand = _find_matched_candidate_skill(
            jd_skill, normalized_candidate, fuzzy_threshold=fuzzy_threshold
        )
        if matched_cand:
            matching_skills.append(matched_cand)
        else:
            missing_skills.append(jd_skill)

    matching_skills = sorted(matching_skills, key=str.lower)
    missing_skills = sorted(missing_skills, key=str.lower)

    # 4. Calculate coverage ratio percentage
    matched_count = len(matching_skills)
    total_count = len(target_jd_skills)
    score_pct = int(round((matched_count / total_count) * 100))
    score_pct = max(0, min(100, score_pct))

    return {
        "programmatic_score": score_pct,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "matched_count": matched_count,
        "total_required_count": total_count,
        "candidate_total_skills": len(cand_skills),
    }
