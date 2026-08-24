from app.services.skill_normalizer import (
    extract_skills_from_text,
    hybrid_extract_skills,
    normalize_skill,
    normalize_skills_list,
)


def test_normalize_skill_taxonomy():
    assert normalize_skill("rag") == "Retrieval-Augmented Generation (RAG)"
    assert (
        normalize_skill("retrieval augmented generation")
        == "Retrieval-Augmented Generation (RAG)"
    )
    assert (
        normalize_skill("vector embeddings retrieval augmented (rag)")
        == "Retrieval-Augmented Generation (RAG)"
    )

    assert normalize_skill("ci/cd") == "CI/CD"
    assert normalize_skill("cicd") == "CI/CD"
    assert normalize_skill("continuous integration") == "CI/CD"
    assert normalize_skill("ci / cd pipelines") == "CI/CD"

    assert normalize_skill("llm") == "Large Language Models (LLM)"
    assert normalize_skill("llms") == "Large Language Models (LLM)"
    assert normalize_skill("large language models") == "Large Language Models (LLM)"

    assert normalize_skill("k8s") == "Kubernetes"
    assert normalize_skill("kubernetes") == "Kubernetes"

    assert normalize_skill("postgres") == "PostgreSQL"
    assert normalize_skill("postgresql") == "PostgreSQL"
    assert normalize_skill("pgvector") == "pgvector"

    assert normalize_skill("azure") == "Microsoft Azure"
    assert normalize_skill("microsoft azure") == "Microsoft Azure"
    assert normalize_skill("azure cloud") == "Microsoft Azure"

    assert normalize_skill("docker") == "Docker"
    assert normalize_skill("docker containers") == "Docker"
    assert normalize_skill("containerization") == "Docker"

    assert normalize_skill("vue") == "Vue.js"
    assert normalize_skill("vuejs") == "Vue.js"
    assert normalize_skill("vue 3") == "Vue.js"
    assert normalize_skill("vue.js") == "Vue.js"

    assert normalize_skill("react") == "React"
    assert normalize_skill("reactjs") == "React"
    assert normalize_skill("react.js") == "React"

    assert normalize_skill("aws") == "AWS"
    assert normalize_skill("amazon web services") == "AWS"

    assert normalize_skill("gcp") == "Google Cloud Platform (GCP)"
    assert normalize_skill("google cloud platform") == "Google Cloud Platform (GCP)"

    assert normalize_skill("fastapi") == "FastAPI"
    assert normalize_skill("fast api") == "FastAPI"

    assert normalize_skill("ts") == "TypeScript"
    assert normalize_skill("typescript") == "TypeScript"

    assert normalize_skill("js") == "JavaScript"
    assert normalize_skill("javascript") == "JavaScript"


def test_normalize_skill_casing_fallback():
    # Known taxonomy terms in dict
    assert normalize_skill("gRPC") == "gRPC"
    assert normalize_skill("PyTorch") == "PyTorch"
    assert normalize_skill("GraphQL") == "GraphQL"
    assert normalize_skill("OAuth") == "OAuth"
    assert normalize_skill("Node.js") == "Node.js"

    # Unmatched terms
    assert normalize_skill("customtech") == "Customtech"
    assert normalize_skill("CUSTOMTECH") == "Customtech"
    assert normalize_skill("myCustomLib") == "myCustomLib"
    assert normalize_skill("   ") == ""
    assert normalize_skill(None) == ""


def test_normalize_skills_list():
    raw_list = [
        "  rag  ",
        "CI/CD",
        "cicd",
        "llm",
        "K8s",
        "k8s",
        "postgres",
        "pgvector",
        "",
        "   ",
        "React",
        "reactjs",
    ]
    expected = [
        "Retrieval-Augmented Generation (RAG)",
        "CI/CD",
        "Large Language Models (LLM)",
        "Kubernetes",
        "PostgreSQL",
        "pgvector",
        "React",
    ]
    assert normalize_skills_list(raw_list) == expected


def test_extract_skills_from_text():
    text = "Experience with Python, FastAPI, Docker, and CI/CD pipelines"
    extracted = extract_skills_from_text(text)
    assert "Python" in extracted
    assert "FastAPI" in extracted
    assert "Docker" in extracted
    assert "CI/CD" in extracted


def test_hybrid_extract_skills():
    raw_text = "We build LLM apps with Python, Postgres, and Docker containers."
    llm_skills = ["python", "Large Language Models", "PostgreSQL", "Tailwind CSS"]

    result = hybrid_extract_skills(raw_text, llm_skills)

    assert "Python" in result
    assert "Large Language Models (LLM)" in result
    assert "PostgreSQL" in result
    assert "Docker" in result
    assert "Tailwind CSS" in result
    # Check no duplicate variations
    assert len(result) == len(set(s.lower() for s in result))
