import re
from typing import List, Tuple
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


def compute_programmatic_skill_match(
    candidate_skills: List[str],
    jd_text: str,
    fuzzy_threshold: float = 85.0,
) -> dict:
    """
    Computes hybrid exact + rapidfuzz skill overlap between candidate CV skills and Job Description text.
    Handles single tokens, multi-word phrases, and extended keywords using partial and token-set matching.
    Returns:
      - programmatic_score: int (0 - 100)
      - matching_skills: list of candidate skills present in the JD
      - candidate_total_skills: total skills in CV
    """
    if not candidate_skills or not jd_text:
        return {
            "programmatic_score": 0,
            "matching_skills": [],
            "candidate_total_skills": len(candidate_skills) if candidate_skills else 0,
        }

    jd_lower = jd_text.lower()
    normalized_candidate = {s: _normalize_token(s) for s in candidate_skills}

    matching_skills: List[str] = []

    # Extract word tokens and multi-word line segments from JD
    jd_words = set(re.findall(r"\b[a-zA-Z0-9\+\#\/\.\-]+\b", jd_lower))
    jd_words_normalized = {_normalize_token(w) for w in jd_words}
    jd_phrases = [
        p.strip() for p in re.split(r"[\n,;•·\-–—]+", jd_lower) if len(p.strip()) >= 3
    ]

    for orig_skill, norm_skill in normalized_candidate.items():
        if not norm_skill:
            continue

        # 1. Exact substring check or word-boundary check
        pattern = r"\b" + re.escape(norm_skill) + r"\b"
        if re.search(pattern, jd_lower) or norm_skill in jd_words_normalized:
            matching_skills.append(orig_skill)
            continue

        # 2. Check multi-word phrase containment
        skill_clean = orig_skill.lower().strip()
        if skill_clean and skill_clean in jd_lower:
            matching_skills.append(orig_skill)
            continue

        # 3. RapidFuzz token matching against JD words
        matched = False
        for jd_word in jd_words_normalized:
            if len(norm_skill) >= 4 and len(jd_word) >= 4:
                ratio = fuzz.ratio(norm_skill, jd_word)
                if ratio >= fuzzy_threshold:
                    matching_skills.append(orig_skill)
                    matched = True
                    break
        if matched:
            continue

        # 4. RapidFuzz partial & token set matching against JD phrases (e.g. 'FastAPI backend services')
        for phrase in jd_phrases:
            if len(norm_skill) >= 3 and len(phrase) >= 3:
                partial = fuzz.partial_ratio(norm_skill, phrase)
                token_set = fuzz.token_set_ratio(norm_skill, phrase)
                if max(partial, token_set) >= fuzzy_threshold:
                    matching_skills.append(orig_skill)
                    break

    # Calculate weighted match score
    match_count = len(matching_skills)
    total_count = len(candidate_skills)
    score_pct = int(round((match_count / max(1, min(total_count, 12))) * 100))
    score_pct = max(0, min(100, score_pct))

    return {
        "programmatic_score": score_pct,
        "matching_skills": matching_skills,
        "candidate_total_skills": total_count,
    }
