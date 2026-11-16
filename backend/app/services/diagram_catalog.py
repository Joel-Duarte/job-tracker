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
    {
        "type_id": "webhook_actor",
        "label": "External System / Webhook",
        "category": "clients_edge",
        "icon": "globe",
        "default_role": "External partner service, B2B caller, IoT fleet, or webhook emitter initiating inbound events.",
        "keywords": [
            "webhook",
            "external system",
            "partner api",
            "third party",
            "b2b",
            "iot device",
        ],
    },
    {
        "type_id": "static_hosting",
        "label": "Static Web / SPA Host",
        "category": "clients_edge",
        "icon": "layers",
        "default_role": "Serves compiled SPA bundles and static web assets at the edge or origin bucket.",
        "keywords": [
            "static site",
            "spa",
            "s3 hosting",
            "static web apps",
            "cloudflare pages",
            "frontend bundle",
        ],
    },
    # 2. Traffic & API (7)
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
    {
        "type_id": "circuit_breaker",
        "label": "Service Mesh / Circuit Breaker",
        "category": "traffic_api",
        "icon": "shield-alert",
        "default_role": "Enforces mTLS, adaptive circuit breaking, retries, and overload shedding between services.",
        "keywords": [
            "circuit breaker",
            "service mesh",
            "istio",
            "envoy",
            "bulkhead",
            "shedding",
        ],
    },
    # 3. Compute & Services (7)
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
        "type_id": "llm_gateway",
        "label": "LLM / AI Model Gateway",
        "category": "compute_services",
        "icon": "brain",
        "default_role": "Routes prompts across LLM providers, manages token quotas/caching, and applies AI guardrails.",
        "keywords": [
            "llm gateway",
            "ai gateway",
            "bedrock",
            "azure openai",
            "vertex ai",
            "token quota",
            "prompt proxy",
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
        "type_id": "geo_index",
        "label": "Geospatial / Proximity Index",
        "category": "databases_storage",
        "icon": "compass",
        "default_role": "Stores spatial coordinates, H3 cells, or geohashes for low-latency nearby radius queries.",
        "keywords": [
            "geospatial",
            "geo",
            "h3",
            "quadtree",
            "geohash",
            "postgis",
            "proximity",
            "location index",
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
    {
        "type_id": "notification_hub",
        "label": "Push / Email / SMS Gateway",
        "category": "messaging_streaming",
        "icon": "radio",
        "default_role": "Delivers multi-channel alerts via APNs, FCM, SMTP/SES, or SMS carriers with delivery receipts.",
        "keywords": [
            "notification",
            "apns",
            "fcm",
            "push notification",
            "email",
            "ses",
            "sms",
            "twilio",
        ],
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

CLOUD_PROVIDERS: list[dict[str, str]] = [
    {"id": "generic", "label": "Generic (Cloud-Agnostic)", "short_label": "Generic"},
    {"id": "aws", "label": "Amazon Web Services (AWS)", "short_label": "AWS"},
    {"id": "azure", "label": "Microsoft Azure", "short_label": "Azure"},
    {"id": "gcp", "label": "Google Cloud (GCP)", "short_label": "GCP"},
    {"id": "cloudflare", "label": "Cloudflare", "short_label": "CF"},
    {"id": "oci", "label": "Oracle Cloud (OCI)", "short_label": "OCI"},
]

VALID_CLOUD_PROVIDER_IDS: set[str] = {p["id"] for p in CLOUD_PROVIDERS}

CLOUD_EQUIVALENTS_BY_TYPE: dict[str, dict[str, str]] = {
    "static_hosting": {
        "aws": "Amazon S3 + CloudFront SPA",
        "azure": "Azure Static Web Apps",
        "gcp": "Firebase Hosting / Cloud Storage SPA",
        "cloudflare": "Cloudflare Pages",
        "oci": "OCI Object Storage Static Web",
    },
    "dns": {
        "aws": "Amazon Route 53",
        "azure": "Azure DNS / Traffic Manager",
        "gcp": "Google Cloud DNS",
        "cloudflare": "Cloudflare Authoritative DNS",
        "oci": "OCI DNS & Traffic Management",
    },
    "cdn": {
        "aws": "Amazon CloudFront",
        "azure": "Azure Front Door / CDN",
        "gcp": "Google Cloud CDN",
        "cloudflare": "Cloudflare Global CDN",
        "oci": "OCI Edge / Akamai CDN",
    },
    "waf_ddos": {
        "aws": "AWS WAF & Shield Advanced",
        "azure": "Azure WAF & DDoS Protection",
        "gcp": "Google Cloud Armor",
        "cloudflare": "Cloudflare WAF & DDoS",
        "oci": "OCI Web Application Firewall",
    },
    "load_balancer": {
        "aws": "AWS ALB / NLB (ELB)",
        "azure": "Azure Application Gateway / Load Balancer",
        "gcp": "Google Cloud Load Balancing",
        "cloudflare": "Cloudflare Load Balancing",
        "oci": "OCI Flexible Load Balancer",
    },
    "api_gateway": {
        "aws": "Amazon API Gateway",
        "azure": "Azure API Management (APIM)",
        "gcp": "Apigee / GCP API Gateway",
        "cloudflare": "Cloudflare API Gateway",
        "oci": "OCI API Gateway",
    },
    "rate_limiter": {
        "aws": "AWS WAF / API GW Usage Plans",
        "azure": "Azure APIM Rate-Limit Policy",
        "gcp": "Cloud Armor Rate Limiting",
        "cloudflare": "Cloudflare Rate Limiting",
        "oci": "OCI API Gateway Rate Limit",
    },
    "circuit_breaker": {
        "aws": "AWS App Mesh / VPC Lattice",
        "azure": "Azure Service Mesh / APIM Breaker",
        "gcp": "Google Cloud Service Mesh",
        "cloudflare": "Cloudflare Health Checks & Failover",
        "oci": "OCI Service Mesh (Envoy)",
    },
    "auth_service": {
        "aws": "Amazon Cognito / AWS IAM",
        "azure": "Microsoft Entra ID (Azure AD)",
        "gcp": "GCP Identity Platform / Firebase Auth",
        "cloudflare": "Cloudflare Access (Zero Trust)",
        "oci": "OCI IAM Identity Domains",
    },
    "realtime_gateway": {
        "aws": "API Gateway WebSockets / IoT Core",
        "azure": "Azure Web PubSub / SignalR",
        "gcp": "Cloud Run WebSockets / Firebase RTDB",
        "cloudflare": "Cloudflare Durable Objects (WS)",
        "oci": "OCI API GW / Load Balancer WS",
    },
    "content_filter": {
        "aws": "AWS GuardDuty / Lambda Safe Filter",
        "azure": "Azure AI Content Safety",
        "gcp": "Google Web Risk API",
        "cloudflare": "Cloudflare Gateway / URL Scanner",
        "oci": "OCI Threat Intelligence / Functions",
    },
    "app_service": {
        "aws": "AWS ECS / EKS / EC2 Auto Scaling",
        "azure": "Azure App Service / AKS / Container Apps",
        "gcp": "Google Cloud Run / GKE",
        "cloudflare": "Cloudflare Workers",
        "oci": "OCI Container Engine (OKE)",
    },
    "async_worker": {
        "aws": "AWS Lambda / ECS SQS Workers",
        "azure": "Azure Functions / Container Apps",
        "gcp": "Cloud Run / Cloud Functions Workers",
        "cloudflare": "Cloudflare Queue Consumer Workers",
        "oci": "OCI Functions / Container Instances",
    },
    "scheduler": {
        "aws": "Amazon EventBridge Scheduler",
        "azure": "Azure Logic Apps / Timer Functions",
        "gcp": "Google Cloud Scheduler",
        "cloudflare": "Cloudflare Cron Triggers",
        "oci": "OCI Resource Scheduler / Functions",
    },
    "id_generator": {
        "aws": "ECS Key Service + DynamoDB Counter",
        "azure": "Azure Container Apps Key Service",
        "gcp": "Cloud Run Key Range Allocator",
        "cloudflare": "Cloudflare Durable Objects Coordinator",
        "oci": "OKE Key Generator Service",
    },
    "ml_inference": {
        "aws": "Amazon SageMaker / ECS Inference",
        "azure": "Azure Machine Learning Endpoint",
        "gcp": "Google Vertex AI Prediction",
        "cloudflare": "Cloudflare Workers AI",
        "oci": "OCI Data Science Model Deployment",
    },
    "llm_gateway": {
        "aws": "Amazon Bedrock / AI Gateway",
        "azure": "Azure OpenAI / APIM AI Gateway",
        "gcp": "Google Vertex AI Gateway",
        "cloudflare": "Cloudflare AI Gateway",
        "oci": "OCI Generative AI Service",
    },
    "media_transcoder": {
        "aws": "AWS Elemental MediaConvert",
        "azure": "Azure Media / Container Batch",
        "gcp": "Google Transcoder API",
        "cloudflare": "Cloudflare Stream",
        "oci": "OCI Vision / Media Services",
    },
    "distributed_cache": {
        "aws": "Amazon ElastiCache (Redis)",
        "azure": "Azure Cache for Redis",
        "gcp": "Google Cloud Memorystore (Redis)",
        "cloudflare": "Cloudflare Workers KV / Durable Objects",
        "oci": "OCI Cache (Managed Redis)",
    },
    "local_cache": {
        "aws": "In-Process Cache (ECS/EKS Pod RAM)",
        "azure": "In-Memory Cache (App Service / AKS)",
        "gcp": "In-Process Memory (Cloud Run / GKE)",
        "cloudflare": "Cloudflare Edge Cache API",
        "oci": "In-Process Cache (OKE Pod RAM)",
    },
    "feature_store": {
        "aws": "SageMaker Feature Store / DynamoDB",
        "azure": "Azure Managed Redis / Cosmos DB",
        "gcp": "Vertex AI Feature Store",
        "cloudflare": "Workers KV Online State",
        "oci": "OCI NoSQL / Cache Store",
    },
    "bloom_filter": {
        "aws": "ElastiCache RedisBloom",
        "azure": "Azure Managed Redis (RedisBloom)",
        "gcp": "Memorystore / In-Memory Filter",
        "cloudflare": "Durable Objects / Workers Filter",
        "oci": "OCI Cache (Redis Modules)",
    },
    "relational_db": {
        "aws": "Amazon RDS / Aurora PostgreSQL",
        "azure": "Azure Database for PostgreSQL / SQL",
        "gcp": "Google Cloud SQL / Cloud Spanner",
        "cloudflare": "Cloudflare D1 (Serverless SQLite)",
        "oci": "OCI Autonomous Database / MySQL HeatWave",
    },
    "read_replica": {
        "aws": "Amazon Aurora / RDS Read Replica",
        "azure": "Azure SQL / PostgreSQL Read Replica",
        "gcp": "Google Cloud SQL Read Replica",
        "cloudflare": "Cloudflare D1 Read Replication",
        "oci": "OCI MySQL / Autonomous Read Replica",
    },
    "nosql_kv": {
        "aws": "Amazon DynamoDB",
        "azure": "Azure Cosmos DB",
        "gcp": "Google Firestore / Cloud Bigtable",
        "cloudflare": "Cloudflare Workers KV / Durable Objects",
        "oci": "OCI NoSQL Database Cloud",
    },
    "object_storage": {
        "aws": "Amazon S3",
        "azure": "Azure Blob Storage",
        "gcp": "Google Cloud Storage (GCS)",
        "cloudflare": "Cloudflare R2",
        "oci": "OCI Object Storage",
    },
    "timeseries_db": {
        "aws": "Amazon Timestream",
        "azure": "Azure Data Explorer (Kusto)",
        "gcp": "Cloud Bigtable Time-Series",
        "cloudflare": "Cloudflare Analytics Engine",
        "oci": "OCI Logging Analytics / Monitoring TS",
    },
    "vector_db": {
        "aws": "Amazon OpenSearch Vector / Aurora pgvector",
        "azure": "Azure AI Search Vector / Cosmos pgvector",
        "gcp": "Vertex AI Vector Search",
        "cloudflare": "Cloudflare Vectorize",
        "oci": "OCI Database 23ai AI Vector Search",
    },
    "geo_index": {
        "aws": "Amazon Location / ElastiCache Geo",
        "azure": "Azure Maps / Managed Redis Geo",
        "gcp": "Memorystore Geo / Firestore Geo",
        "cloudflare": "Durable Objects Spatial Shard",
        "oci": "OCI Spatial & Cache Geo",
    },
    "consensus_store": {
        "aws": "AWS etcd / DynamoDB Lock Table",
        "azure": "Azure Blob Leases / etcd on AKS",
        "gcp": "Cloud Spanner / etcd on GKE",
        "cloudflare": "Cloudflare Durable Objects Coordination",
        "oci": "OCI etcd on OKE / Autonomous Lock",
    },
    "message_queue": {
        "aws": "Amazon SQS",
        "azure": "Azure Service Bus Queues",
        "gcp": "Google Cloud Tasks / Pub/Sub",
        "cloudflare": "Cloudflare Queues",
        "oci": "OCI Queue Service",
    },
    "event_stream": {
        "aws": "Amazon Kinesis / MSK (Kafka)",
        "azure": "Azure Event Hubs",
        "gcp": "Google Cloud Pub/Sub",
        "cloudflare": "Cloudflare Pipelines",
        "oci": "OCI Streaming (Kafka-compatible)",
    },
    "pubsub_bus": {
        "aws": "Amazon SNS",
        "azure": "Azure Event Grid / Service Bus Topics",
        "gcp": "Google Cloud Pub/Sub Topics",
        "cloudflare": "Cloudflare Queues Multi-Consumer",
        "oci": "OCI Notifications & Streaming",
    },
    "stream_processor": {
        "aws": "Amazon Managed Service for Apache Flink",
        "azure": "Azure Stream Analytics",
        "gcp": "Google Cloud Dataflow",
        "cloudflare": "Cloudflare Pipelines / Workers Stream",
        "oci": "OCI GoldenGate Stream Analytics",
    },
    "dlq": {
        "aws": "Amazon SQS Dead-Letter Queue",
        "azure": "Azure Service Bus DLQ",
        "gcp": "Google Pub/Sub Dead-Letter Topic",
        "cloudflare": "Cloudflare Queue DLQ",
        "oci": "OCI Queue Dead-Letter Channel",
    },
    "notification_hub": {
        "aws": "Amazon SNS / SES / Pinpoint",
        "azure": "Azure Notification Hubs / Comm.",
        "gcp": "Firebase Cloud Messaging (FCM)",
        "cloudflare": "Cloudflare Email Workers / Webhook",
        "oci": "OCI Notifications & Email Delivery",
    },
    "search_engine": {
        "aws": "Amazon OpenSearch Service",
        "azure": "Azure AI Search",
        "gcp": "Vertex AI Search / Elastic Cloud",
        "cloudflare": "Cloudflare Vectorize / D1 FTS",
        "oci": "OCI Search Service with OpenSearch",
    },
    "olap_warehouse": {
        "aws": "Amazon Redshift / Athena",
        "azure": "Azure Synapse Analytics / Fabric",
        "gcp": "Google BigQuery",
        "cloudflare": "Cloudflare R2 + Workers Analytics",
        "oci": "OCI Autonomous Data Warehouse",
    },
    "cdc_connector": {
        "aws": "AWS DMS / MSK Connect Debezium",
        "azure": "Azure Data Factory CDC / Event Hubs",
        "gcp": "Google Datastream (CDC)",
        "cloudflare": "D1 Export / Worker Outbox",
        "oci": "OCI GoldenGate CDC",
    },
    "observability": {
        "aws": "Amazon CloudWatch & AWS X-Ray",
        "azure": "Azure Monitor & Application Insights",
        "gcp": "Google Cloud Monitoring & Cloud Trace",
        "cloudflare": "Cloudflare Logpush & Workers Analytics",
        "oci": "OCI Monitoring, Logging & APM",
    },
}

for _block in CANONICAL_DIAGRAM_BLOCKS:
    _block["cloud_equivalents"] = dict(
        CLOUD_EQUIVALENTS_BY_TYPE.get(_block["type_id"], {})
    )

BLOCKS_BY_TYPE_ID: dict[str, dict[str, Any]] = {
    block["type_id"]: block for block in CANONICAL_DIAGRAM_BLOCKS
}


def normalize_cloud_provider(provider: str | None) -> str:
    """Normalize a cloud lens identifier onto the canonical provider set."""
    cleaned = str(provider or "generic").strip().lower()
    return cleaned if cleaned in VALID_CLOUD_PROVIDER_IDS else "generic"


def get_cloud_service_name(type_id: str, cloud_provider: str | None) -> str:
    """Return the provider-specific service label for a canonical component type."""
    norm = normalize_cloud_provider(cloud_provider)
    if norm == "generic":
        return ""
    return str(CLOUD_EQUIVALENTS_BY_TYPE.get(type_id, {}).get(norm, "")).strip()


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
    outside_parens = re.sub(r"\([^()]*\)", "", cleaned).strip().lower()
    name_tokens = _tokenize(cleaned)

    for block in CANONICAL_DIAGRAM_BLOCKS:
        score = 0
        block_lbl = block["label"].lower()
        if block_lbl == lower_name or block["type_id"] == lower_name:
            score += 500
        elif outside_parens and block_lbl == outside_parens:
            score += 400
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
    """Canonicalize submitted canvas nodes, edges, notes, cloud_provider, and viewport into Flow JSON."""
    raw_nodes = list(raw_payload.get("nodes") or [])
    raw_edges = list(raw_payload.get("edges") or [])
    flow_cloud = normalize_cloud_provider(raw_payload.get("cloud_provider"))

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
        generic_label = str(
            node.get("generic_label")
            or (catalog_meta["label"] if catalog_meta else label)
        ).strip()
        node_cloud = normalize_cloud_provider(node.get("cloud_provider") or flow_cloud)
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
                "generic_label": generic_label,
                "cloud_provider": node_cloud,
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
        "cloud_provider": flow_cloud,
        "nodes": normalized_nodes,
        "edges": normalized_edges,
        "notes": str(raw_payload.get("notes") or "").strip(),
        "viewport": raw_payload.get("viewport") or {"x": 0, "y": 0, "zoom": 1},
    }


def summarize_diagram_flow(flow_payload: dict[str, Any]) -> dict[str, Any]:
    """Produce deterministic components, directed flows, and topology diagnostics from Flow JSON."""
    cloud_provider = normalize_cloud_provider(flow_payload.get("cloud_provider"))
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
        "cloud_provider": cloud_provider,
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
    """Guidance hints never deduct score points (Solo vs Coached tracking replaces penalties)."""
    _ = (hints_used_count, revealed_all_bank, mode)
    return 0.0


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
    {
        "type_id": "geo_index",
        "patterns": (
            "geospatial",
            "h3",
            "geohash",
            "quadtree",
            "nearby",
            "proximity",
            "driver location",
            "postgis",
        ),
        "why": "Indexes live entity coordinates for fast proximity/radius searches without scanning the full database.",
        "checklist": [
            "Shard spatial grid by city/region and expire stale location TTLs automatically"
        ],
    },
    {
        "type_id": "notification_hub",
        "patterns": (
            "push notification",
            "apns",
            "fcm",
            "sms",
            "email alert",
            "multi-channel",
        ),
        "why": "Decouples external APNs/FCM/SMTP/SMS carrier integrations with per-channel templates, backoff, and delivery receipts.",
        "checklist": [
            "Track idempotency keys and fallback/retry policies per notification carrier"
        ],
    },
    {
        "type_id": "circuit_breaker",
        "patterns": (
            "circuit breaker",
            "service mesh",
            "bulkhead",
            "overload shedding",
            "downstream health",
        ),
        "why": "Prevents cascading failures when slow or degraded downstreams exhaust caller thread/connection pools.",
        "checklist": [
            "Configure error-rate trip thresholds, half-open probes, and bounded timeouts"
        ],
    },
    {
        "type_id": "llm_gateway",
        "patterns": (
            "llm",
            "prompt token",
            "bedrock",
            "openai",
            "foundation model",
            "generative ai",
            "ai gateway",
        ),
        "why": "Centralizes LLM routing, prompt/token quotas, semantic caching, and safety guardrails across model providers.",
        "checklist": [
            "Track prompt+completion token budgets, streaming SSE pass-through, and fallback models"
        ],
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
    outside_lower = outside_parens.lower()
    if any(
        b["label"].lower() == lower or b["label"].lower() == outside_lower
        for b in CANONICAL_DIAGRAM_BLOCKS
    ):
        return [cleaned]
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

    if "/" not in outside_parens and "+" not in outside_parens:
        return [cleaned]

    if "api gateway" in lower and "load balancer" in lower:
        return ["Load Balancer", "API Gateway"]
    if "queue" in lower and "worker" in lower:
        return ["Task Queue", "Background Worker Pool"]
    if "client" in lower and "cdn" in lower:
        return ["Web / Browser Client", "CDN / Edge Cache"]

    parts = [p.strip() for p in re.split(r"[/+]", outside_parens) if p.strip()]
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
        "cloud_equivalents": dict(
            CLOUD_EQUIVALENTS_BY_TYPE.get(matched["type_id"], {})
        ),
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

    if has("app_service") and has("local_cache"):
        read_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": "local_cache",
                "target_label": by_type["local_cache"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "L1 hot-key lookup",
                "rationale": "Absorb ultra-hot Viral/Celebrity reads in process memory before network hops to Redis.",
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
    if has("cdn") and has("object_storage") and not has("app_service"):
        read_steps.append(
            {
                "source_type_id": "cdn",
                "source_label": by_type["cdn"]["label"],
                "target_type_id": "object_storage",
                "target_label": by_type["object_storage"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Origin media / asset pull",
                "rationale": "CDN fetches uncached immutable media segments or chunks from object storage.",
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
    if has("app_service") and has("geo_index"):
        read_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": "geo_index",
                "target_label": by_type["geo_index"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Proximity / H3 cell query",
                "rationale": "Query live spatial buckets for nearby drivers/entities instead of full DB scans.",
            }
        )
    if has("app_service") and has("llm_gateway"):
        read_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": "llm_gateway",
                "target_label": by_type["llm_gateway"]["label"],
                "delivery_mode": "sync",
                "suggested_label": "Model inference & quota check",
                "rationale": "Route AI calls through LLM Gateway for token accounting, guardrails, and provider failover.",
            }
        )
        if has("vector_db"):
            read_steps.append(
                {
                    "source_type_id": "llm_gateway",
                    "source_label": by_type["llm_gateway"]["label"],
                    "target_type_id": "vector_db",
                    "target_label": by_type["vector_db"]["label"],
                    "delivery_mode": "sync",
                    "suggested_label": "RAG vector retrieval",
                    "rationale": "Fetch semantic context chunks prior to prompt assembly.",
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

    # 3. Async / Streaming & Lifecycle Path
    async_steps: list[dict[str, Any]] = []
    queue_type = (
        "event_stream"
        if has("event_stream") and has("stream_processor")
        else (
            "message_queue"
            if has("message_queue")
            else ("event_stream" if has("event_stream") else None)
        )
    )
    if has("app_service") and queue_type:
        async_steps.append(
            {
                "source_type_id": "app_service",
                "source_label": by_type["app_service"]["label"],
                "target_type_id": queue_type,
                "target_label": by_type[queue_type]["label"],
                "delivery_mode": "async",
                "suggested_label": "Publish async event / telemetry",
                "rationale": "Decouple analytics, transcoding, or background fan-out so hot-path latency stays under SLA.",
            }
        )
    if queue_type and has("stream_processor"):
        async_steps.append(
            {
                "source_type_id": queue_type,
                "source_label": by_type[queue_type]["label"],
                "target_type_id": "stream_processor",
                "target_label": by_type["stream_processor"]["label"],
                "delivery_mode": "async",
                "suggested_label": "Stream windowing & filtering",
                "rationale": "Compute real-time bot/fraud dedup and sliding window aggregations off-path.",
            }
        )
        if has("olap_warehouse"):
            async_steps.append(
                {
                    "source_type_id": "stream_processor",
                    "source_label": by_type["stream_processor"]["label"],
                    "target_type_id": "olap_warehouse",
                    "target_label": by_type["olap_warehouse"]["label"],
                    "delivery_mode": "async",
                    "suggested_label": "Sink aggregated metrics",
                    "rationale": "Write rolled-up telemetry into OLAP storage for fast analytical queries.",
                }
            )
    if queue_type and has("async_worker"):
        sink_target = (
            ("notification_hub", by_type["notification_hub"]["label"])
            if has("notification_hub")
            else (
                ("olap_warehouse", by_type["olap_warehouse"]["label"])
                if has("olap_warehouse")
                else (
                    (primary_db_type, by_type[primary_db_type]["label"])
                    if primary_db_type
                    else None
                )
            )
        )
        async_steps.append(
            {
                "source_type_id": queue_type,
                "source_label": by_type[queue_type]["label"],
                "target_type_id": "async_worker",
                "target_label": by_type["async_worker"]["label"],
                "delivery_mode": "async",
                "suggested_label": "Consume & process jobs",
                "rationale": "Workers aggregate or process queued events asynchronously with retries/DLQ.",
            }
        )
        if has("media_transcoder"):
            async_steps.append(
                {
                    "source_type_id": "async_worker",
                    "source_label": by_type["async_worker"]["label"],
                    "target_type_id": "media_transcoder",
                    "target_label": by_type["media_transcoder"]["label"],
                    "delivery_mode": "async",
                    "suggested_label": "Transcode / chunk media",
                    "rationale": "Execute CPU/GPU-heavy segmentation & ABR encoding asynchronously.",
                }
            )
        elif sink_target:
            async_steps.append(
                {
                    "source_type_id": "async_worker",
                    "source_label": by_type["async_worker"]["label"],
                    "target_type_id": sink_target[0],
                    "target_label": sink_target[1],
                    "delivery_mode": "async",
                    "suggested_label": "Flush aggregated updates",
                    "rationale": "Persist batched updates or dispatch multi-channel alerts asynchronously.",
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
                "rationale": "Periodically delete/archive expired records alongside lazy TTL checks on read.",
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

    # 1. Start with explicit challenge expected_components (splitting composite multi-layer bundles cleanly)
    raw_expected = safe_brief.get("expected_components") or []
    if isinstance(raw_expected, list):
        for raw_item in raw_expected:
            raw_text = str(raw_item or "").strip()
            if not raw_text:
                continue
            split_names = _split_composite_component_specs(raw_text)
            for atomic_name in split_names:
                matched_meta = match_component_to_catalog(
                    atomic_name, palette_extensions
                )
                why_text = (
                    str(matched_meta.get("hint_role") or "")
                    if len(split_names) > 1 and matched_meta.get("hint_role")
                    else f"Core challenge requirement: {raw_text}"
                )
                _register(
                    _build_component_entry(
                        atomic_name,
                        palette_extensions,
                        why_required=why_text,
                    )
                )

    # 2. Dynamically synthesize missing blocks implied by Challenge Constraints + Locked Stage 1 Ledger
    # Skip fuzzy regex guessing when the challenge variant already supplies both curated components & curated paths.
    raw_paths_preview = safe_brief.get("expected_paths")
    has_curated_spec = (
        isinstance(raw_paths_preview, list)
        and len(raw_paths_preview) > 0
        and isinstance(raw_expected, list)
        and len(raw_expected) > 0
    )
    if not has_curated_spec:
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

    # 3. Ensure baseline stateless compute & client entry point when backend/ingress components exist (for non-curated/legacy briefs)
    if (
        not has_curated_spec
        and not any(
            t in seen_type_ids
            for t in ("app_service", "serverless_fn", "microservice", "llm_gateway")
        )
        and any(
            t in seen_type_ids
            for t in (
                "load_balancer",
                "api_gateway",
                "relational_db",
                "nosql_kv",
                "distributed_cache",
                "message_queue",
                "event_stream",
                "geo_index",
            )
        )
    ):
        app_meta = BLOCKS_BY_TYPE_ID["app_service"]
        _register(
            _build_component_entry(
                app_meta["label"],
                palette_extensions,
                why_required="Handles request validation, cache-aside orchestration, and read/write business logic cleanly.",
            )
        )

    if not any(
        t in seen_type_ids for t in ("web_client", "mobile_client", "webhook_actor")
    ) and any(
        t in seen_type_ids
        for t in (
            "load_balancer",
            "api_gateway",
            "cdn",
            "app_service",
            "realtime_gateway",
        )
    ):
        _register(
            _build_component_entry(
                "Web / Browser Client",
                palette_extensions,
                why_required="Shows user entry points so end-to-end read and write traffic flows are complete.",
            )
        )

    # 4. Expected paths: prefer curated brief expected_paths when valid, else deterministic synthesis
    raw_paths = safe_brief.get("expected_paths")
    expected_paths: list[dict[str, Any]] = []
    if isinstance(raw_paths, list) and raw_paths:
        for path_group in raw_paths:
            if not isinstance(path_group, dict):
                continue
            steps: list[dict[str, Any]] = []
            for step in path_group.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                src_tid = str(step.get("source_type_id") or "")
                dst_tid = str(step.get("target_type_id") or "")
                src_lbl = str(
                    step.get("source_label")
                    or (BLOCKS_BY_TYPE_ID.get(src_tid) or {}).get("label")
                    or src_tid
                )
                dst_lbl = str(
                    step.get("target_label")
                    or (BLOCKS_BY_TYPE_ID.get(dst_tid) or {}).get("label")
                    or dst_tid
                )
                steps.append(
                    {
                        "source_type_id": src_tid,
                        "source_label": src_lbl,
                        "target_type_id": dst_tid,
                        "target_label": dst_lbl,
                        "delivery_mode": str(step.get("delivery_mode") or "sync"),
                        "suggested_label": str(step.get("suggested_label") or ""),
                        "rationale": str(step.get("rationale") or ""),
                    }
                )
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
    for path_item in expected_paths:
        if not path_item.get("description"):
            path_item["description"] = _describe_path_steps(
                path_item.get("steps") or []
            )

    required_capabilities = synthesize_required_capabilities(
        safe_brief, safe_ledger, required_components
    )

    return {
        "required_components": required_components,
        "expected_paths": expected_paths,
        "required_capabilities": required_capabilities,
        "out_of_scope_text": out_of_scope_text,
    }


def synthesize_required_capabilities(
    brief: dict[str, Any] | None,
    locked_ledger: dict[str, Any] | None,
    required_components: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return high-level, non-spoiling architectural capabilities satisfiable by multiple valid stacks."""
    safe_brief = brief if isinstance(brief, dict) else {}
    safe_ledger = locked_ledger if isinstance(locked_ledger, dict) else {}

    explicit = safe_brief.get("required_capabilities")
    if isinstance(explicit, list) and explicit:
        cleaned_explicit: list[dict[str, Any]] = []
        for idx, item in enumerate(explicit):
            if not isinstance(item, dict) or not item.get("title"):
                continue
            groups = (
                item.get("accepted_type_groups") or item.get("accepted_types") or []
            )
            norm_groups: list[list[str]] = []
            for grp in groups:
                if isinstance(grp, list):
                    norm_groups.append([str(t) for t in grp if t])
                elif isinstance(grp, str) and grp:
                    norm_groups.append([grp])
            cleaned_explicit.append(
                {
                    "id": str(item.get("id") or f"cap-{idx + 1}"),
                    "title": str(item.get("title") or "").strip(),
                    "goal": str(
                        item.get("goal")
                        or item.get("description")
                        or item.get("title")
                        or ""
                    ).strip(),
                    "accepted_type_groups": norm_groups,
                    "defence_tradeoff": str(item.get("defence_tradeoff") or "").strip(),
                }
            )
        if cleaned_explicit:
            return cleaned_explicit

    req_tids = {str(c.get("type_id") or "") for c in required_components}
    corpus = " ".join(
        [
            _flatten_text_values(safe_brief.get("functional_requirements")),
            _flatten_text_values(safe_brief.get("non_functional_requirements")),
            _flatten_text_values(safe_brief.get("constraints")),
            _flatten_text_values(safe_ledger.get("functional_requirements")),
            _flatten_text_values(safe_ledger.get("non_functional_requirements")),
            _flatten_text_values(safe_ledger.get("constraints")),
        ]
    ).lower()

    capabilities: list[dict[str, Any]] = []

    if req_tids & {
        "cdn",
        "load_balancer",
        "api_gateway",
        "waf_ddos",
        "realtime_gateway",
    }:
        capabilities.append(
            {
                "id": "edge_ingress",
                "title": "Edge & Ingress Routing",
                "goal": "Terminate client traffic through edge caching, load balancing, or an API/realtime gateway without exposing storage directly.",
                "accepted_type_groups": [
                    ["cdn"],
                    ["load_balancer"],
                    ["api_gateway"],
                    ["realtime_gateway"],
                    ["waf_ddos"],
                ],
                "defence_tradeoff": "If omitting CDN/WAF on public high-QPS traffic, defend tail latency and DDoS absorption.",
            }
        )

    if req_tids & {"app_service", "serverless_fn", "microservice", "llm_gateway"}:
        capabilities.append(
            {
                "id": "compute_layer",
                "title": "Stateless Compute & Business Logic",
                "goal": "Process validation, orchestration, and read/write APIs in horizontally scalable compute (app tier, serverless, microservices, or model gateway).",
                "accepted_type_groups": [
                    ["app_service"],
                    ["serverless_fn"],
                    ["microservice"],
                    ["llm_gateway"],
                ],
                "defence_tradeoff": "Be ready to defend cold-start/connection-pool bounds (Serverless) or deployment/boundary isolation (Monolith vs Microservices).",
            }
        )

    if req_tids & {
        "distributed_cache",
        "local_cache",
        "bloom_filter",
        "feature_store",
    } or any(
        tok in corpus
        for tok in (
            "< 30ms",
            "<30ms",
            "< 50ms",
            "hot-key",
            "hot key",
            "read-heavy",
            "100:1",
            "cache",
        )
    ):
        capabilities.append(
            {
                "id": "low_latency_caching",
                "title": "Low-Latency Caching / Hot-Key Mitigation",
                "goal": "Absorb hot read bursts and stay within p99 latency targets via edge caching, in-process L1 cache, distributed memory cache, or pre-filter indexes.",
                "accepted_type_groups": [
                    ["distributed_cache"],
                    ["local_cache"],
                    ["cdn"],
                    ["bloom_filter"],
                    ["feature_store"],
                ],
                "defence_tradeoff": "Explain cache invalidation/TTL staleness, thundering-herd protection, and hot-key skew on single shards.",
            }
        )

    if req_tids & {
        "relational_db",
        "nosql_kv",
        "object_storage",
        "timeseries_db",
        "consensus_store",
    }:
        capabilities.append(
            {
                "id": "durable_storage",
                "title": "Durable Authoritative Persistence",
                "goal": "Persist core entities or blobs reliably using relational SQL (+ replicas/partitioning), distributed KV/NoSQL, or durable object/time-series storage.",
                "accepted_type_groups": [
                    ["relational_db"],
                    ["nosql_kv"],
                    ["object_storage"],
                    ["timeseries_db"],
                    ["consensus_store"],
                ],
                "defence_tradeoff": "Justify primary key/sharding choice, replication lag tolerance, and failover strategy for your write vs read ratio.",
            }
        )

    if req_tids & {
        "message_queue",
        "event_stream",
        "pubsub_bus",
        "async_worker",
        "stream_processor",
        "olap_warehouse",
    }:
        capabilities.append(
            {
                "id": "async_decoupling",
                "title": "Async Decoupling / Analytics / Background Work",
                "goal": "Keep user-facing latency isolated from heavy analytics, notifications, or transcoding using a queue, event stream, pub/sub bus, or background workers.",
                "accepted_type_groups": [
                    ["message_queue"],
                    ["event_stream"],
                    ["pubsub_bus"],
                    ["async_worker"],
                    ["stream_processor"],
                ],
                "defence_tradeoff": "Clarify delivery guarantees (at-least-once + idempotency), backpressure, and DLQ replay when consumers lag.",
            }
        )

    if req_tids & {"id_generator"}:
        capabilities.append(
            {
                "id": "unique_id_generation",
                "title": "Collision-Free Unique ID / Key Minting",
                "goal": "Generate collision-free non-predictable short codes safely under concurrent writes without a database sequence SPOF.",
                "accepted_type_groups": [
                    ["id_generator"],
                    ["consensus_store"],
                    ["app_service"],
                ],
                "defence_tradeoff": "Explain whether you use dedicated Key Generation ranges/standby, Snowflake/ULID in-app, or consensus leases.",
            }
        )

    if req_tids & {
        "content_filter",
        "rate_limiter",
        "auth_service",
        "waf_ddos",
        "scheduler",
    } or any(
        tok in corpus
        for tok in (
            "ttl",
            "expir",
            "malicious",
            "phishing",
            "rate limit",
            "abuse",
            "rbac",
            "sso",
        )
    ):
        capabilities.append(
            {
                "id": "safety_and_lifecycle",
                "title": "Safety, Access Control & Data Lifecycle",
                "goal": "Enforce abuse protection, authorization/blocklisting, and retention/TTL cleanup policies without blocking hot read paths.",
                "accepted_type_groups": [
                    ["content_filter"],
                    ["rate_limiter"],
                    ["auth_service"],
                    ["scheduler"],
                    ["waf_ddos"],
                    ["api_gateway"],
                ],
                "defence_tradeoff": "Specify lazy vs scheduled TTL cleanup, auth/blocklist lookup latency overhead, and abuse rate thresholds.",
            }
        )

    return capabilities


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


_EQUIVALENT_COMPONENT_ALTERNATIVES: dict[str, set[str]] = {
    "app_service": {"serverless_fn", "microservice"},
    "serverless_fn": {"app_service", "microservice"},
    "microservice": {"app_service", "serverless_fn"},
    "relational_db": {"nosql_kv"},
    "nosql_kv": {"relational_db"},
    "read_replica": {"nosql_kv"},
    "distributed_cache": {"local_cache"},
    "message_queue": {"event_stream", "pubsub_bus"},
    "event_stream": {"message_queue", "pubsub_bus"},
    "pubsub_bus": {"event_stream", "message_queue"},
    "async_worker": {"stream_processor", "serverless_fn"},
    "stream_processor": {"async_worker"},
}


def _describe_path_steps(steps: list[dict[str, Any]]) -> str:
    """Build a compact readable chain summary (A -> B -> C) from structured step dicts."""
    if not steps:
        return ""
    parts: list[str] = []
    for idx, step in enumerate(steps):
        src = str(step.get("source_label") or step.get("source_type_id") or "").strip()
        dst = str(step.get("target_label") or step.get("target_type_id") or "").strip()
        if idx == 0 and src:
            parts.append(src)
        if dst and (not parts or parts[-1] != dst):
            parts.append(dst)
    return " -> ".join(parts)


def evaluate_canvas_topology(
    flow_payload: dict[str, Any],
    resolved_blueprint: dict[str, Any],
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run deterministic pre-flight coaching checks on capabilities, valid alternatives, anti-patterns, and SPOFs."""
    nodes = [n for n in (flow_payload.get("nodes") or []) if isinstance(n, dict)]
    edges = [e for e in (flow_payload.get("edges") or []) if isinstance(e, dict)]
    canvas_notes = str(flow_payload.get("notes") or "").lower()
    required_components = list(resolved_blueprint.get("required_components") or [])
    expected_paths = list(resolved_blueprint.get("expected_paths") or [])
    out_of_scope_text = str(resolved_blueprint.get("out_of_scope_text") or "").lower()
    required_capabilities = list(
        resolved_blueprint.get("required_capabilities")
        or synthesize_required_capabilities(brief, None, required_components)
    )

    node_by_id = {str(n.get("id")): n for n in nodes if n.get("id")}
    placed_type_ids = {str(n.get("type_id") or "") for n in nodes}

    # Build adjacency before capability wiring checks
    incoming: dict[str, int] = {nid: 0 for nid in node_by_id}
    outgoing: dict[str, int] = {nid: 0 for nid in node_by_id}
    for edge in edges:
        src_id = str(edge.get("source") or "")
        dst_id = str(edge.get("target") or "")
        if src_id in node_by_id and dst_id in node_by_id:
            outgoing[src_id] += 1
            incoming[dst_id] += 1

    # 1. Non-spoiling Capability Coverage + Valid Architectural Alternatives
    placed_required_count = 0
    alternative_notes: list[str] = []
    for req in required_components:
        req_tid = str(req.get("type_id") or "")
        is_present = any(
            node_matches_expected(n, req["name"])
            or (req_tid != "custom" and n.get("type_id") == req_tid)
            for n in nodes
        )
        alt_types = _EQUIVALENT_COMPONENT_ALTERNATIVES.get(req_tid, set())
        matched_alt = next((alt for alt in alt_types if alt in placed_type_ids), None)
        if is_present:
            placed_required_count += 1
        elif matched_alt:
            placed_required_count += 1
            alt_block = BLOCKS_BY_TYPE_ID.get(matched_alt)
            alt_label = alt_block["label"] if alt_block else matched_alt
            msg = f"Using {alt_label} cleanly covers {req['label']} responsibilities."
            if msg not in alternative_notes:
                alternative_notes.append(msg)

    capability_checks: list[dict[str, Any]] = []
    defence_probes: list[str] = []
    met_capabilities = 0
    for cap in required_capabilities:
        groups = cap.get("accepted_type_groups") or []
        matched_nodes: list[dict[str, Any]] = []
        matched_group: list[str] = []
        for grp in groups:
            if grp and all(tid in placed_type_ids for tid in grp):
                matched_group = grp
                matched_nodes = [n for n in nodes if str(n.get("type_id") or "") in grp]
                break

        if not matched_nodes:
            capability_checks.append(
                {
                    "id": cap["id"],
                    "title": cap["title"],
                    "goal": cap["goal"],
                    "status": "pending",
                    "satisfied_by": "",
                    "defence_tradeoff": cap.get("defence_tradeoff") or "",
                }
            )
            continue

        all_wired = len(nodes) == 1 or any(
            incoming[str(n["id"])] > 0 or outgoing[str(n["id"])] > 0
            for n in matched_nodes
            if n.get("id")
        )
        placed_labels = ", ".join(
            dict.fromkeys(
                str(n.get("label") or n.get("type_id") or "") for n in matched_nodes
            )
        )
        status = "met" if all_wired else "partial"
        if status == "met":
            met_capabilities += 1
        capability_checks.append(
            {
                "id": cap["id"],
                "title": cap["title"],
                "goal": cap["goal"],
                "status": status,
                "satisfied_by": placed_labels,
                "defence_tradeoff": cap.get("defence_tradeoff") or "",
            }
        )
        if matched_group and cap.get("defence_tradeoff"):
            defence_probes.append(
                f"{cap['title']} ({placed_labels}): {cap['defence_tradeoff']}"
            )

    total_required = len(required_components)
    total_caps = len(capability_checks)
    coverage_pct = (
        round((met_capabilities / total_caps) * 100)
        if total_caps
        else (
            round((placed_required_count / total_required) * 100)
            if total_required
            else 100
        )
    )

    findings: list[dict[str, Any]] = []
    for alt_msg in alternative_notes:
        findings.append(
            {
                "severity": "info",
                "title": "Valid Alternative Choice",
                "detail": alt_msg,
            }
        )

    # 2. Structural & directional anti-pattern checks on drawn edges
    seen_reversed_checks: set[str] = set()

    for edge in edges:
        src_id = str(edge.get("source") or "")
        dst_id = str(edge.get("target") or "")
        if src_id not in node_by_id or dst_id not in node_by_id:
            continue

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

        if src_type in (
            "web_client",
            "mobile_client",
            "webhook_actor",
        ) and dst_type in (
            "relational_db",
            "nosql_kv",
            "distributed_cache",
        ):
            if "client_to_internal" not in seen_reversed_checks:
                seen_reversed_checks.add("client_to_internal")
                findings.append(
                    {
                        "severity": "flow_direction",
                        "title": "Direct Client Connection to Internal Data Store",
                        "detail": (
                            f"{node_by_id[src_id].get('label')} connects straight to {node_by_id[dst_id].get('label')}. "
                            "Terminate client traffic at API Gateway / Load Balancer / App Service for auth, validation, and connection pooling."
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
    req_tids_set = {r["type_id"] for r in required_components}
    is_streaming_excluded = bool(
        re.search(
            r"(?:real-time|sub-second).{0,30}(?:analytics|stream|dashboard)",
            out_of_scope_text,
        )
    )
    if (
        "stream_processor" in placed_type_ids
        and "stream_processor" not in req_tids_set
        and (is_streaming_excluded or "message_queue" in req_tids_set)
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
        raw_steps = path.get("steps") or []
        for step in raw_steps:
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
            step_results.append(
                {
                    **step,
                    "satisfied": satisfied,
                    "placed_both": src_tid in placed_type_ids
                    and dst_tid in placed_type_ids,
                }
            )
        path_milestones.append(
            {
                "id": path.get("id") or "path",
                "title": path.get("title") or "Path",
                "description": _describe_path_steps(step_results),
                "completed": completed_steps,
                "total": len(step_results),
                "satisfied": bool(step_results)
                and completed_steps == len(step_results),
                "steps": step_results,
            }
        )

    warning_count = sum(1 for f in findings if f.get("severity") != "info")
    if not nodes:
        summary = (
            f"0 active warnings · {total_caps} architectural capability goal(s) ready "
            "(design any defendable stack or open Bank for 1 full reference blueprint)."
        )
    elif warning_count == 0:
        summary = f"0 structural warnings · {met_capabilities}/{total_caps} capabilities addressed."
    else:
        summary = (
            f"{warning_count} structural check(s) to address · "
            f"{met_capabilities}/{total_caps} capabilities addressed."
        )

    return {
        "placed_required_count": placed_required_count,
        "total_required_count": total_required,
        "coverage_pct": coverage_pct,
        "met_capabilities_count": met_capabilities,
        "total_capabilities_count": total_caps,
        "capability_checks": capability_checks,
        "defence_probes": defence_probes[:6],
        "path_milestones": path_milestones,
        "findings": findings,
        "next_connection_hint": next_connection_hint,
        "summary": summary,
    }


def build_coach_canvas_actions(
    resolved_blueprint: dict[str, Any],
    flow_payload: dict[str, Any],
    user_message: str = "",
    cloud_provider: str | None = None,
) -> list[dict[str, Any]]:
    """Build non-destructive executable Apply-to-Canvas actions prioritized by the learner's question."""
    active_cloud = normalize_cloud_provider(
        cloud_provider or flow_payload.get("cloud_provider")
    )
    nodes = [n for n in (flow_payload.get("nodes") or []) if isinstance(n, dict)]
    edges = [e for e in (flow_payload.get("edges") or []) if isinstance(e, dict)]
    placed_types = {str(n.get("type_id") or "") for n in nodes}
    required_components = list(resolved_blueprint.get("required_components") or [])
    expected_paths = list(resolved_blueprint.get("expected_paths") or [])
    by_type = {
        str(c.get("type_id") or ""): c for c in required_components if c.get("type_id")
    }

    path_actions: list[dict[str, Any]] = []
    lower_msg = str(user_message or "").lower()

    # Draw / wire individual reference paths first (prioritized if matching user's prompt)
    def _path_priority(path_item: dict[str, Any]) -> int:
        text = f"{path_item.get('id', '')} {path_item.get('title', '')}".lower()
        if "write" in lower_msg and "write" in text:
            return 0
        if "read" in lower_msg and "read" in text:
            return 0
        if any(k in lower_msg for k in ("async", "ttl", "queue", "worker")) and any(
            k in text for k in ("async", "ttl", "lifecycle", "background")
        ):
            return 0
        return 1

    for path in sorted(expected_paths, key=_path_priority):
        pid = str(path.get("id") or "path")
        ptitle = str(path.get("title") or "Architecture Path")
        raw_steps = [s for s in (path.get("steps") or []) if isinstance(s, dict)]
        if not raw_steps:
            continue

        needed_edges = []
        path_type_ids: list[str] = []
        for step in raw_steps:
            src_tid = str(step.get("source_type_id") or "")
            dst_tid = str(step.get("target_type_id") or "")
            if src_tid and src_tid not in path_type_ids:
                path_type_ids.append(src_tid)
            if dst_tid and dst_tid not in path_type_ids:
                path_type_ids.append(dst_tid)
            if (
                src_tid
                and dst_tid
                and not _edges_match_step(nodes, edges, src_tid, dst_tid)
            ):
                needed_edges.append(
                    {
                        "source_type_id": src_tid,
                        "source_label": str(step.get("source_label") or src_tid),
                        "target_type_id": dst_tid,
                        "target_label": str(step.get("target_label") or dst_tid),
                        "label": str(step.get("suggested_label") or ""),
                        "delivery_mode": str(step.get("delivery_mode") or "sync"),
                    }
                )

        def _cloudify_block(spec_dict: dict[str, Any]) -> dict[str, Any]:
            item = dict(spec_dict)
            tid = str(item.get("type_id") or "")
            svc = get_cloud_service_name(tid, active_cloud)
            generic_lbl = str(item.get("label") or item.get("name") or "")
            item["generic_label"] = generic_lbl
            item["cloud_provider"] = active_cloud
            if svc:
                item["label"] = svc
                item["tech_stack"] = svc
            return item

        needed_blocks: list[dict[str, Any]] = []
        for tid in path_type_ids:
            if tid not in placed_types:
                spec = by_type.get(tid) or BLOCKS_BY_TYPE_ID.get(tid)
                if spec:
                    needed_blocks.append(_cloudify_block(spec))

        if needed_blocks or needed_edges:
            path_actions.append(
                {
                    "id": f"apply_{pid}",
                    "title": f"Draw {ptitle}",
                    "description": _describe_path_steps(raw_steps),
                    "blocks": needed_blocks,
                    "edges": needed_edges,
                }
            )

    all_blocks: list[dict[str, Any]] = []
    all_edges: list[dict[str, Any]] = []
    seen_full_blocks: set[str] = set()
    seen_full_edges: set[tuple[str, str]] = set()
    for act in path_actions:
        for blk in act.get("blocks") or []:
            bkey = f"{blk.get('type_id')}:{blk.get('label')}"
            if bkey not in seen_full_blocks:
                seen_full_blocks.add(bkey)
                all_blocks.append(blk)
        for edg in act.get("edges") or []:
            ekey = (
                str(edg.get("source_type_id") or ""),
                str(edg.get("target_type_id") or ""),
            )
            if ekey not in seen_full_edges:
                seen_full_edges.add(ekey)
                all_edges.append(edg)

    if len(path_actions) >= 2 and (all_blocks or all_edges):
        path_actions.insert(
            0,
            {
                "id": "build_full_reference",
                "title": "Build Full Reference System",
                "description": f"Places {len(all_blocks)} reference blocks & {len(all_edges)} end-to-end wires across all flows (one valid blueprint).",
                "blocks": all_blocks,
                "edges": all_edges,
            },
        )

    missing_specs = [
        spec
        for spec in required_components
        if not any(
            node_matches_expected(n, spec["name"])
            or (spec["type_id"] != "custom" and n.get("type_id") == spec["type_id"])
            for n in nodes
        )
    ]
    if missing_specs and len(path_actions) < 3:
        cloudified_missing = []
        for spec in missing_specs:
            item = dict(spec)
            tid = str(item.get("type_id") or "")
            svc = get_cloud_service_name(tid, active_cloud)
            item["generic_label"] = str(item.get("label") or item.get("name") or "")
            item["cloud_provider"] = active_cloud
            if svc:
                item["label"] = svc
                item["tech_stack"] = svc
            cloudified_missing.append(item)
        path_actions.append(
            {
                "id": "add_missing_components",
                "title": f"Place Missing Blocks ({len(missing_specs)})",
                "description": ", ".join(s["label"] for s in missing_specs[:5])
                + ("..." if len(missing_specs) > 5 else ""),
                "blocks": cloudified_missing,
                "edges": [],
            }
        )

    return path_actions[:4]
