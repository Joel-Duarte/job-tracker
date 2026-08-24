"""
Skill Canonicalization Engine.
Provides zero-latency taxonomy dictionary mapping for technology skills, aliases, acronyms,
and formatting normalization, alongside fast deterministic regex text scanning and hybrid extraction.
"""

import re

CANONICAL_SKILL_TAXONOMY: dict[str, str] = {
    # AI / ML / LLMs / Vector Search
    "rag": "Retrieval-Augmented Generation (RAG)",
    "retrieval augmented generation": "Retrieval-Augmented Generation (RAG)",
    "vector embeddings retrieval augmented (rag)": "Retrieval-Augmented Generation (RAG)",
    "llm": "Large Language Models (LLM)",
    "llms": "Large Language Models (LLM)",
    "large language models": "Large Language Models (LLM)",
    "large language model": "Large Language Models (LLM)",
    "genai": "Generative AI",
    "generative ai": "Generative AI",
    "nlp": "Natural Language Processing (NLP)",
    "natural language processing": "Natural Language Processing (NLP)",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence (AI)",
    "artificial intelligence": "Artificial Intelligence (AI)",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "scikit-learn": "scikit-learn",
    "scikitlearn": "scikit-learn",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    # DevOps / Infrastructure / Cloud
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "continuous integration": "CI/CD",
    "ci / cd pipelines": "CI/CD",
    "continuous integration / continuous deployment": "CI/CD",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "docker containers": "Docker",
    "containerization": "Docker",
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Microsoft Azure",
    "microsoft azure": "Microsoft Azure",
    "azure cloud": "Microsoft Azure",
    "gcp": "Google Cloud Platform (GCP)",
    "google cloud platform": "Google Cloud Platform (GCP)",
    "google cloud": "Google Cloud Platform (GCP)",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    # Databases & Storage
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "pgvector": "pgvector",
    "redis": "Redis",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "dynamodb": "Amazon DynamoDB",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "qdrant": "Qdrant",
    "chromadb": "ChromaDB",
    "elasticsearch": "Elasticsearch",
    # Frontend Technologies
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue 3": "Vue.js",
    "vue.js": "Vue.js",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "react native": "React Native",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "nuxt": "Nuxt.js",
    "nuxtjs": "Nuxt.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "svelte": "Svelte",
    "tailwindcss": "Tailwind CSS",
    "tailwind": "Tailwind CSS",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    # Languages & Runtime
    "python": "Python",
    "python3": "Python",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "c#": "C#",
    ".net": ".NET",
    "dotnet": ".NET",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    # Backend / APIs / Web Frameworks
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "express": "Express.js",
    "expressjs": "Express.js",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "rest": "REST API",
    "rest api": "REST API",
    "restful": "REST API",
    "oauth": "OAuth",
    "oauth2": "OAuth 2.0",
}

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


def normalize_skill(skill: str) -> str:
    """
    Normalizes a single skill string using a multi-stage pipeline:
    - Stage 1: Direct Taxonomy Match
    - Stage 3: Parenthetical Stripping
    - Stage 4: Boilerplate Noise Suffix Stripping
    - Stage 5: Fallback Casing Rules
    """
    if not skill or not isinstance(skill, str):
        return ""

    raw_trimmed = skill.strip()
    if not raw_trimmed:
        return ""

    lookup_key = raw_trimmed.lower()

    # Stage 1: Direct Taxonomy Match
    if lookup_key in CANONICAL_SKILL_TAXONOMY:
        return CANONICAL_SKILL_TAXONOMY[lookup_key]

    # Stage 3: Parenthetical Stripping
    no_parens = re.sub(r"\(.*?\)", "", raw_trimmed).strip()
    no_parens_key = no_parens.lower()
    if no_parens_key and no_parens_key in CANONICAL_SKILL_TAXONOMY:
        return CANONICAL_SKILL_TAXONOMY[no_parens_key]

    current = no_parens if no_parens else raw_trimmed
    current_key = current.lower()

    # Stage 4: Boilerplate Noise Suffix Stripping
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

    # Stage 2: Compound Splitting on " / ", " & ", or " + "
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
