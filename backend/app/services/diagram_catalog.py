"""Canonical architecture component taxonomy, matching helpers, Flow JSON normalizer, and penalty math."""

from __future__ import annotations

import re
from typing import Any

DIAGRAM_HINT_SINGLE_PENALTY: float = 3.0
DIAGRAM_HINT_BULK_MIN_PENALTY: float = 18.0
DIAGRAM_HINT_MAX_PENALTY: float = 25.0

CANONICAL_CATEGORIES: list[dict[str, str]] = [
    {"id": "clients_edge", "label": "Clients & Edge"},
    {"id": "traffic_api", "label": "Traffic & API"},
    {"id": "compute_services", "label": "Compute & Services"},
    {"id": "caching_memory", "label": "Caching & Memory"},
    {"id": "databases_storage", "label": "Databases & Storage"},
    {"id": "messaging_streaming", "label": "Messaging & Streaming"},
    {"id": "search_analytics_ops", "label": "Search, Analytics & Ops"},
]

CANONICAL_DIAGRAM_BLOCKS: list[dict[str, Any]] = [
    # 1. Clients & Edge (5)
    {
        "type_id": "web_client",
        "label": "Web / Browser Client",
        "category": "clients_edge",
        "icon": "globe",
        "default_role": "Browser SPA or SSR web client initiating user traffic.",
        "keywords": ["web client", "browser", "frontend", "spa", "client app", "user"],
    },
    {
        "type_id": "mobile_client",
        "label": "Mobile Client",
        "category": "clients_edge",
        "icon": "smartphone",
        "default_role": "iOS/Android mobile application sending API or WebSocket traffic.",
        "keywords": ["mobile", "ios", "android", "sdk", "mobile app"],
    },
    {
        "type_id": "dns",
        "label": "DNS / GeoDNS",
        "category": "clients_edge",
        "icon": "compass",
        "default_role": "Resolves domain names to nearest healthy regional PoP or VIP.",
        "keywords": ["dns", "route53", "geodns", "anycast"],
    },
    {
        "type_id": "cdn",
        "label": "CDN / Edge Cache",
        "category": "clients_edge",
        "icon": "zap",
        "default_role": "Caches static assets, media segments, or cacheable responses near users.",
        "keywords": ["cdn", "cloudfront", "cloudflare", "edge cache", "edge network"],
    },
    {
        "type_id": "waf_ddos",
        "label": "WAF / DDoS Shield",
        "category": "clients_edge",
        "icon": "shield",
        "default_role": "Filters malicious payloads, bot bursts, and L7/L4 volumetric attacks.",
        "keywords": ["waf", "ddos", "firewall", "bot protection", "shield"],
    },
    # 2. Traffic & API (5)
    {
        "type_id": "load_balancer",
        "label": "Load Balancer",
        "category": "traffic_api",
        "icon": "network",
        "default_role": "Distributes inbound traffic across healthy backend instances (L4/L7).",
        "keywords": ["load balancer", "alb", "nlb", "elb", "nginx", "haproxy", "envoy"],
    },
    {
        "type_id": "api_gateway",
        "label": "API Gateway",
        "category": "traffic_api",
        "icon": "door-open",
        "default_role": "Terminates TLS, routes REST/GraphQL/gRPC calls, and enforces auth & quotas.",
        "keywords": ["api gateway", "gateway", "kong", "apigee", "bff", "ingress"],
    },
    {
        "type_id": "rate_limiter",
        "label": "Rate Limiter",
        "category": "traffic_api",
        "icon": "gauge",
        "default_role": "Throttles per-user/IP/tenant requests using token bucket or sliding window.",
        "keywords": ["rate limit", "rate limiter", "throttler", "quota"],
    },
    {
        "type_id": "auth_service",
        "label": "Auth / IAM Service",
        "category": "traffic_api",
        "icon": "key-round",
        "default_role": "Issues/validates JWTs, OAuth2 tokens, API keys, and RBAC policies.",
        "keywords": [
            "auth",
            "authentication",
            "authorization",
            "iam",
            "oauth",
            "jwt",
            "idp",
        ],
    },
    {
        "type_id": "realtime_gateway",
        "label": "WebSocket / Push Gateway",
        "category": "traffic_api",
        "icon": "radio",
        "default_role": "Holds persistent WebSocket/SSE/MQTT connections for real-time delivery.",
        "keywords": ["websocket", "sse", "push", "realtime gateway", "socket", "mqtt"],
    },
    {
        "type_id": "content_filter",
        "label": "URL / Payload Safety Filter",
        "category": "traffic_api",
        "icon": "shield-alert",
        "default_role": "Checks URLs, payloads, or uploads against phishing/malware blocklists and abuse policies.",
        "keywords": [
            "blocklist",
            "blacklist",
            "malicious",
            "phishing",
            "safety filter",
            "moderation",
            "virus",
            "spam filter",
            "url filter",
            "abuse",
        ],
    },
    # 3. Compute & Services (6)
    {
        "type_id": "app_service",
        "label": "Stateless App Service",
        "category": "compute_services",
        "icon": "server",
        "default_role": "Core domain microservice handling stateless business logic.",
        "keywords": [
            "app service",
            "microservice",
            "service",
            "backend",
            "api server",
            "write service",
            "read service",
            "redirect service",
            "shortener",
        ],
    },
    {
        "type_id": "async_worker",
        "label": "Background Worker Pool",
        "category": "compute_services",
        "icon": "cog",
        "default_role": "Consumes async jobs for retries, enrichment, notifications, or ETL.",
        "keywords": ["worker", "consumer", "job runner", "background", "processor"],
    },
    {
        "type_id": "scheduler",
        "label": "Scheduler / TTL Sweeper",
        "category": "compute_services",
        "icon": "clock",
        "default_role": "Triggers delayed tasks, link TTL/expiration sweeps, retention cleanup, or periodic jobs.",
        "keywords": [
            "scheduler",
            "cron",
            "timer",
            "ttl",
            "expiration",
            "expiry",
            "cleanup",
            "retention",
            "lifecycle",
            "delayed job",
            "sweeper",
        ],
    },
    {
        "type_id": "id_generator",
        "label": "Unique ID / Key Generator",
        "category": "compute_services",
        "icon": "hash",
        "default_role": "Generates globally unique sortable IDs or collision-free short codes.",
        "keywords": [
            "id generator",
            "key generation",
            "kgs",
            "snowflake",
            "base62",
            "uuid",
        ],
    },
    {
        "type_id": "ml_inference",
        "label": "ML / Ranking Service",
        "category": "compute_services",
        "icon": "brain",
        "default_role": "Scores embeddings, fraud risk, personalization ranking, or LLM inference.",
        "keywords": [
            "ml",
            "model",
            "inference",
            "ranking",
            "embedding",
            "llm",
            "fraud",
            "rag",
        ],
    },
    {
        "type_id": "media_transcoder",
        "label": "Media / Document Processor",
        "category": "compute_services",
        "icon": "film",
        "default_role": "Chunks, transcodes, thumbnails, or parses uploaded binaries.",
        "keywords": [
            "transcoder",
            "ffmpeg",
            "media",
            "video",
            "image",
            "ocr",
            "parser",
        ],
    },
    # 4. Caching & Memory (4)
    {
        "type_id": "distributed_cache",
        "label": "Distributed Cache (Redis)",
        "category": "caching_memory",
        "icon": "bolt",
        "default_role": "In-memory KV store for hot reads, sessions, locks, and sub-ms lookups.",
        "keywords": ["redis", "memcached", "cache", "distributed cache", "in-memory"],
    },
    {
        "type_id": "local_cache",
        "label": "Local / L1 In-Process Cache",
        "category": "caching_memory",
        "icon": "cpu",
        "default_role": "Ultra-fast local memory cache shielding remote cache/DB from hot keys.",
        "keywords": ["l1 cache", "local cache", "in-process", "caffeine"],
    },
    {
        "type_id": "feature_store",
        "label": "Feature / State Store",
        "category": "caching_memory",
        "icon": "layers",
        "default_role": "Low-latency online store for ML features, counters, or session state.",
        "keywords": ["feature store", "online store", "state store", "leaderboard"],
    },
    {
        "type_id": "bloom_filter",
        "label": "Bloom Filter / Dedup Index",
        "category": "caching_memory",
        "icon": "filter",
        "default_role": "Compact probabilistic membership check avoiding costly DB misses.",
        "keywords": ["bloom filter", "dedup", "deduplication", "seen set"],
    },
    # 5. Databases & Storage (7)
    {
        "type_id": "relational_db",
        "label": "Primary Relational DB",
        "category": "databases_storage",
        "icon": "database",
        "default_role": "ACID relational store with primary-replica or sharded topology.",
        "keywords": [
            "postgres",
            "postgresql",
            "mysql",
            "sql",
            "rds",
            "relational",
            "acid",
        ],
    },
    {
        "type_id": "read_replica",
        "label": "DB Read Replica",
        "category": "databases_storage",
        "icon": "copy",
        "default_role": "Serves scaled read queries asynchronously replicated from the primary.",
        "keywords": ["read replica", "replica", "follower", "read pool"],
    },
    {
        "type_id": "nosql_kv",
        "label": "NoSQL / Wide-Column / KV DB",
        "category": "databases_storage",
        "icon": "table",
        "default_role": "Horizontally partitioned KV/document/wide-column store (Dynamo/Cassandra).",
        "keywords": [
            "nosql",
            "dynamodb",
            "cassandra",
            "scylladb",
            "mongodb",
            "kv store",
            "key-value",
        ],
    },
    {
        "type_id": "object_storage",
        "label": "Object / Blob Storage",
        "category": "databases_storage",
        "icon": "hard-drive",
        "default_role": "Durable S3-compatible blob store for media, backups, and data lake files.",
        "keywords": ["s3", "object storage", "blob", "gcs", "minio", "archive"],
    },
    {
        "type_id": "timeseries_db",
        "label": "Time-Series DB",
        "category": "databases_storage",
        "icon": "activity",
        "default_role": "Append-optimized store for metrics, telemetry, or IoT event series.",
        "keywords": [
            "timeseries",
            "time-series",
            "timescaledb",
            "influxdb",
            "clickhouse",
            "prometheus",
        ],
    },
    {
        "type_id": "vector_db",
        "label": "Vector Index / DB",
        "category": "databases_storage",
        "icon": "sparkles",
        "default_role": "ANN similarity index (HNSW/IVF) for semantic retrieval and RAG.",
        "keywords": [
            "vector",
            "pgvector",
            "qdrant",
            "pinecone",
            "milvus",
            "faiss",
            "ann",
        ],
    },
    {
        "type_id": "consensus_store",
        "label": "Coordination / Lease Store",
        "category": "databases_storage",
        "icon": "lock",
        "default_role": "Raft/Paxos metadata store for leader election, locks, and shard maps.",
        "keywords": [
            "etcd",
            "zookeeper",
            "consul",
            "coordination",
            "lease",
            "lock service",
        ],
    },
    # 6. Messaging & Streaming (5)
    {
        "type_id": "message_queue",
        "label": "Task Queue",
        "category": "messaging_streaming",
        "icon": "inbox",
        "default_role": "Decouples producers from consumers with at-least-once delivery & visibility timeout.",
        "keywords": [
            "queue",
            "sqs",
            "rabbitmq",
            "task queue",
            "message queue",
            "async queue",
            "click analytics",
            "click counting",
        ],
    },
    {
        "type_id": "event_stream",
        "label": "Event Log / Kafka Stream",
        "category": "messaging_streaming",
        "icon": "git-commit-horizontal",
        "default_role": "Partitioned append-only log for high-throughput replayable event streams.",
        "keywords": [
            "kafka",
            "kinesis",
            "pulsar",
            "redpanda",
            "event stream",
            "event log",
            "commit log",
        ],
    },
    {
        "type_id": "pubsub_bus",
        "label": "Pub/Sub Fan-out Bus",
        "category": "messaging_streaming",
        "icon": "share-2",
        "default_role": "Broadcasts topic events to multiple independent downstream subscribers.",
        "keywords": ["pub/sub", "pubsub", "sns", "fanout", "fan-out", "topic"],
    },
    {
        "type_id": "stream_processor",
        "label": "Stream Processor (Flink)",
        "category": "messaging_streaming",
        "icon": "workflow",
        "default_role": "Stateful windowed aggregation, joins, and CEP over live event streams.",
        "keywords": [
            "flink",
            "spark streaming",
            "kafka streams",
            "stream processor",
            "windowed stream",
            "cep",
        ],
    },
    {
        "type_id": "dlq",
        "label": "Dead-Letter Queue (DLQ)",
        "category": "messaging_streaming",
        "icon": "alert-triangle",
        "default_role": "Isolates poison messages exceeding retry bounds for replay and triage.",
        "keywords": ["dlq", "dead letter", "dead-letter", "poison"],
    },
    # 7. Search, Analytics & Ops (4)
    {
        "type_id": "search_engine",
        "label": "Full-Text / Geo Search",
        "category": "search_analytics_ops",
        "icon": "search",
        "default_role": "Inverted/spatial index (Elasticsearch/OpenSearch) for search and filtering.",
        "keywords": [
            "elasticsearch",
            "opensearch",
            "solr",
            "search engine",
            "full-text",
            "inverted index",
        ],
    },
    {
        "type_id": "olap_warehouse",
        "label": "Analytics / OLAP Store",
        "category": "search_analytics_ops",
        "icon": "bar-chart-3",
        "default_role": "Columnar analytical warehouse (BigQuery/ClickHouse/Snowflake) for rollups.",
        "keywords": [
            "analytics",
            "olap",
            "warehouse",
            "bigquery",
            "snowflake",
            "parquet",
            "rollup",
        ],
    },
    {
        "type_id": "cdc_connector",
        "label": "Outbox / CDC Pipeline",
        "category": "search_analytics_ops",
        "icon": "repeat",
        "default_role": "Streams DB WAL changes reliably (Debezium/Outbox) without dual-write races.",
        "keywords": ["cdc", "debezium", "outbox", "change data capture", "wal"],
    },
    {
        "type_id": "observability",
        "label": "Metrics, Logs & Tracing",
        "category": "search_analytics_ops",
        "icon": "eye",
        "default_role": "Collects OpenTelemetry traces, p99 latency SLO metrics, alerts, and audit logs.",
        "keywords": [
            "observability",
            "monitoring",
            "telemetry",
            "metrics",
            "logging",
            "tracing",
            "alerts",
        ],
    },
]

BLOCKS_BY_TYPE_ID: dict[str, dict[str, Any]] = {
    block["type_id"]: block for block in CANONICAL_DIAGRAM_BLOCKS
}


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(t) > 1}


def match_component_to_catalog(
    name: str,
    palette_extensions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Map an expected component name or custom extension to its canonical block metadata."""
    cleaned = str(name or "").strip()
    lower_name = cleaned.lower()

    # Check challenge-specific palette extensions first when supplied.
    for ext in palette_extensions or []:
        if not isinstance(ext, dict):
            continue
        ext_label = str(ext.get("label") or ext.get("name") or "").strip()
        ext_type = str(ext.get("type_id") or "").strip()
        if ext_label and (
            ext_label.lower() == lower_name
            or ext_label.lower() in lower_name
            or lower_name in ext_label.lower()
        ):
            return {
                "name": cleaned or ext_label,
                "type_id": ext_type or "custom",
                "label": ext_label,
                "category": str(ext.get("category") or "compute_services"),
                "icon": str(ext.get("icon") or "box"),
                "hint_role": str(
                    ext.get("default_role")
                    or ext.get("hint_role")
                    or f"Domain-specific block: {ext_label}."
                ),
                "is_custom": ext_type not in BLOCKS_BY_TYPE_ID,
            }

    # Exact or substring keyword match against canonical blocks.
    best_block: dict[str, Any] | None = None
    best_score = 0
    name_tokens = _tokenize(cleaned)

    for block in CANONICAL_DIAGRAM_BLOCKS:
        score = 0
        if block["label"].lower() == lower_name or block["type_id"] == lower_name:
            score += 100
        for kw in block.get("keywords", []):
            if kw in lower_name:
                score += 20 + len(kw)
        kw_tokens: set[str] = set()
        for kw in block.get("keywords", []):
            kw_tokens |= _tokenize(kw)
        kw_tokens |= _tokenize(block["label"])
        overlap = len(name_tokens & kw_tokens)
        score += overlap * 5
        if score > best_score:
            best_score = score
            best_block = block

    if best_block and best_score >= 10:
        return {
            "name": cleaned or best_block["label"],
            "type_id": best_block["type_id"],
            "label": best_block["label"],
            "category": best_block["category"],
            "icon": best_block["icon"],
            "hint_role": best_block["default_role"],
            "is_custom": False,
        }

    # Fallback custom block with sensible inferred category/icon.
    category = "compute_services"
    icon = "box"
    if any(
        w in lower_name for w in ("db", "store", "storage", "table", "shard", "wal")
    ):
        category, icon = "databases_storage", "database"
    elif any(w in lower_name for w in ("cache", "redis", "memory")):
        category, icon = "caching_memory", "bolt"
    elif any(
        w in lower_name for w in ("queue", "kafka", "stream", "event", "bus", "topic")
    ):
        category, icon = "messaging_streaming", "git-commit-horizontal"
    elif any(
        w in lower_name for w in ("gateway", "balancer", "proxy", "router", "auth")
    ):
        category, icon = "traffic_api", "network"
    elif any(
        w in lower_name for w in ("client", "cdn", "dns", "edge", "browser", "mobile")
    ):
        category, icon = "clients_edge", "globe"
    elif any(
        w in lower_name for w in ("search", "index", "metric", "log", "analytics")
    ):
        category, icon = "search_analytics_ops", "search"

    return {
        "name": cleaned or "Custom Component",
        "type_id": "custom",
        "label": cleaned or "Custom Component",
        "category": category,
        "icon": icon,
        "hint_role": f"Add a block representing '{cleaned}' and connect it cleanly in the data flow.",
        "is_custom": True,
    }


def node_matches_expected(node: dict[str, Any], expected_name: str) -> bool:
    """Return True if a canvas node satisfies an expected component requirement."""
    expected_match = match_component_to_catalog(expected_name)
    exp_tokens = _tokenize(expected_name)
    node_label = str(node.get("label") or "")
    node_tech = str(node.get("tech_stack") or "")
    node_notes = str(node.get("notes") or "")
    node_type = str(node.get("type_id") or "")

    if node_type and node_type != "custom" and node_type == expected_match["type_id"]:
        return True

    combined = f"{node_label} {node_tech} {node_notes}".lower()
    if expected_name.lower() in combined:
        return True
    node_tokens = _tokenize(combined)
    if exp_tokens and len(exp_tokens & node_tokens) >= max(1, len(exp_tokens) // 2):
        # Avoid trivial 1-word generic matches like "service" or "data".
        generic = {"service", "system", "layer", "data", "store", "manager"}
        meaningful = (exp_tokens & node_tokens) - generic
        if meaningful:
            return True
    return False


def normalize_flow_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize submitted canvas nodes, edges, notes, and viewport into normalized Flow JSON."""
    raw_nodes = list(raw_payload.get("nodes") or [])
    raw_edges = list(raw_payload.get("edges") or [])

    normalized_nodes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for idx, node in enumerate(raw_nodes, start=1):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or f"node-{idx}").strip()
        if not node_id or node_id in seen_ids:
            node_id = f"node-{idx}"
        seen_ids.add(node_id)

        type_id = str(node.get("type_id") or "custom").strip() or "custom"
        catalog_meta = BLOCKS_BY_TYPE_ID.get(type_id)
        label = str(node.get("label") or "").strip() or (
            catalog_meta["label"] if catalog_meta else f"Component {idx}"
        )
        category = str(
            node.get("category")
            or (catalog_meta["category"] if catalog_meta else "compute_services")
        ).strip()
        icon = str(
            node.get("icon") or (catalog_meta["icon"] if catalog_meta else "box")
        ).strip()
        pos = node.get("position") if isinstance(node.get("position"), dict) else {}
        x = float(pos.get("x", (idx % 4) * 240))
        y = float(pos.get("y", (idx // 4) * 140))

        normalized_nodes.append(
            {
                "id": node_id,
                "type_id": type_id,
                "label": label,
                "category": category,
                "icon": icon,
                "tech_stack": str(node.get("tech_stack") or "").strip(),
                "notes": str(node.get("notes") or "").strip(),
                "is_custom": bool(
                    node.get("is_custom", type_id not in BLOCKS_BY_TYPE_ID)
                ),
                "position": {"x": round(x, 1), "y": round(y, 1)},
            }
        )

    valid_node_ids = {n["id"] for n in normalized_nodes}
    normalized_edges: list[dict[str, Any]] = []
    for idx, edge in enumerate(raw_edges, start=1):
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("source") or "").strip()
        target = str(edge.get("target") or "").strip()
        if (
            not source
            or not target
            or source not in valid_node_ids
            or target not in valid_node_ids
        ):
            continue
        mode = str(edge.get("delivery_mode") or "sync").strip().lower()
        if mode not in {"sync", "async"}:
            mode = "sync"
        normalized_edges.append(
            {
                "id": str(edge.get("id") or f"edge-{idx}").strip(),
                "source": source,
                "target": target,
                "source_handle": str(edge.get("source_handle") or "").strip() or None,
                "target_handle": str(edge.get("target_handle") or "").strip() or None,
                "protocol": str(edge.get("protocol") or "").strip(),
                "delivery_mode": mode,
                "label": str(edge.get("label") or "").strip(),
            }
        )

    return {
        "schema_version": 1,
        "nodes": normalized_nodes,
        "edges": normalized_edges,
        "notes": str(raw_payload.get("notes") or "").strip(),
        "viewport": raw_payload.get("viewport") or {"x": 0, "y": 0, "zoom": 1},
    }


def summarize_diagram_flow(flow_payload: dict[str, Any]) -> dict[str, Any]:
    """Produce deterministic components, directed flows, and topology diagnostics from Flow JSON."""
    nodes = list(flow_payload.get("nodes") or [])
    edges = list(flow_payload.get("edges") or [])
    node_map = {
        str(n.get("id")): n for n in nodes if isinstance(n, dict) and n.get("id")
    }

    incoming: dict[str, int] = {nid: 0 for nid in node_map}
    outgoing: dict[str, int] = {nid: 0 for nid in node_map}
    flows_readable: list[str] = []

    for edge in edges:
        src_id = str(edge.get("source") or "")
        dst_id = str(edge.get("target") or "")
        if src_id not in node_map or dst_id not in node_map:
            continue
        outgoing[src_id] += 1
        incoming[dst_id] += 1
        src_label = node_map[src_id].get("label", src_id)
        dst_label = node_map[dst_id].get("label", dst_id)
        protocol = str(edge.get("protocol") or "").strip()
        mode = edge.get("delivery_mode") or "sync"
        label = str(edge.get("label") or "").strip()
        meta = ", ".join(part for part in (protocol, mode) if part)
        desc = f"{src_label} -> {dst_label} [{meta}]"
        if label:
            desc += f": {label}"
        flows_readable.append(desc)

    isolated = [
        node_map[nid].get("label", nid)
        for nid in node_map
        if len(node_map) > 1 and incoming[nid] == 0 and outgoing[nid] == 0
    ]
    entry_nodes = [
        node_map[nid].get("label", nid)
        for nid in node_map
        if incoming[nid] == 0 and outgoing[nid] > 0
    ]
    terminal_sinks = [
        node_map[nid].get("label", nid)
        for nid in node_map
        if outgoing[nid] == 0 and incoming[nid] > 0
    ]

    components_list = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        comp_desc = str(n.get("label") or "")
        if n.get("tech_stack"):
            comp_desc += f" ({n['tech_stack']})"
        if n.get("notes"):
            comp_desc += f" — {n['notes']}"
        components_list.append(comp_desc)

    diagnostics: list[str] = []
    if len(nodes) == 0:
        diagnostics.append("Diagram contains zero components.")
    if isolated:
        diagnostics.append(f"Isolated / unwired component(s): {', '.join(isolated)}.")
    if len(nodes) > 1 and not edges:
        diagnostics.append(
            "Multiple components placed without any connecting data flows."
        )

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "components": components_list,
        "directed_flows": flows_readable,
        "entry_nodes": entry_nodes,
        "terminal_sinks": terminal_sinks,
        "isolated_nodes": isolated,
        "topology_diagnostics": diagnostics,
    }


def compute_diagram_hint_penalty(
    hints_used_count: int,
    revealed_all_bank: bool,
    mode: str = "ADAPTIVE",
) -> float:
    """Compute cumulative capped score penalty for diagram guidance (0.0 in PRACTICE mode)."""
    if str(mode or "ADAPTIVE").strip().upper() == "PRACTICE":
        return 0.0
    single_penalty = max(0, int(hints_used_count)) * DIAGRAM_HINT_SINGLE_PENALTY
    if revealed_all_bank:
        raw = max(DIAGRAM_HINT_BULK_MIN_PENALTY, single_penalty)
    else:
        raw = single_penalty
    return round(min(DIAGRAM_HINT_MAX_PENALTY, raw), 1)


_SYNTHESIS_RULES: list[dict[str, Any]] = [
    {
        "type_id": "web_client",
        "patterns": (),
        "always_core": False,
        "why": "Entry point for users invoking create and read flows.",
        "checklist": ["Distinguish read traffic from write/creation traffic"],
    },
    {
        "type_id": "cdn",
        "patterns": (
            "global",
            "cdn",
            "edge",
            "< 30ms",
            "<30ms",
            "< 50ms",
            "sub-50ms",
            "media",
            "video",
        ),
        "why": "Required for global low-latency read delivery and offloading hot static/redirect traffic.",
        "checklist": [
            "Specify cache TTL / invalidation policy vs custom redirect tracking"
        ],
    },
    {
        "type_id": "load_balancer",
        "patterns": ("99.9", "high availability", "qps", "horizontal", "scale"),
        "why": "Distributes inbound traffic cleanly across healthy stateless service instances.",
        "checklist": [
            "Use L7 load balancing with health checks across multi-AZ targets"
        ],
    },
    {
        "type_id": "api_gateway",
        "patterns": ("api", "rest", "graphql", "auth", "quota", "routing"),
        "why": "Terminates TLS, enforces request validation/throttling, and routes read vs write APIs.",
        "checklist": [
            "Route creation writes separately from hot read endpoints if scaled independently"
        ],
    },
    {
        "type_id": "rate_limiter",
        "patterns": (
            "rate limit",
            "throttl",
            "quota",
            "anti-scrap",
            "scraping",
            "enumeration",
            "ddos",
            "abuse",
        ),
        "why": "Protects write/redirect paths from abusive bursts, scraping, or noisy neighbors.",
        "checklist": [
            "Apply token bucket or sliding window counters keyed by IP/API key"
        ],
    },
    {
        "type_id": "content_filter",
        "patterns": (
            "malicious",
            "phishing",
            "blocklist",
            "blacklist",
            "safety",
            "moderation",
            "virus",
            "spam",
        ),
        "why": "Required by security constraints to reject phishing/malicious targets before storing or redirecting.",
        "checklist": [
            "Check URLs against a fast blocklist/lookup before minting or serving redirects"
        ],
    },
    {
        "type_id": "scheduler",
        "patterns": (
            "ttl",
            "expir",
            "retention",
            "cleanup",
            "sweeper",
            "cron",
            "scheduled",
        ),
        "why": "Required by lifecycle/TTL rules to purge expired records and reclaim storage safely.",
        "checklist": [
            "Combine lazy expiration check on read (return 410/404) with periodic background TTL sweeps"
        ],
    },
    {
        "type_id": "read_replica",
        "patterns": (
            "read-heavy",
            "100:1",
            "10:1",
            "99.99%",
            "99.95%",
            "replica",
            "failover",
            "single point of failure",
        ),
        "why": "Absorbs cache-miss read load and eliminates single-DB read/failover bottlenecks.",
        "checklist": [
            "Document asynchronous replication lag tolerance and Primary -> Replica failover"
        ],
    },
    {
        "type_id": "message_queue",
        "patterns": (
            "async",
            "eventual",
            "click count",
            "click analytics",
            "background",
            "webhook",
            "job queue",
        ),
        "why": "Decouples non-blocking background work (analytics, webhooks) from the critical read/write latency path.",
        "checklist": [
            "Keep producers non-blocking; pair with workers and DLQ/retry handling"
        ],
    },
    {
        "type_id": "async_worker",
        "patterns": (
            "async",
            "eventual",
            "click count",
            "click analytics",
            "background",
            "worker",
            "consumer",
        ),
        "why": "Consumes queued events to batch-update counters, run cleanup, or handle retries off the hot path.",
        "checklist": ["Batch DB updates and design idempotent consumers"],
    },
]

_STATEFUL_CHECKLISTS: dict[str, list[str]] = {
    "id_generator": [
        "Avoid Single Point of Failure: note pre-allocated key ranges, ZooKeeper/etcd leases, or active-active standby instances",
        "Ensure non-sequential/non-predictable Base62 codes if link privacy is required",
    ],
    "relational_db": [
        "Note Primary-Replica topology or sharding key (e.g. short_code) to prevent single-DB SPOF",
        "Store expires_at/TTL metadata cleanly for lifecycle enforcement",
    ],
    "nosql_kv": [
        "Specify partition key and replication factor / Multi-AZ quorum strategy",
    ],
    "distributed_cache": [
        "Document eviction policy (LRU/LFU), TTL alignment, and stampede mitigation (singleflight / circuit breaker)",
    ],
    "read_replica": [
        "Route read-miss fallback queries here while writes go strictly to Primary DB",
    ],
}

_RESILIENCE_TOKENS = (
    "standby",
    "replica",
    "pre-alloc",
    "range",
    "shard",
    "multi-az",
    "raft",
    "etcd",
    "zookeeper",
    "cluster",
    "failover",
    "active-active",
    "quorum",
    "redundant",
    "singleflight",
    "evict",
    "lru",
)


def _split_composite_component_specs(raw_name: str) -> list[str]:
    """Split composite multi-layer component descriptions into atomic required components."""
    cleaned = str(raw_name or "").strip()
    if not cleaned:
        return []
    lower = cleaned.lower()

    # Keep single-component tech alternatives like "Primary database (PostgreSQL / DynamoDB)" together,
    # while stripping parens to inspect architectural layer slashes/arrows outside parentheses.
    outside_parens = re.sub(r"\([^)]*\)", "", cleaned).strip()
    if "->" in outside_parens:
        arrow_parts = [
            p.strip() for p in re.split(r"\s*->\s*", outside_parens) if p.strip()
        ]
        if len(arrow_parts) >= 2:
            resolved_arrow_types = [
                match_component_to_catalog(p)["type_id"] for p in arrow_parts
            ]
            if (
                len(set(resolved_arrow_types)) >= 2
                and "custom" not in resolved_arrow_types
            ):
                return [
                    BLOCKS_BY_TYPE_ID[tid]["label"]
                    for tid in dict.fromkeys(resolved_arrow_types)
                ]

    if "/" not in outside_parens:
        return [cleaned]

    if "api gateway" in lower and "load balancer" in lower:
        return ["Load Balancer", "API Gateway"]
    if "queue" in lower and "worker" in lower:
        return ["Task Queue", "Background Worker Pool"]
    if "client" in lower and "cdn" in lower:
        return ["Web / Browser Client", "CDN / Edge Cache"]

    parts = [p.strip() for p in outside_parens.split("/") if p.strip()]
    if len(parts) < 2:
        return [cleaned]

    resolved_types = [match_component_to_catalog(p)["type_id"] for p in parts]
    if len(set(resolved_types)) >= 2 and "custom" not in resolved_types:
        return [
            BLOCKS_BY_TYPE_ID[tid]["label"] for tid in dict.fromkeys(resolved_types)
        ]
    return [cleaned]


def _flatten_text_values(values: Any) -> str:
    if isinstance(values, str):
        return values
    if isinstance(values, list):
        return " ".join(_flatten_text_values(v) for v in values)
    if isinstance(values, dict):
        return " ".join(f"{k} {_flatten_text_values(v)}" for k, v in values.items())
    return str(values or "")


def _build_component_entry(
    raw_name: str,
    palette_extensions: list[dict[str, Any]] | None,
    why_required: str,
    extra_checklist: list[str] | None = None,
) -> dict[str, Any]:
    matched = match_component_to_catalog(raw_name, palette_extensions)
    checklist: list[str] = []
    for item in [
        *(_STATEFUL_CHECKLISTS.get(matched["type_id"], [])),
        *(extra_checklist or []),
    ]:
        clean_item = str(item or "").strip()
        if clean_item and clean_item not in checklist:
            checklist.append(clean_item)
    return {
        **matched,
        "why_required": why_required or matched.get("hint_role") or "",
        "config_checklist": checklist,
    }


def _synthesize_expected_paths(
    required_components: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Synthesize concrete Read / Write / Async-Lifecycle path steps from required component types."""
    by_type: dict[str, dict[str, Any]] = {}
    for comp in required_components:
        tid = str(comp.get("type_id") or "")
        if tid and tid not in by_type:
            by_type[tid] = comp

    has = by_type.__contains__
    paths: list[dict[str, Any]] = []

    ingress_target = (
        ("load_balancer", by_type["load_balancer"]["label"])
        if has("load_balancer")
        else (
            ("api_gateway", by_type["api_gateway"]["label"])
            if has("api_gateway")
            else (
                ("app_service", by_type["app_service"]["label"])
                if has("app_service")
                else None
            )
        )
    )

    # 1. Read Path
    read_steps: list[dict[str, Any]] = []
    if has("web_client") and has("cdn") and ingress_target:
        read_steps.append(
            {
                "source_type_id": "web_client",
                "source_label": by_type["web_client"]["label"],
                "target_type_id": "cdn",
                "target_label": by_type["cdn"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Request / redirect lookup",
                "rationale": "Serve cacheable edge responses close to users first.",
            }
        )
        read_steps.append(
            {
                "source_type_id": "cdn",
                "source_label": by_type["cdn"]["label"],
                "target_type_id": ingress_target[0],
                "target_label": ingress_target[1],
                "delivery_mode": "sync",
                "suggested_label": "Origin miss forward",
                "rationale": "Edge misses route through your load balancer / gateway, never straight to internal caches or DBs.",
            }
        )
    elif has("web_client") and ingress_target:
        read_steps.append(
            {
                "source_type_id": "web_client",
                "source_label": by_type["web_client"]["label"],
                "target_type_id": ingress_target[0],
                "target_label": ingress_target[1],
                "delivery_mode": "sync",
                "suggested_label": "HTTPS request",
                "rationale": "Client traffic enters through edge load balancer / gateway.",
            }
        )

    if has("load_balancer") and has("api_gateway"):
        read_steps.append(
            {
                "source_type_id": "load_balancer",
                "source_label": by_type["load_balancer"]["label"],
                "target_type_id": "api_gateway",
                "target_label": by_type["api_gateway"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Balanced traffic",
                "rationale": "Load Balancer spreads connections across API Gateway nodes.",
            }
        )
    if has("api_gateway") and has("app_service"):
        read_steps.append(
            {
                "source_type_id": "api_gateway",
                "source_label": by_type["api_gateway"]["label"],
                "target_type_id": "app_service",
                "target_label": by_type["app_service"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Routed API call",
                "rationale": "Gateway forwards validated read/write requests to stateless services.",
            }
        )
    elif has("load_balancer") and has("app_service") and not has("api_gateway"):
        read_steps.append(
            {
                "source_type_id": "load_balancer",
                "source_label": by_type["load_balancer"]["label"],
                "target_type_id": "app_service",
                "target_label": by_type["app_service"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Balanced app call",
                "rationale": "Load Balancer routes requests to stateless app servers.",
            }
        )

    if has("app_service") and has("distributed_cache"):
        read_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": "distributed_cache",
                "target_label": by_type["distributed_cache"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Cache-aside lookup & populate",
                "rationale": "App Service checks Redis first; on miss it queries DB and populates cache.",
            }
        )

    read_db_type = (
        "read_replica"
        if has("read_replica")
        else (
            "relational_db"
            if has("relational_db")
            else ("nosql_kv" if has("nosql_kv") else None)
        )
    )
    if has("app_service") and read_db_type:
        read_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": read_db_type,
                "target_label": by_type[read_db_type]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Read fallback on cache miss",
                "rationale": "Serve cache-miss reads without overloading primary write locks.",
            }
        )

    if read_steps:
        paths.append(
            {"id": "read_path", "title": "Read / Low-Latency Path", "steps": read_steps}
        )

    # 2. Write / Creation Path
    write_steps: list[dict[str, Any]] = []
    if has("app_service") and has("content_filter"):
        write_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": "content_filter",
                "target_label": by_type["content_filter"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Validate URL safety / blocklist",
                "rationale": "Reject phishing/malicious destinations synchronously before minting or redirecting.",
            }
        )
    if has("app_service") and has("rate_limiter"):
        write_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": "rate_limiter",
                "target_label": by_type["rate_limiter"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Check write/abuse quota",
                "rationale": "Prevent abusive link creation spikes or brute-force code scraping.",
            }
        )
    if has("app_service") and has("id_generator"):
        write_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": "id_generator",
                "target_label": by_type["id_generator"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Mint collision-free short code",
                "rationale": "Short code creation needs a synchronous unique code before persisting the mapping.",
            }
        )
    primary_db_type = (
        "relational_db"
        if has("relational_db")
        else ("nosql_kv" if has("nosql_kv") else None)
    )
    if has("app_service") and primary_db_type:
        write_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": primary_db_type,
                "target_label": by_type[primary_db_type]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Persist mapping & optional TTL",
                "rationale": "Persist authoritative mapping + expires_at timestamp to primary storage.",
            }
        )
    if primary_db_type and has("read_replica"):
        write_steps.append(
            {
                "source_type_id": primary_db_type,
                "source_label": by_type[primary_db_type]["label"],
                "target_type_id": "read_replica",
                "target_label": by_type["read_replica"]["label"],
                "delivery_mode": "async",
                "suggested_label": "Async WAL replication",
                "rationale": "Replicate primary writes to read replicas for scale and failover.",
            }
        )

    if write_steps:
        paths.append(
            {"id": "write_path", "title": "Write & Safety Path", "steps": write_steps}
        )

    # 3. Async / Lifecycle Path
    async_steps: list[dict[str, Any]] = []
    queue_type = (
        "message_queue"
        if has("message_queue")
        else ("event_stream" if has("event_stream") else None)
    )
    if has("app_service") and queue_type:
        async_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": queue_type,
                "target_label": by_type[queue_type]["label"],
                "delivery_mode": "async",
                "suggested_label": "Enqueue async event / click log",
                "rationale": "Decouple analytics/background work so redirect latency stays under SLA.",
            }
        )
    if queue_type and has("async_worker"):
        sink_target = (
            ("olap_warehouse", by_type["olap_warehouse"]["label"])
            if has("olap_warehouse")
            else (
                (primary_db_type, by_type[primary_db_type]["label"])
                if primary_db_type
                else None
            )
        )
        async_steps.append(
            {
                "source_type_id": queue_type,
                "source_label": by_type[queue_type]["label"],
                "target_type_id": "async_worker",
                "target_label": by_type["async_worker"]["label"],
                "delivery_mode": "async",
                "suggested_label": "Consume & batch events",
                "rationale": "Workers aggregate queued events off the hot user path.",
            }
        )
        if sink_target:
            async_steps.append(
                {
                    "source_type_id": "async_worker",
                    "source_label": by_type["async_worker"]["label"],
                    "target_type_id": sink_target[0],
                    "target_label": sink_target[1],
                    "delivery_mode": "async",
                    "suggested_label": "Flush aggregated updates",
                    "rationale": "Persist batched counters asynchronously to storage.",
                }
            )
    if has("scheduler") and primary_db_type:
        async_steps.append(
            {
                "source_type_id": "scheduler",
                "source_label": by_type["scheduler"]["label"],
                "target_type_id": primary_db_type,
                "target_label": by_type[primary_db_type]["label"],
                "delivery_mode": "async",
                "suggested_label": "Sweep expired TTL rows",
                "rationale": "Periodically delete/archive expired links alongside lazy TTL checks on read.",
            }
        )

    if async_steps:
        paths.append(
            {
                "id": "async_lifecycle_path",
                "title": "Async Analytics & Lifecycle Path",
                "steps": async_steps,
            }
        )

    return paths


def resolve_challenge_blueprint(
    brief: dict[str, Any] | None,
    locked_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build unified required components and expected flow paths from challenge brief + locked ledger."""
    safe_brief = brief if isinstance(brief, dict) else {}
    safe_ledger = locked_ledger if isinstance(locked_ledger, dict) else {}
    palette_extensions = (
        safe_brief.get("diagram_palette_extensions")
        if isinstance(safe_brief.get("diagram_palette_extensions"), list)
        else []
    )

    corpus = " ".join(
        [
            _flatten_text_values(safe_brief.get("functional_requirements")),
            _flatten_text_values(safe_brief.get("non_functional_requirements")),
            _flatten_text_values(safe_brief.get("constraints")),
            _flatten_text_values(safe_brief.get("scale_estimates")),
            _flatten_text_values(safe_ledger.get("functional_requirements")),
            _flatten_text_values(safe_ledger.get("non_functional_requirements")),
            _flatten_text_values(safe_ledger.get("scale_estimates")),
            _flatten_text_values(safe_ledger.get("assumptions")),
            _flatten_text_values(safe_ledger.get("notes")),
        ]
    ).lower()

    out_of_scope_text = " ".join(
        [
            _flatten_text_values(safe_brief.get("out_of_scope")),
            _flatten_text_values(safe_ledger.get("out_of_scope")),
        ]
    ).lower()

    required_components: list[dict[str, Any]] = []
    seen_type_ids: set[str] = set()
    seen_labels: set[str] = set()

    def _register(entry: dict[str, Any]) -> None:
        tid = str(entry.get("type_id") or "")
        lbl = str(entry.get("label") or "").strip().lower()
        if tid and tid != "custom":
            if tid in seen_type_ids:
                return
            seen_type_ids.add(tid)
        elif lbl in seen_labels:
            return
        if lbl:
            seen_labels.add(lbl)
        required_components.append(entry)

    # 1. Start with explicit challenge expected_components (splitting composite multi-layer bundles)
    raw_expected = safe_brief.get("expected_components") or []
    if isinstance(raw_expected, list):
        for raw_item in raw_expected:
            raw_text = str(raw_item or "").strip()
            if not raw_text:
                continue
            for atomic_name in _split_composite_component_specs(raw_text):
                _register(
                    _build_component_entry(
                        atomic_name,
                        palette_extensions,
                        why_required=f"Core challenge requirement: {raw_text}",
                    )
                )

    # 2. Ensure core client entry when ingress/gateway is present
    if any(
        t in seen_type_ids
        for t in ("load_balancer", "api_gateway", "cdn", "app_service")
    ):
        _register(
            _build_component_entry(
                "Web / Browser Client",
                palette_extensions,
                why_required="Shows user entry points so end-to-end read and write traffic flows are complete.",
            )
        )

    # 3. Dynamically synthesize missing blocks implied by Challenge Constraints + Locked Stage 1 Ledger
    for rule in _SYNTHESIS_RULES:
        tid = rule["type_id"]
        if tid in seen_type_ids:
            continue
        patterns = rule.get("patterns") or ()
        if not patterns:
            continue
        if any(pat in corpus for pat in patterns):
            # Do not infer Read Replica if the challenge has no persistent primary DB at all
            if tid == "read_replica" and not (
                "relational_db" in seen_type_ids or "nosql_kv" in seen_type_ids
            ):
                continue
            # Do not suggest public CDN when explicitly excluded or flagged private-only
            if tid == "cdn" and (
                "cdn" in out_of_scope_text
                or "never publicly cache" in corpus
                or "no public cdn" in corpus
            ):
                continue
            block_meta = BLOCKS_BY_TYPE_ID.get(tid)
            if not block_meta:
                continue
            _register(
                _build_component_entry(
                    block_meta["label"],
                    palette_extensions,
                    why_required=rule["why"],
                    extra_checklist=rule.get("checklist"),
                )
            )

    # 4. Expected paths: prefer curated brief expected_paths when valid, else deterministic synthesis
    raw_paths = safe_brief.get("expected_paths")
    expected_paths: list[dict[str, Any]] = []
    if isinstance(raw_paths, list) and raw_paths:
        for path_group in raw_paths:
            if not isinstance(path_group, dict):
                continue
            steps = [
                step
                for step in (path_group.get("steps") or [])
                if isinstance(step, dict)
            ]
            if steps:
                expected_paths.append(
                    {
                        "id": str(path_group.get("id") or "path"),
                        "title": str(path_group.get("title") or "Architecture Flow"),
                        "steps": steps,
                    }
                )
    if not expected_paths:
        expected_paths = _synthesize_expected_paths(required_components)

    return {
        "required_components": required_components,
        "expected_paths": expected_paths,
        "out_of_scope_text": out_of_scope_text,
    }


def _edges_match_step(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    source_type_id: str,
    target_type_id: str,
) -> bool:
    node_types = {
        str(n.get("id")): str(n.get("type_id") or "")
        for n in nodes
        if isinstance(n, dict)
    }
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src_type = node_types.get(str(edge.get("source") or ""), "")
        dst_type = node_types.get(str(edge.get("target") or ""), "")
        if src_type == source_type_id and dst_type == target_type_id:
            return True
    return False


def evaluate_canvas_topology(
    flow_payload: dict[str, Any],
    resolved_blueprint: dict[str, Any],
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run deterministic pre-flight coaching checks on nodes, edges, SPOFs, and NFR coverage."""
    nodes = [n for n in (flow_payload.get("nodes") or []) if isinstance(n, dict)]
    edges = [e for e in (flow_payload.get("edges") or []) if isinstance(e, dict)]
    canvas_notes = str(flow_payload.get("notes") or "").lower()
    required_components = list(resolved_blueprint.get("required_components") or [])
    expected_paths = list(resolved_blueprint.get("expected_paths") or [])
    out_of_scope_text = str(resolved_blueprint.get("out_of_scope_text") or "").lower()

    node_by_id = {str(n.get("id")): n for n in nodes if n.get("id")}
    placed_type_ids = {str(n.get("type_id") or "") for n in nodes}

    # 1. Required component coverage
    missing_required: list[dict[str, Any]] = []
    placed_required_count = 0
    for req in required_components:
        is_present = any(
            node_matches_expected(n, req["name"])
            or (req["type_id"] != "custom" and n.get("type_id") == req["type_id"])
            for n in nodes
        )
        if is_present:
            placed_required_count += 1
        else:
            missing_required.append(req)

    total_required = len(required_components)
    coverage_pct = (
        round((placed_required_count / total_required) * 100) if total_required else 100
    )

    findings: list[dict[str, Any]] = []
    for req in missing_required:
        findings.append(
            {
                "severity": "missing",
                "title": f"Missing: {req['label']}",
                "detail": req.get("why_required") or req.get("hint_role") or "",
                "component_type_id": req["type_id"],
            }
        )

    # 2. Structural & directional anti-pattern checks on drawn edges
    incoming: dict[str, int] = {nid: 0 for nid in node_by_id}
    outgoing: dict[str, int] = {nid: 0 for nid in node_by_id}
    unlabeled_edge_count = 0
    seen_reversed_checks: set[str] = set()

    for edge in edges:
        src_id = str(edge.get("source") or "")
        dst_id = str(edge.get("target") or "")
        if src_id not in node_by_id or dst_id not in node_by_id:
            continue
        outgoing[src_id] += 1
        incoming[dst_id] += 1
        if not str(edge.get("label") or "").strip():
            unlabeled_edge_count += 1

        src_type = str(node_by_id[src_id].get("type_id") or "")
        dst_type = str(node_by_id[dst_id].get("type_id") or "")

        if src_type in ("relational_db", "nosql_kv", "read_replica") and dst_type in (
            "distributed_cache",
            "local_cache",
        ):
            if "db_to_cache" not in seen_reversed_checks:
                seen_reversed_checks.add("db_to_cache")
                findings.append(
                    {
                        "severity": "flow_direction",
                        "title": "Inverted Cache-Aside Direction (DB -> Cache)",
                        "detail": (
                            f"{node_by_id[src_id].get('label')} feeds {node_by_id[dst_id].get('label')} directly. "
                            "In cache-aside reads, Stateless App Service checks Redis first, queries DB/Replica on a miss, then populates Redis."
                        ),
                    }
                )

        if src_type == "cdn" and dst_type in (
            "distributed_cache",
            "relational_db",
            "nosql_kv",
            "id_generator",
        ):
            if "cdn_to_internal" not in seen_reversed_checks:
                seen_reversed_checks.add("cdn_to_internal")
                findings.append(
                    {
                        "severity": "flow_direction",
                        "title": "CDN Bypassing Load Balancer / App Layer",
                        "detail": (
                            f"{node_by_id[src_id].get('label')} connects straight to internal storage/cache ({node_by_id[dst_id].get('label')}). "
                            "Route CDN origin misses through Load Balancer -> API Gateway -> Stateless App Service."
                        ),
                    }
                )

        if (
            src_type
            in ("message_queue", "event_stream", "stream_processor", "async_worker")
            and dst_type == "id_generator"
        ):
            if "async_to_idgen" not in seen_reversed_checks:
                seen_reversed_checks.add("async_to_idgen")
                findings.append(
                    {
                        "severity": "flow_direction",
                        "title": "Async Layer Calling ID Generator",
                        "detail": (
                            f"{node_by_id[src_id].get('label')} -> {node_by_id[dst_id].get('label')} puts ID generation on an async queue path. "
                            "Link creation needs an immediate short code synchronously from Stateless App Service -> Unique ID / Key Generator."
                        ),
                    }
                )

    if len(nodes) > 1:
        isolated = [
            str(n.get("label") or nid)
            for nid, n in node_by_id.items()
            if incoming[nid] == 0 and outgoing[nid] == 0
        ]
        if isolated:
            findings.append(
                {
                    "severity": "wiring",
                    "title": f"Unwired Component(s): {', '.join(isolated[:3])}",
                    "detail": "Connect every placed block into a Read, Write, or Async flow so Reviewer sees how it participates.",
                }
            )
    if unlabeled_edge_count > 0:
        findings.append(
            {
                "severity": "wiring",
                "title": f"{unlabeled_edge_count} Unlabeled Wire(s)",
                "detail": "Click each wire to describe its action (e.g. 'Check cache / miss fallback', 'Persist short code + TTL').",
            }
        )

    # 3. SPOF & Resilience Notes checks on placed stateful blocks
    for node in nodes:
        tid = str(node.get("type_id") or "")
        combined_node_notes = " ".join(
            [
                str(node.get("tech_stack") or ""),
                str(node.get("notes") or ""),
                canvas_notes,
            ]
        ).lower()
        has_resilience_note = any(
            tok in combined_node_notes for tok in _RESILIENCE_TOKENS
        )
        if (
            tid == "id_generator"
            and not has_resilience_note
            and "consensus_store" not in placed_type_ids
        ):
            findings.append(
                {
                    "severity": "spof",
                    "title": "Single Point of Failure Risk on Unique ID / Key Generator",
                    "detail": "Click this node and note pre-allocated key ranges, ZooKeeper/etcd leases, or multi-instance active-active standby.",
                }
            )
        if (
            tid in ("relational_db", "nosql_kv")
            and "read_replica" not in placed_type_ids
            and not has_resilience_note
        ):
            findings.append(
                {
                    "severity": "spof",
                    "title": f"Redundancy / Read Scaling Note Missing on {node.get('label')}",
                    "detail": "Add a DB Read Replica block or specify Multi-AZ Primary-Replica failover and sharding key in node notes.",
                }
            )

    # 4. Over-engineering check aligned with challenge out-of-scope / traps
    if "stream_processor" in placed_type_ids and (
        "real-time" in out_of_scope_text
        or "sub-second" in out_of_scope_text
        or "message_queue" in {r["type_id"] for r in required_components}
    ):
        findings.append(
            {
                "severity": "complexity",
                "title": "Over-Engineering Risk: Stream Processor (Flink)",
                "detail": "Basic eventual-consistency click counting fits Task Queue + Background Worker Pool; Flink adds unnecessary operational overhead unless windowed real-time streaming is needed.",
            }
        )

    # 5. Path milestones & next connection hint
    path_milestones: list[dict[str, Any]] = []
    next_connection_hint: dict[str, Any] | None = None
    for path in expected_paths:
        step_results: list[dict[str, Any]] = []
        completed_steps = 0
        for step in path.get("steps") or []:
            src_tid = str(step.get("source_type_id") or "")
            dst_tid = str(step.get("target_type_id") or "")
            satisfied = _edges_match_step(nodes, edges, src_tid, dst_tid)
            if satisfied:
                completed_steps += 1
            elif next_connection_hint is None:
                next_connection_hint = {
                    "path_title": path.get("title") or "Architecture Flow",
                    **step,
                }
            step_results.append({**step, "satisfied": satisfied})
        path_milestones.append(
            {
                "id": path.get("id") or "path",
                "title": path.get("title") or "Path",
                "completed": completed_steps,
                "total": len(step_results),
                "steps": step_results,
            }
        )

    return {
        "placed_required_count": placed_required_count,
        "total_required_count": total_required,
        "coverage_pct": coverage_pct,
        "path_milestones": path_milestones,
        "findings": findings,
        "next_connection_hint": next_connection_hint,
    }
