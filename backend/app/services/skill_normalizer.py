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
    Normalizes a single skill string.
    - Trims whitespace.
    - Performs exact lookup against CANONICAL_SKILL_TAXONOMY dictionary (lowercased key).
    - If unmatched and the string is all lowercase or all uppercase, applies title-casing.
    - Otherwise preserves original mixed-case / camelCase formatting.
    """
    if not skill or not isinstance(skill, str):
        return ""

    raw_trimmed = skill.strip()
    if not raw_trimmed:
        return ""

    lookup_key = raw_trimmed.lower()
    if lookup_key in CANONICAL_SKILL_TAXONOMY:
        return CANONICAL_SKILL_TAXONOMY[lookup_key]

    # Unmatched term handling:
    # Check if raw_trimmed is entirely lowercase or entirely uppercase
    if raw_trimmed.islower() or raw_trimmed.isupper():
        return raw_trimmed.title()

    # Preserve casing on mixed-case/camelCase terms
    return raw_trimmed


def normalize_skills_list(skills: list[str]) -> list[str]:
    """
    Normalizes an array of skills, removes duplicates (preserving canonical order),
    and filters empty entries.
    """
    if not skills or not isinstance(skills, list):
        return []

    normalized_skills: list[str] = []
    seen: set[str] = set()

    for s in skills:
        norm = normalize_skill(s)
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
