"""
Skill Canonicalization Engine.
Provides multi-stage skill normalization, taxonomy mapping (~450+ terms), RapidFuzz typo recovery,
fast deterministic regex text scanning, and hybrid extraction.
"""

import re

from rapidfuzz import fuzz, process

from app.services.skill_taxonomy import CANONICAL_SKILL_TAXONOMY

# Protected acronyms/terms that contain slashes or hyphens and must never be split
PROTECTED_COMPOUNDS = {"ci/cd", "pl/sql", "tcp/ip", "os/2"}

# Common boilerplate filler suffixes
NOISE_SUFFIXES = {
    "pipelines",
    "pipeline",
    "development",
    "developer",
    "engineering",
    "engineer",
    "cloud",
    "infrastructure",
    "database",
    "databases",
    "architecture",
    "management",
    "administration",
    "experience",
    "skills",
    "tools",
}

# Pre-compile regex search patterns for taxonomy keys sorted by length descending
_SORTED_TAXONOMY_KEYS = sorted(CANONICAL_SKILL_TAXONOMY.keys(), key=len, reverse=True)
_SKILL_PATTERNS: list[tuple[re.Pattern, str]] = []

for _key in _SORTED_TAXONOMY_KEYS:
    _escaped_key = re.escape(_key)
    _prefix = r"(?<![a-zA-Z0-9])" if _key[0].isalnum() else r"(?<!\S)"
    _suffix = r"(?![a-zA-Z0-9])"
    _pattern = re.compile(_prefix + _escaped_key + _suffix, re.IGNORECASE)
    _SKILL_PATTERNS.append((_pattern, CANONICAL_SKILL_TAXONOMY[_key]))

# List of taxonomy keys for RapidFuzz matching
_TAXONOMY_KEYS = list(CANONICAL_SKILL_TAXONOMY.keys())


def normalize_skill(skill: str) -> str:
    """
    Normalizes a single skill string using a 5-stage pipeline:
    - Stage 1: Direct Exact Match
    - Stage 3: Parenthetical & Noise Suffix Stripping
    - Stage 4: RapidFuzz Typo Recovery
    - Stage 5: Fallback Casing Rules
    """
    if not skill or not isinstance(skill, str):
        return ""

    raw_trimmed = skill.strip()
    if not raw_trimmed:
        return ""

    lookup_key = raw_trimmed.lower()

    # Stage 1: Direct Exact Match
    if lookup_key in CANONICAL_SKILL_TAXONOMY:
        return CANONICAL_SKILL_TAXONOMY[lookup_key]

    # Stage 3: Parenthetical Stripping
    no_parens = re.sub(r"\(.*?\)", "", raw_trimmed).strip()
    no_parens_key = no_parens.lower()
    if no_parens_key and no_parens_key in CANONICAL_SKILL_TAXONOMY:
        return CANONICAL_SKILL_TAXONOMY[no_parens_key]

    current = no_parens if no_parens else raw_trimmed
    current_key = current.lower()

    # Stage 3 (cont): Boilerplate Noise Suffix Stripping
    words = current.split()
    while len(words) > 1 and words[-1].lower() in NOISE_SUFFIXES:
        words.pop()
        stem_candidate = " ".join(words).strip()
        stem_key = stem_candidate.lower()
        if stem_key in CANONICAL_SKILL_TAXONOMY:
            return CANONICAL_SKILL_TAXONOMY[stem_key]
        current = stem_candidate
        current_key = stem_key

    if current_key in CANONICAL_SKILL_TAXONOMY:
        return CANONICAL_SKILL_TAXONOMY[current_key]

    # Stage 4: RapidFuzz Typo Recovery
    if len(current_key) >= 3:
        fuzz_match = process.extractOne(current_key, _TAXONOMY_KEYS, scorer=fuzz.WRatio)
        if fuzz_match:
            best_key, score, _ = fuzz_match
            if score >= 85.0 and abs(len(current_key) - len(best_key)) <= 3:
                return CANONICAL_SKILL_TAXONOMY[best_key]

    # Stage 5: Fallback Formatting
    if current.islower() or current.isupper():
        return current.title()

    # Preserve casing on mixed-case/camelCase terms
    return current


def _split_compound_skill(skill: str) -> list[str]:
    """Helper to split compound skills unless protected."""
    if not skill or not isinstance(skill, str):
        return []

    trimmed = skill.strip()
    if not trimmed:
        return []

    lower_val = trimmed.lower()
    if lower_val in PROTECTED_COMPOUNDS or lower_val in CANONICAL_SKILL_TAXONOMY:
        return [trimmed]

    no_parens = re.sub(r"\(.*?\)", "", trimmed).strip().lower()
    if no_parens in PROTECTED_COMPOUNDS or no_parens in CANONICAL_SKILL_TAXONOMY:
        return [trimmed]

    # Stage 2: Compound Term Splitting
    parts = re.split(r"\s+/\s+|\s+&\s+|\s+\+\s+", trimmed)
    return [p.strip() for p in parts if p.strip()]


def normalize_skills_list(skills: list[str]) -> list[str]:
    """
    Normalizes an array of skills with compound splitting, removes duplicates (preserving canonical order),
    and filters empty entries.
    """
    if not skills or not isinstance(skills, list):
        return []

    normalized_skills: list[str] = []
    seen: set[str] = set()

    for s in skills:
        sub_skills = _split_compound_skill(s)
        for sub in sub_skills:
            norm = normalize_skill(sub)
            if norm and norm.lower() not in seen:
                seen.add(norm.lower())
                normalized_skills.append(norm)

    return normalized_skills


def extract_skills_from_text(text: str | None) -> list[str]:
    """
    Scans raw text using pre-compiled regex patterns to deterministically
    detect all explicitly mentioned technical skills in CANONICAL_SKILL_TAXONOMY.
    Returns a list of canonical skill names.
    """
    if not text or not isinstance(text, str):
        return []

    found_skills: list[str] = []
    seen: set[str] = set()

    for pattern, canonical_name in _SKILL_PATTERNS:
        if pattern.search(text):
            if canonical_name.lower() not in seen:
                seen.add(canonical_name.lower())
                found_skills.append(canonical_name)

    return found_skills


def hybrid_extract_skills(
    raw_text: str | None,
    llm_skills: list[str] | None = None,
) -> list[str]:
    """
    Combines regex-scanned skills from raw text with LLM-extracted skills,
    returning a clean, deduplicated, canonical array.
    """
    regex_skills = extract_skills_from_text(raw_text)
    combined = regex_skills + (llm_skills or [])
    return normalize_skills_list(combined)
