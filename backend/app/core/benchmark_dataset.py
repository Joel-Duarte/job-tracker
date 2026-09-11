"""Standardized benchmark dataset for LLM hardware capacity testing."""

BENCHMARK_SENIOR_CV = {
    "candidate_name": "Alex Mercer",
    "summary": "Staff Distributed Systems & Infrastructure Engineer with 12+ years of experience designing high-throughput, fault-tolerant platforms in Go, Rust, and Python. Specialized in event-driven microservices, Kafka/Redpanda orchestration, Kubernetes operators, and PostgreSQL performance tuning.",
    "skills": [
        "Go",
        "Rust",
        "Python",
        "Distributed Systems",
        "PostgreSQL",
        "Kafka",
        "Kubernetes",
        "Redis",
        "gRPC",
        "Docker",
        "AWS",
        "Terraform",
    ],
    "experience": [
        {
            "company": "Nexus Streaming Systems",
            "title": "Staff Platform Engineer",
            "duration": "2021 - Present",
            "description": "Architected low-latency streaming platform handling 2.5M events/sec. Designed custom partitioned ingestion pipeline in Go reducing p99 latency by 45%. Led migration to bare-metal Kubernetes and CockroachDB clusters across 3 global regions.",
        },
        {
            "company": "CloudScale Financial",
            "title": "Senior Distributed Systems Engineer",
            "duration": "2017 - 2021",
            "description": "Led core ledger team rebuilding real-time settlement engine in Rust and PostgreSQL. Implemented zero-data-loss Raft replication protocol and asynchronous event bus supporting $40B in annual transaction volume.",
        },
        {
            "company": "DataPulse Analytics",
            "title": "Systems Software Engineer",
            "duration": "2013 - 2017",
            "description": "Developed distributed metrics aggregation daemon in C++ and Python. Optimized time-series indexing pipelines, slashing disk I/O by 60% across 5,000 production nodes.",
        },
    ],
    "education": [
        {
            "institution": "University of Washington",
            "degree": "B.S. in Computer Science & Engineering",
            "year": "2013",
        }
    ],
}

BENCHMARK_PLATFORM_JD = """
# Staff Infrastructure / Distributed Systems Engineer

## Company Overview
Apex Velocity is building next-generation infrastructure for real-time edge intelligence and ultra-low-latency event processing. We manage petabyte-scale distributed data fabrics powering autonomous robotics, real-time finance, and aerospace teleoperation.

## The Role
We are seeking an exceptional Staff Infrastructure Engineer to lead our Core Data Plane team. In this high-impact position, you will be responsible for the architecture, reliability, and sub-millisecond execution of our global distributed ingestion and storage platform.

## Responsibilities
- Architect, build, and operate globally distributed event streaming and state storage engines capable of sustained multi-million ops/sec throughput.
- Lead deep performance profiling and optimization initiatives across Linux kernel, network stack, eBPF, and storage subsystems.
- Define reliability standards, automated chaos testing, and disaster recovery architectures with strict 99.999% availability targets.
- Mentor senior engineers, drive architectural RFC reviews, and establish distributed systems best practices across the engineering organization.

## Requirements
- 10+ years of production experience in systems software, distributed computing, and high-throughput networking.
- Mastery of systems languages such as Go, Rust, or modern C++.
- Deep practical expertise with distributed coordination protocols (Raft, Paxos), LSM-tree storage engines, and streaming systems (Kafka, Redpanda).
- Proven track record operating mission-critical distributed databases (PostgreSQL, CockroachDB, ScyllaDB) at massive scale.
- Strong knowledge of Linux internals, memory management, zero-copy networking, and container orchestration (Kubernetes internals).

## Preferred Qualifications
- Active contributor to open-source systems software, databases, or runtime ecosystems.
- Experience with eBPF observability and Linux kernel tuning.
- Advanced degree in Computer Science, Systems Architecture, or equivalent field experience.
"""
