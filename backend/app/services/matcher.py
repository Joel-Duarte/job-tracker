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


def _is_skill_matched(
    jd_skill: str,
    normalized_candidate: dict[str, str],
    fuzzy_threshold: float = 85.0,
) -> bool:
    """Checks if a JD required skill matches any skill in the candidate's CV profile."""
    norm_jd = _normalize_token(jd_skill)
    jd_clean = jd_skill.lower().strip()

    for cand_orig, cand_norm in normalized_candidate.items():
        if not cand_norm:
            continue

        # 1. Exact normalized token match or exact string match
        if norm_jd == cand_norm or jd_clean == cand_orig.lower().strip():
            return True

        # 2. Substring / phrase containment for multi-word or compound skills
        if len(norm_jd) >= 3 and len(cand_norm) >= 3:
            if norm_jd in cand_norm or cand_norm in norm_jd:
                return True

        # 3. RapidFuzz token matching
        if len(norm_jd) >= 4 and len(cand_norm) >= 4:
            if fuzz.ratio(norm_jd, cand_norm) >= fuzzy_threshold:
                return True
            if fuzz.token_set_ratio(jd_clean, cand_orig.lower()) >= fuzzy_threshold:
                return True

    return False


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

    # 1. Determine target JD skills list
    target_jd_skills: list[str] = []
    if jd_required_skills:
        seen = set()
        for s in jd_required_skills:
            clean = s.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                target_jd_skills.append(clean)

    # 2. Fallback: Scan candidate skills found in raw JD text if no structured skills provided
    if not target_jd_skills and jd_text:
        jd_lower = jd_text.lower()
        jd_words = set(re.findall(r"\b[a-zA-Z0-9\+\#\/\.\-]+\b", jd_lower))
        jd_words_normalized = {_normalize_token(w) for w in jd_words}

        found_in_jd: list[str] = []
        for orig_skill, norm_skill in normalized_candidate.items():
            if not norm_skill:
                continue
            pattern = r"\b" + re.escape(norm_skill) + r"\b"
            if (
                re.search(pattern, jd_lower)
                or norm_skill in jd_words_normalized
                or orig_skill.lower().strip() in jd_lower
            ):
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
        if _is_skill_matched(
            jd_skill, normalized_candidate, fuzzy_threshold=fuzzy_threshold
        ):
            matching_skills.append(jd_skill)
        else:
            missing_skills.append(jd_skill)

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
