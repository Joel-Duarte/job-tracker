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
        "label": "Scheduler / Cron Coordinator",
        "category": "compute_services",
        "icon": "clock",
        "default_role": "Triggers delayed tasks, TTL sweeps, billing runs, or periodic jobs.",
        "keywords": ["scheduler", "cron", "timer", "ttl", "delayed job", "sweeper"],
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
        "keywords": ["queue", "sqs", "rabbitmq", "task queue", "message queue"],
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
            "aggregation",
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
    hints_used_count: int, revealed_all_bank: bool
) -> float:
    """Compute cumulative capped score penalty for diagram component guidance."""
    single_penalty = max(0, int(hints_used_count)) * DIAGRAM_HINT_SINGLE_PENALTY
    if revealed_all_bank:
        raw = max(DIAGRAM_HINT_BULK_MIN_PENALTY, single_penalty)
    else:
        raw = single_penalty
    return round(min(DIAGRAM_HINT_MAX_PENALTY, raw), 1)
