from app.services.skill_normalizer import (
    extract_skills_from_text,
    hybrid_extract_skills,
    normalize_skill,
    normalize_skills_list,
)


def test_normalize_skill_taxonomy():
    assert normalize_skill("k8s") == "Kubernetes"
    assert normalize_skill("rag") == "Retrieval-Augmented Generation (RAG)"
    assert (
        normalize_skill("retrieval augmented generation")
        == "Retrieval-Augmented Generation (RAG)"
    )
    assert normalize_skill("ci/cd") == "CI/CD"
    assert normalize_skill("cicd") == "CI/CD"
    assert normalize_skill("llm") == "Large Language Models (LLM)"
    assert normalize_skill("postgres") == "PostgreSQL"
    assert normalize_skill("postgresql") == "PostgreSQL"
    assert normalize_skill("aws") == "AWS"
    assert normalize_skill("gcp") == "Google Cloud Platform (GCP)"
    assert normalize_skill("fastapi") == "FastAPI"


def test_parenthetical_and_noise_stripping():
    assert normalize_skill("CI/CD (GitHub Actions / GitLab)") == "CI/CD"
    assert normalize_skill("Postgres database") == "PostgreSQL"
    assert normalize_skill("AWS cloud") == "AWS"
    assert normalize_skill("AWS cloud infrastructure") == "AWS"
    assert normalize_skill("Vue.js development") == "Vue.js"


def test_compound_splitting():
    raw_list = ["Docker / Kubernetes", "CI/CD"]
    expected = ["Docker", "Kubernetes", "CI/CD"]
    assert normalize_skills_list(raw_list) == expected


def test_typo_correction_rapidfuzz():
    assert normalize_skill("Kuberenetes") == "Kubernetes"
    assert normalize_skill("Tensor Flow") == "TensorFlow"


def test_normalize_skill_casing_fallback():
    # Known taxonomy terms in dict
    assert normalize_skill("gRPC") == "gRPC"
    assert normalize_skill("PyTorch") == "PyTorch"
    assert normalize_skill("GraphQL") == "GraphQL"
    assert normalize_skill("OAuth") == "OAuth 2.0"

    # Unmatched terms
    assert normalize_skill("CustomFramework") == "CustomFramework"
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
    assert len(result) == len(set(s.lower() for s in result))
