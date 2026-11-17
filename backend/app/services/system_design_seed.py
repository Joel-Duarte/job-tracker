from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_design import SystemDesignChallengeModel


def _step(
    src: str,
    dst: str,
    suggested_label: str = "",
    rationale: str = "",
    delivery_mode: str = "sync",
) -> dict[str, Any]:
    return {
        "source_type_id": src,
        "target_type_id": dst,
        "delivery_mode": delivery_mode,
        "suggested_label": suggested_label,
        "rationale": rationale,
    }


def _cap(
    cid: str,
    title: str,
    goal: str,
    groups: list[list[str]],
    defence_tradeoff: str = "",
) -> dict[str, Any]:
    return {
        "id": cid,
        "title": title,
        "goal": goal,
        "accepted_type_groups": groups,
        "defence_tradeoff": defence_tradeoff,
    }


CURATED_CHALLENGES: list[dict[str, Any]] = [
    {
        "slug": "url-shortener",
        "title": "Design a URL Shortener",
        "category": "DISTRIBUTED_SYSTEMS",
        "difficulty": "EASY",
        "prompt_summary": "Build a service that creates short, shareable aliases for long URLs and redirects users reliably with low latency.",
        "initial_prompt": (
            "We need to design a URL shortening service like bit.ly or TinyURL. "
            "Users should be able to generate short links for arbitrary long URLs and "
            "be redirected when visiting a short link. Let's start with requirements discovery: "
            "what clarifying questions do you have about scale, features, and constraints?"
        ),
        "tags": ["hashing", "caching", "key-generation", "redirects", "read-heavy"],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Global public URL shortening service for consumers, marketers, and API integrations to share compact links and track basic aggregate click counts.",
                "target_users": "Public web visitors following links, anonymous/authenticated link creators, and internal partner apps.",
                "privacy_and_access": "Short links are public by default (no authentication required to follow a redirect); short codes must be non-sequential and non-predictable to prevent enumeration/scraping; HTTPS enforced and malicious URLs blocked.",
                "analytics_model": "Basic aggregate click count per short link via asynchronous eventual consistency (1-5 minute freshness lag is acceptable; never block the redirect path).",
            },
            "scale_estimates": {
                "mau": "~80M monthly active users (MAU)",
                "dau": "20M daily active users (DAU)",
                "daily_creation_volume": "~3.3M new shortened URLs created per day (~100M/month; ~40 writes/s average, ~120 writes/s peak)",
                "daily_redirect_volume": "~330M redirects/day (~4,000 redirect QPS average, ~12,000 peak QPS; 100:1 read-to-write ratio)",
                "payload_and_storage": "~500 bytes per URL mapping record; 7-char Base62 short codes; ~300M active records over 5 years (~150 GB raw mapping data before indexes and replicas)",
            },
            "functional_requirements": [
                "Create a unique 7-character Base62 short URL from a valid long URL",
                "Optional custom short alias selection with uniqueness/collision handling",
                "Redirect from short code to original URL (HTTP 301 vs 302 trade-off)",
                "Default 5-year link retention lifecycle plus optional user-specified TTL/expiration timestamp",
                "Asynchronous eventual-consistency click count analytics",
            ],
            "non_functional_requirements": [
                "99.99% availability on the redirect read path",
                "p99 redirect latency < 30ms; link creation latency < 200ms",
                "Zero short-code collisions and non-predictable/non-sequential codes for link privacy",
                "Eventual consistency acceptable for click analytics (1-5 minute lag); read path decoupled from analytics writes",
            ],
            "constraints": [
                "Global user base: reads served globally at low latency; writes can terminate in regional primaries",
                "Treat POST /links creation and GET /{short_code} redirection as distinct traffic flows with independent latency and capacity concerns; they may remain handlers in one service until scale justifies separation",
                "Default retention is 5 years unless an explicit shorter TTL is provided; expired links return HTTP 410/404",
                "No authentication required on redirect path; malicious/phishing destination URLs must be rejected",
            ],
            "priorities": [
                "P0: Fast (<30ms p99) and highly available (99.99%) URL redirects",
                "P1: Collision-free, non-predictable 7-char Base62 code generation and default 5-year lifecycle + optional TTL",
                "P2: Eventual-consistency click counting and optional custom aliases",
            ],
            "out_of_scope": [
                "Interstitial link-preview or warning pages",
                "User billing, paid plans, or subscription management",
                "Custom branded domain SSL certificate provisioning",
                "Real-time sub-second streaming analytics dashboards",
            ],
            "hidden_context": {
                "dau": "80M MAU; 20M daily active users; ~3.3M new URLs/day (~100M/month)",
                "read_write_ratio": "100:1 read-heavy (~330M redirects/day; ~4,000 redirect QPS average, ~12,000 peak QPS; ~40 writes/s average, ~120 peak)",
                "payload_size": "~500 bytes per URL mapping record; short code length 7 chars (Base62)",
                "retention": "Default 5-year retention (~300M total records over 5 years, ~150 GB raw mapping data before indexes and replicas) plus optional user-specified TTL",
                "privacy_and_security": "Public links by default (no login to redirect); non-sequential/non-predictable short codes; HTTPS + URL blocklist",
                "analytics": "Asynchronous eventual consistency (1-5 min lag acceptable; decoupled from redirect latency)",
                "latency_sla": "p99 redirect latency < 30ms; link creation < 200ms",
                "availability_target": "99.99% availability on redirects (eventual consistency acceptable for analytics)",
                "geographic_distribution": "Global user base; reads served globally, writes can terminate in regional primaries",
                "optional_features": "Custom aliases supported with uniqueness checks; basic click count analytics eventual; no preview page required",
            },
            "expected_functional_requirements": [
                "Create a unique short URL from a valid long URL",
                "Optional custom short alias selection with collision handling",
                "Redirect HTTP 301 vs 302 from short code to original URL",
                "Link expiration / TTL support",
                "Basic click count analytics (asynchronous)",
            ],
            "expected_non_functional_requirements": [
                "High availability (99.99%) on the redirect read path",
                "Low read latency (< 30ms p99) via in-memory caching / CDN edge",
                "Zero short-code collisions and non-predictable/non-sequential URLs if privacy desired",
                "Read-path decoupling from analytics writes",
            ],
            "expected_components": [
                "Web / Browser Client",
                "CDN / Edge Cache",
                "Load Balancer",
                "API Gateway",
                "Stateless App Service (write + redirect handlers)",
                "URL / Payload Safety Filter (malicious/phishing blocklist check)",
                "Unique ID / Key Generator (KGS with pre-allocated ranges or active-active standby)",
                "Distributed Cache (Redis) for hot short-to-long URL mappings",
                "Primary Relational DB (PostgreSQL / DynamoDB keyed on short_code)",
                "DB Read Replica for cache-miss read scaling and failover",
                "Scheduler / TTL Sweeper for optional link expiration lifecycle",
                "Task Queue (async click event buffer)",
                "Background Worker Pool (batched eventual-consistency click counter updates)",
            ],
            "expected_paths": [
                {
                    "id": "read_path",
                    "title": "Read Path (Low-Latency Redirect)",
                    "steps": [
                        _step(
                            "web_client",
                            "cdn",
                            "GET /{short_code}",
                            "Serve globally cached redirects from the edge first.",
                        ),
                        _step(
                            "cdn",
                            "load_balancer",
                            "Cache miss forward",
                            "Forward CDN misses across healthy L7 load balancers.",
                        ),
                        _step(
                            "load_balancer",
                            "api_gateway",
                            "Route request",
                            "Terminate TLS and enforce routing policies.",
                        ),
                        _step(
                            "api_gateway",
                            "app_service",
                            "Dispatch redirect",
                            "Pass validated lookup to stateless redirect handlers.",
                        ),
                        _step(
                            "app_service",
                            "distributed_cache",
                            "Redis lookup / populate",
                            "Check hot key mappings in Redis before querying storage.",
                        ),
                        _step(
                            "app_service",
                            "read_replica",
                            "Miss fallback query",
                            "Read cold mappings from replicas without locking primary writes.",
                        ),
                    ],
                },
                {
                    "id": "write_path",
                    "title": "Write & Safety Creation Path",
                    "steps": [
                        _step(
                            "app_service",
                            "content_filter",
                            "Check phishing/blocklist",
                            "Reject malicious destinations before minting a short code.",
                        ),
                        _step(
                            "app_service",
                            "id_generator",
                            "Mint Base62 code",
                            "Allocate collision-free non-sequential 7-char codes synchronously.",
                        ),
                        _step(
                            "app_service",
                            "relational_db",
                            "Persist mapping + TTL",
                            "Write durable short-to-long mapping and expires_at timestamp.",
                        ),
                        _step(
                            "relational_db",
                            "read_replica",
                            "Replicate writes",
                            "Asynchronously replicate mappings for read scaling.",
                            "async",
                        ),
                    ],
                },
                {
                    "id": "async_lifecycle_path",
                    "title": "Async Click Analytics & TTL Cleanup",
                    "steps": [
                        _step(
                            "app_service",
                            "message_queue",
                            "Enqueue click event",
                            "Keep redirect latency decoupled from analytics writes.",
                            "async",
                        ),
                        _step(
                            "message_queue",
                            "async_worker",
                            "Consume & aggregate",
                            "Batch click increments safely off the critical path.",
                            "async",
                        ),
                        _step(
                            "async_worker",
                            "relational_db",
                            "Flush click counts",
                            "Persist rolled-up aggregate click counts.",
                            "async",
                        ),
                        _step(
                            "scheduler",
                            "relational_db",
                            "Sweep expired links",
                            "Periodically purge or archive expired TTL mappings.",
                            "async",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "edge_ingress",
                    "Edge Caching & Ingress Routing",
                    "Route public redirect/create traffic via CDN/Edge, Load Balancer, or API Gateway without exposing DB/cache directly.",
                    [["cdn"], ["load_balancer"], ["api_gateway"], ["waf_ddos"]],
                    "Defend HTTP 301 vs 302 cacheability if relying heavily on CDN edge caching.",
                ),
                _cap(
                    "compute",
                    "Stateless Create & Redirect Service",
                    "Run URL validation, short-code orchestration, and redirect resolution in stateless compute.",
                    [["app_service"], ["serverless_fn"], ["microservice"]],
                ),
                _cap(
                    "fast_cache",
                    "Sub-30ms Hot-Read Caching",
                    "Keep 100:1 redirect p99 < 30ms via in-memory cache, CDN, or bloom filter.",
                    [["distributed_cache"], ["local_cache"], ["cdn"]],
                    "Explain cache-aside misses, TTL invalidation, and Redis failure stampede mitigation.",
                ),
                _cap(
                    "key_minting",
                    "Collision-Free Short Code Minting",
                    "Issue unique, non-predictable 7-char Base62 keys cleanly under concurrent writes.",
                    [["id_generator"], ["consensus_store"], ["app_service"]],
                    "Explain pre-allocated key ranges or active-active KGS standby to avoid SPOFs.",
                ),
                _cap(
                    "durable_store",
                    "Durable Mapping Persistence",
                    "Store 300M+ mappings safely with read-scaling or partitioned NoSQL KV.",
                    [["relational_db"], ["nosql_kv"]],
                ),
                _cap(
                    "async_ttl",
                    "Decoupled Analytics & Safety/TTL Lifecycle",
                    "Handle click counting off-path plus malicious URL blocking and 5-year/custom TTL cleanup.",
                    [
                        ["message_queue"],
                        ["event_stream"],
                        ["async_worker"],
                        ["scheduler"],
                        ["content_filter"],
                    ],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Single auto-increment database sequence bottleneck or single KGS instance without standby/pre-allocated ranges",
                "Synchronous analytics DB writes on the redirect critical path",
                "Cache stampede / cold cache hits on viral links",
                "Missing discussion of HTTP 301 (browser caches, breaks analytics) vs 302/307 trade-offs",
            ],
            "over_engineering_traps": [
                "Multi-datacenter active-active synchronous consensus (Paxos/Raft) on every click analytics increment",
                "Complex microservice mesh when two stateless handlers (write + redirect) suffice",
            ],
            "defence_questions": [
                "Why did you choose HTTP 301 vs 302 for redirects, and how does that affect both latency and analytics?",
                "How do you guarantee two concurrent requests never receive the same short code without adding a single point of failure?",
                "What happens when a celebrity shares a short link that suddenly receives 50,000 requests/second?",
                "If Redis goes down completely, will your database survive the thundering herd?",
            ],
            "default_variant_meta": {
                "variant_id": "public-consumer-shortener",
                "title": "Public Consumer Link Shortener",
                "focus_summary": "80M MAU, 3.3M links/day, 12k peak QPS, 5-year TTL, public non-predictable codes, eventual click counts",
                "difficulty_hint": "EASY",
            },
            "extra_variants": [
                {
                    "variant_id": "enterprise-compliance-linker",
                    "title": "Enterprise Internal Compliance Linker",
                    "focus_summary": "150k employees, SSO/RBAC private links, custom domains, audit logs, Postgres-first YAGNI",
                    "difficulty_hint": "EASY",
                    "business_context": {
                        "product_goal": "Internal corporate URL shortener for workspaces, SSO-gated wiki/ticket links, and security compliance teams.",
                        "target_users": "150,000 authenticated corporate employees and automated CI/bot integrations.",
                        "privacy_and_access": "Private by default: only authenticated SSO users in the workspace tenant may resolve links; per-link ACL groups supported; zero anonymous public access.",
                        "analytics_model": "Strongly consistent compliance audit trail logging creator, timestamp, and resolver identity for every click (regulatory retention 7 years).",
                    },
                    "scale_estimates": {
                        "mau": "150,000 employees (100k DAU)",
                        "daily_creation_volume": "~25,000 new internal short links/day (< 2 writes/sec peak)",
                        "daily_redirect_volume": "~1.5M redirects/day (~20 avg / ~150 peak QPS, concentrated 9am-5pm regional business hours)",
                        "payload_and_storage": "~1 KB per link record + ~3.5 KB/redirect audit log (~5 GB/day compliance audit log growth)",
                    },
                    "functional_requirements": [
                        "SSO/OIDC authenticated link creation and namespace-scoped custom aliases (e.g. go/roadmap)",
                        "RBAC authorization check before issuing HTTP 302 redirect",
                        "Workspace custom domain routing and link ownership transfer",
                        "Immutable compliance audit log export for every redirect access",
                    ],
                    "non_functional_requirements": [
                        "99.95% availability during corporate business hours",
                        "p99 redirect latency < 80ms including SSO session/ACL check",
                        "Strict auditability and zero unauthorized cross-tenant resolution",
                    ],
                    "constraints": [
                        "Lean 2-engineer platform team: favor managed PostgreSQL + single Redis session cache over distributed NoSQL/Kafka stacks",
                        "Audit records must be retained 7 years for SOC2 compliance",
                    ],
                    "priorities": [
                        "P0: RBAC access enforcement and immutable audit logging",
                        "P1: Operational simplicity and easy custom keyword alias resolution",
                    ],
                    "out_of_scope": [
                        "Anonymous unauthenticated consumer short links",
                        "Global edge CDN caching of private redirect targets",
                    ],
                    "hidden_context": {
                        "dau": "150k registered employees; 100k DAU; ~25k new links/day",
                        "read_write_ratio": "60:1 (~150 peak redirect QPS, <2 peak write QPS)",
                        "privacy_and_security": "Private SSO/RBAC links by default; never publicly cache target URLs on shared CDNs",
                        "retention": "Links active until revoked/archived; compliance audit logs immutable for 7 years",
                        "analytics": "Strongly logged audit events (not best-effort approximate counts)",
                    },
                    "expected_components": [
                        "Web / Browser Client (Corporate SSO browser)",
                        "API Gateway (OIDC / SSO middleware)",
                        "Auth / IAM Service (Workspace RBAC & ACL checks)",
                        "Stateless App Service (Link create, resolve, audit)",
                        "Distributed Cache (Redis for SSO sessions & go/alias)",
                        "Primary Relational DB (PostgreSQL link + partitioned audit log)",
                        "Object / Blob Storage (Cold >90-day S3 Glacier archive)",
                        "Scheduler / TTL Sweeper (Audit partition archiver)",
                    ],
                    "expected_paths": [
                        {
                            "id": "private_redirect_path",
                            "title": "Authenticated Private Redirect Path",
                            "steps": [
                                _step(
                                    "web_client",
                                    "api_gateway",
                                    "HTTPS + SSO cookie",
                                    "All internal go/links must terminate at corporate gateway (no public CDN).",
                                ),
                                _step(
                                    "api_gateway",
                                    "auth_service",
                                    "Verify OIDC / ACL",
                                    "Enforce corporate SSO session and tenant RBAC.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Resolve alias",
                                    "Handle private alias lookup after auth.",
                                ),
                                _step(
                                    "app_service",
                                    "distributed_cache",
                                    "Hot go/alias & token lookup",
                                    "Accelerate corporate navigation with short-TTL Redis lookups.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Miss fallback + log",
                                    "Fetch link metadata and commit strongly logged access record.",
                                ),
                            ],
                        },
                        {
                            "id": "audit_archive_path",
                            "title": "7-Year Audit Lifecycle Path",
                            "steps": [
                                _step(
                                    "scheduler",
                                    "relational_db",
                                    "Detach >90d partition",
                                    "Keep primary B-trees lean by rotating time partitions.",
                                    "async",
                                ),
                                _step(
                                    "relational_db",
                                    "object_storage",
                                    "Archive to cold object store",
                                    "Retain immutable 7-year SOC2 logs cost-effectively.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "private_ingress_auth",
                            "Authenticated Private Ingress & RBAC (No Public CDN)",
                            "Enforce corporate OIDC/SSO and workspace ACLs before redirecting—never serve private targets on public CDNs.",
                            [
                                ["api_gateway", "auth_service"],
                                ["api_gateway"],
                                ["auth_service"],
                                ["load_balancer"],
                            ],
                            "Defend why HTTP 302 + Cache-Control: private protects confidential links.",
                        ),
                        _cap(
                            "lean_compute",
                            "Lean Modular Compute (YAGNI)",
                            "Handle link creation, custom go/ aliases, and audit emission cleanly without distributed microservices bloat.",
                            [["app_service"], ["microservice"]],
                        ),
                        _cap(
                            "postgres_audit",
                            "Relational Storage, Session Cache & 7-Year Archival",
                            "Back 150 QPS cleanly with PostgreSQL + optional Redis cache and cold partition archiving for 7-year SOC2 logs.",
                            [["relational_db"], ["nosql_kv"]],
                            "Explain time-partitioning + cold archive so audit writes don't bloat primary lookups.",
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Caching private redirects on public CDN POPs bypassing RBAC permission checks",
                        "Unpartitioned multi-year audit log table bloating primary PostgreSQL B-tree indexes",
                    ],
                    "over_engineering_traps": [
                        "Deploying multi-region Cassandra, ZooKeeper KGS, and Flink streaming clusters for 150 peak QPS",
                    ],
                    "defence_questions": [
                        "Why can't we use HTTP 301 browser caching or a public CDN cache for `go/q4-layoffs`?",
                        "With only 150 peak QPS, why did you choose (or avoid) sharded NoSQL and Kafka?",
                        "How do you retain 7 years of click audit logs without slowing down live link lookups in PostgreSQL?",
                    ],
                },
                {
                    "variant_id": "viral-adtech-tracker",
                    "title": "Viral Ad-Tech Campaign Link & Analytics Engine",
                    "focus_summary": "300M DAU, 150k peak QPS bursts, geo/device targeting, real-time sub-second clickstream, 90-day TTL",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "High-throughput ad-tech campaign link router enabling device/geo destination branching and real-time conversion analytics.",
                        "target_users": "Enterprise advertisers launching Super Bowl / flash-sale social blasts and 300M DAU clickers.",
                        "privacy_and_access": "Public redirect endpoints with strict open-redirect signature validation and GDPR IP anonymization in analytics.",
                        "analytics_model": "Near real-time clickstream analytics (< 5 seconds dashboard freshness) with bot/fraud deduplication.",
                    },
                    "scale_estimates": {
                        "mau": "900M MAU",
                        "dau": "300M DAU",
                        "daily_creation_volume": "~20M campaign/tracking URLs created/day (~230 writes/s avg, ~1,500 batch campaign burst/s)",
                        "daily_redirect_volume": "~3B redirects/day (~35,000 QPS avg, ~150,000 peak QPS on viral drops)",
                        "payload_and_storage": "~1.2 KB per rule-bearing link; ~300 TB/year raw compressed clickstream events",
                    },
                    "functional_requirements": [
                        "Create parameterized short links supporting device/country conditional redirect rules",
                        "Sub-30ms redirect resolution even during 150k QPS flash-sale spikes",
                        "Real-time bot filtering and geo/device click attribution (< 5s dashboard freshness)",
                        "Automatic 90-day default link TTL with configurable advertiser campaign windows",
                    ],
                    "non_functional_requirements": [
                        "99.995% availability on global redirect path",
                        "p99 redirect latency < 25ms globally via edge routing + distributed cache",
                        "Analytics pipeline must handle 150k events/sec without dropping revenue-attributed clicks",
                    ],
                    "constraints": [
                        "Flash campaigns create extreme hot-key skew (100k QPS hitting a single short code)",
                        "GDPR requires IP truncation/anonymization before analytics persistence",
                    ],
                    "priorities": [
                        "P0: Survive 100k QPS hot-key viral spikes with < 25ms p99 redirect latency",
                        "P1: Zero lost billable click events with < 5s analytics freshness and bot filtering",
                    ],
                    "out_of_scope": [
                        "Manual ad creative image hosting and DSP real-time bidding auctions",
                    ],
                    "hidden_context": {
                        "dau": "900M MAU; 300M DAU; ~20M links/day; ~3B redirects/day (150k peak QPS)",
                        "retention": "Default 90-day active redirect TTL; aggregated analytics retained 2 years",
                        "analytics": "Near real-time (< 5s freshness), bot-filtered, GDPR IP anonymized",
                    },
                    "expected_components": [
                        "Web / Browser Client",
                        "DNS / GeoDNS (Multi-region Anycast routing)",
                        "CDN / Edge Cache (Regional edge redirect POPs)",
                        "Load Balancer",
                        "API Gateway",
                        "Stateless App Service (Geo/device rule resolver & campaign write API)",
                        "Unique ID / Key Generator (Collision-free high-volume code minting)",
                        "Local / L1 In-Process Cache (Mitigate 100k QPS single-link hot keys)",
                        "Distributed Cache (Redis Cluster)",
                        "NoSQL / Wide-Column / KV DB (DynamoDB / Cassandra / sharded CockroachDB)",
                        "Event Log / Kafka Stream (150k click events/sec ingest)",
                        "Stream Processor (Flink bot filtering, IP anonymization & 5s windows)",
                        "Analytics / OLAP Store (ClickHouse / Druid real-time advertiser queries)",
                        "Scheduler / TTL Sweeper (90-day default campaign expiry)",
                    ],
                    "expected_paths": [
                        {
                            "id": "read_path",
                            "title": "Flash-Spike Redirect Path (<25ms p99)",
                            "steps": [
                                _step(
                                    "web_client",
                                    "dns",
                                    "Anycast DNS lookup",
                                    "Steer 300M DAU to closest healthy regional POP.",
                                ),
                                _step(
                                    "dns",
                                    "cdn",
                                    "Edge POP entry",
                                    "Terminate TLS near end users before forwarding uncached rule redirects.",
                                ),
                                _step(
                                    "cdn",
                                    "load_balancer",
                                    "Forward origin requests",
                                    "Spread 150k peak QPS evenly across backend tiers.",
                                ),
                                _step(
                                    "load_balancer",
                                    "api_gateway",
                                    "Route & validate",
                                    "Enforce open-redirect signature checks and campaign routing.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Evaluate geo/device rules",
                                    "Resolve dynamic targeting rules in stateless redirect pods.",
                                ),
                                _step(
                                    "app_service",
                                    "local_cache",
                                    "L1 hot-key shield",
                                    "Serve Super-Bowl single-key spikes from in-process RAM before Redis.",
                                ),
                                _step(
                                    "app_service",
                                    "distributed_cache",
                                    "Redis Cluster lookup",
                                    "Serve remaining active campaign rules with sub-millisecond reads.",
                                ),
                                _step(
                                    "app_service",
                                    "nosql_kv",
                                    "Cold key miss query",
                                    "Fall back to horizontally partitioned KV store on cache miss.",
                                ),
                            ],
                        },
                        {
                            "id": "write_path",
                            "title": "Campaign Link Creation Path",
                            "steps": [
                                _step(
                                    "web_client",
                                    "api_gateway",
                                    "POST /campaigns/links",
                                    "Advertisers publish parameterized campaign links.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Validate rules & target",
                                    "Ensure safe open-redirect signatures and TTL rules.",
                                ),
                                _step(
                                    "app_service",
                                    "id_generator",
                                    "Mint short code",
                                    "Assign collision-free short codes during 1.5k/s campaign drops.",
                                ),
                                _step(
                                    "app_service",
                                    "nosql_kv",
                                    "Persist link + rules + TTL",
                                    "Write partitioned metadata with 90-day default expiration.",
                                ),
                            ],
                        },
                        {
                            "id": "realtime_analytics_path",
                            "title": "Real-Time Attribution Pipeline (<5s)",
                            "steps": [
                                _step(
                                    "app_service",
                                    "event_stream",
                                    "Emit raw clickstream",
                                    "Publish clicks asynchronously without delaying HTTP 302.",
                                    "async",
                                ),
                                _step(
                                    "event_stream",
                                    "stream_processor",
                                    "Bot dedup + GDPR IP mask + 5s window",
                                    "Filter click fraud and truncate PII in Flink before sink.",
                                    "async",
                                ),
                                _step(
                                    "stream_processor",
                                    "olap_warehouse",
                                    "Write advertiser rollups",
                                    "Serve sub-second attribution dashboards from ClickHouse/Druid.",
                                    "async",
                                ),
                                _step(
                                    "scheduler",
                                    "nosql_kv",
                                    "Expire 90-day campaigns",
                                    "Reclaim inactive campaign links cleanly.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "global_edge",
                            "Global Anycast / Edge & Ingress Routing",
                            "Terminate 300M DAU traffic globally via Edge/DNS/CDN/LB/Gateway to meet <25ms p99 redirect latency.",
                            [
                                ["dns", "cdn"],
                                ["cdn"],
                                ["load_balancer"],
                                ["api_gateway"],
                            ],
                        ),
                        _cap(
                            "compute_rule_engine",
                            "Stateless Redirect, Rule & Key Minting Compute",
                            "Evaluate geo/device rules and create collision-free campaign links cleanly.",
                            [["app_service"], ["serverless_fn"], ["microservice"]],
                        ),
                        _cap(
                            "hotkey_shield",
                            "100k QPS Single-Key Skew Protection",
                            "Protect cache shards from melting when 100k QPS hits a single viral campaign code (L1 cache, edge cache, or replicated cache).",
                            [["local_cache"], ["cdn"], ["distributed_cache"]],
                            "If only using Redis Cluster without L1/edge cache, defend how one shard avoids 100k ops/s saturation.",
                        ),
                        _cap(
                            "partitioned_store",
                            "Horizontally Scalable Link & Rule Storage",
                            "Persist billions of links/TTL metadata using sharded NoSQL KV or partitioned SQL.",
                            [["nosql_kv"], ["relational_db"]],
                        ),
                        _cap(
                            "realtime_clickstream",
                            "Sub-5s Fraud-Filtered Clickstream Pipeline",
                            "Stream 150k click events/sec asynchronously through bot filtering & GDPR IP anonymization into analytical storage.",
                            [
                                ["event_stream", "stream_processor"],
                                ["event_stream", "async_worker"],
                                ["message_queue", "async_worker"],
                            ],
                            "Explain how basic queue consumers vs windowed Flink hit <5s freshness with GDPR anonymization.",
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Single Redis shard melting under a 100k QPS celebrity/Super Bowl hot link without local in-memory cache",
                        "Using HTTP 301 causing browsers to bypass the redirect tracker and lose advertiser conversion counts",
                        "Querying OLTP SQL directly for real-time advertiser dashboard aggregations",
                    ],
                    "over_engineering_traps": [
                        "Synchronous OLAP/ClickHouse writes directly inside the HTTP redirect handler",
                    ],
                    "defence_questions": [
                        "A single campaign link suddenly spikes to 120,000 requests/second. Won't sharding Redis by short_code still melt that one shard?",
                        "How do you deliver < 5-second analytics freshness at 150k clicks/sec without slowing down redirects or overloading OLTP storage?",
                        "Why MUST this system use HTTP 302/307 instead of 301?",
                    ],
                },
            ],
        },
    },
    {
        "slug": "spotify-100k",
        "title": "Design Spotify for 100,000 Users",
        "category": "MEDIA_STREAMING",
        "difficulty": "MEDIUM",
        "prompt_summary": "Design an audio streaming platform sized intentionally for 100,000 registered users with playlists, search, and offline/online playback.",
        "initial_prompt": (
            "Design a music streaming service similar to Spotify, scoped specifically to support "
            "100,000 total registered users. Before jumping into architecture, what questions "
            "would you like to ask to clarify the workload, catalog size, features, and constraints?"
        ),
        "tags": [
            "right-sizing",
            "audio-streaming",
            "cdn",
            "object-storage",
            "yagni",
        ],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Right-sized consumer audio streaming platform intentionally capped at 100,000 registered users with cost efficiency and operational simplicity.",
                "target_users": "100,000 registered listeners streaming playlists and search results across mobile and web.",
            },
            "scale_estimates": {
                "registered_users": "100,000 registered users (~30,000 DAU)",
                "concurrent_streams": "~3,000-5,000 concurrent audio streams at evening peak",
                "qps": "~500 QPS peak metadata/search reads; < 20 QPS playlist/like writes (99:1 read-heavy)",
                "catalog_storage": "500,000 tracks (~5 MB average = ~2.5 TB base; ~10 TB across bitrates)",
            },
            "functional_requirements": [
                "Stream audio tracks with chunked HTTP range requests / adaptive bitrate",
                "Browse catalog and search songs, artists, and albums",
                "Create and manage user playlists and liked tracks",
                "Basic play count and listening history tracking",
            ],
            "non_functional_requirements": [
                "Playback start time < 300ms; search/browse < 150ms",
                "99.9% availability (~8.7 hours/year downtime acceptable); single primary region + edge CDN",
                "Operational simplicity and low egress cost via Object Storage + CDN",
            ],
            "constraints": [
                "Lean growth-stage team: avoid multi-region active-active or unnecessary distributed brokers",
                "Single continent deployment with edge CDN caching for audio chunks",
            ],
            "priorities": [
                "P0: Smooth CDN-backed playback (<300ms start) and simple catalog/playlist APIs",
                "P1: Right-sized single-region architecture without over-engineering",
            ],
            "out_of_scope": [
                "Social live listening rooms, podcast recording studio, and real-time ML audio fingerprinting",
            ],
            "hidden_context": {
                "dau": "100,000 registered users; ~30,000 DAU; ~3,000-5,000 concurrent audio streams at evening peak",
                "read_write_ratio": "99:1 read-heavy; audio metadata/search ~500 QPS peak; playlists/likes writes < 20 QPS",
                "catalog_size": "500,000 audio tracks (~5 MB average Ogg/AAC encoded per track = ~2.5 TB audio catalog; ~10 TB with bitrates)",
                "latency_sla": "Playback start time < 300ms; search/browse < 150ms",
                "availability_target": "99.9% availability (~8.7 hours/year downtime acceptable); single primary cloud region sufficient",
                "geographic_distribution": "Single continent (e.g., Europe or North America) with edge CDN caching for audio chunks",
                "budget_constraint": "Lean growth-stage team; operational simplicity and cost efficiency are explicitly prioritized",
            },
            "expected_functional_requirements": [
                "Stream audio tracks with adaptive bitrate / chunked HTTP range requests",
                "Browse catalog and search songs/artists/albums",
                "Create and manage user playlists and liked tracks",
                "Offline download / sync support (optional or scoped)",
                "Play count / basic listening history tracking",
            ],
            "expected_non_functional_requirements": [
                "Smooth stutter-free playback (< 300ms time-to-first-byte via CDN)",
                "Cost-effective storage and egress using object storage + CDN",
                "Operational simplicity appropriate for 100k users (avoid unnecessary distributed systems)",
            ],
            "expected_components": [
                "Mobile Client (Audio player + chunk buffer)",
                "CDN / Edge Cache (Signed audio segment delivery)",
                "Object / Blob Storage (Transcoded AAC/HLS masters)",
                "Load Balancer",
                "Stateless App Service (Catalog, Playlists & Signed URLs)",
                "Primary Relational DB (PostgreSQL + pg_trgm search)",
                "Distributed Cache (Redis session & hot playlists)",
                "Task Queue (Async track ingestion)",
                "Background Worker Pool (Play-count batching)",
            ],
            "expected_paths": [
                {
                    "id": "audio_playback_path",
                    "title": "Adaptive Audio Streaming Path (<300ms TTFB)",
                    "steps": [
                        _step(
                            "mobile_client",
                            "load_balancer",
                            "Request signed stream manifest",
                            "Client fetches track manifest & CDN signed cookies.",
                        ),
                        _step(
                            "load_balancer",
                            "app_service",
                            "Validate entitlement",
                            "Generate short-lived signed CDN URLs in backend.",
                        ),
                        _step(
                            "app_service",
                            "distributed_cache",
                            "Check hot playlist/metadata",
                            "Serve playlist metadata fast from Redis.",
                        ),
                        _step(
                            "mobile_client",
                            "cdn",
                            "GET signed HTTP Range chunks",
                            "Stream audio bytes directly from CDN POPs (never proxy through API pods).",
                        ),
                        _step(
                            "cdn",
                            "object_storage",
                            "Origin cache miss fill",
                            "Fetch cold track segments from S3/GCS.",
                        ),
                    ],
                },
                {
                    "id": "catalog_search_and_plays",
                    "title": "Catalog Browse / Search & Play History",
                    "steps": [
                        _step(
                            "app_service",
                            "relational_db",
                            "Search 500k tracks (pg_trgm) & manage playlists",
                            "Postgres trigram/GIN indexes handle 500k tracks cleanly without extra clusters.",
                        ),
                        _step(
                            "app_service",
                            "message_queue",
                            "Enqueue play event",
                            "Keep playback tracking non-blocking.",
                            "async",
                        ),
                        _step(
                            "message_queue",
                            "async_worker",
                            "Batch listening history",
                            "Flush aggregated plays off-path.",
                            "async",
                        ),
                        _step(
                            "async_worker",
                            "relational_db",
                            "Persist play counts",
                            "Avoid synchronous primary lock contention.",
                            "async",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "direct_edge_audio",
                    "Signed Direct-from-CDN Audio Delivery",
                    "Serve audio bytes via CDN + Object Storage with signed URLs/cookies rather than proxying media streams through API pods.",
                    [["cdn", "object_storage"], ["cdn"], ["object_storage"]],
                ),
                _cap(
                    "lean_audio_backend",
                    "Lean Catalog, Search & Entitlement Compute (YAGNI)",
                    "Handle auth, playlists, signed URLs, and 500k-track search with modular compute + relational/full-text DB without over-engineered microservices.",
                    [
                        ["app_service", "relational_db"],
                        ["app_service", "nosql_kv"],
                        ["microservice", "relational_db"],
                    ],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Proxying audio bytes through application API servers instead of pre-signed CDN/Object Storage URLs",
                "Synchronous play-event logging into PostgreSQL row locks for popular tracks",
                "Lack of pre-transcoding audio pipeline upon catalog ingestion",
            ],
            "over_engineering_traps": [
                "Deploying sharded multi-region Cassandra + Kafka + Flink + dedicated Elasticsearch clusters for only 500k tracks and 30k DAU",
                "Microservices split into 12+ services when 1 PostgreSQL + 1 search index/pg_trgm + S3 + CDN easily handles the load",
                "Custom TCP/UDP streaming protocol instead of standard HLS / HTTP Range requests over CDN",
            ],
            "defence_questions": [
                "With 30k DAU and 500k tracks, why did you include (or omit) dedicated distributed message brokers or sharded NoSQL?",
                "How do audio bytes get from storage to the user's phone—do your API servers proxy them?",
                "How would you handle access control so unauthenticated users can't share raw S3 URLs?",
                "What single component would become your bottleneck first if user count jumped 20x from 100k to 2M?",
            ],
            "default_variant_meta": {
                "variant_id": "lean-100k-streaming",
                "title": "Lean 100k On-Demand Streaming",
                "focus_summary": "100k users / 30k DAU, 500k tracks, single region + S3/CDN + Postgres pg_trgm, strict YAGNI",
                "difficulty_hint": "MEDIUM",
            },
            "extra_variants": [
                {
                    "variant_id": "offline-first-commuter-audio",
                    "title": "Offline-First Mobile Commuter Edition",
                    "focus_summary": "100k users on unreliable mobile LTE, encrypted offline track DRM/leases, 3-device quota, delta playlist sync",
                    "difficulty_hint": "MEDIUM",
                    "business_context": {
                        "product_goal": "Audio streaming app optimized for subway/flight commuters downloading encrypted playlists across up to 3 registered mobile devices.",
                        "target_users": "100,000 paying subscribers (40k DAU) downloading tracks on Wi-Fi and syncing listening state offline.",
                    },
                    "scale_estimates": {
                        "registered_users": "100,000 users (~40,000 DAU, max 3 offline devices/user)",
                        "download_qps": "~2,000 offline chunk/bundle downloads/sec during morning commute spikes",
                        "sync_qps": "~300 offline play-event & playlist delta sync writes/sec on reconnect",
                        "catalog_storage": "500,000 tracks (~4 TB encrypted AAC tiers)",
                    },
                    "functional_requirements": [
                        "Issue device-bound DRM decryption keys / offline license leases (30-day renewal)",
                        "Resumable encrypted playlist bundle downloads from CDN",
                        "Bi-directional offline playlist edits and batch play-history reconciliation on reconnect",
                        "Enforce maximum 3 offline-authorized devices per user with remote revocation",
                    ],
                    "non_functional_requirements": [
                        "99.9% availability; offline downloads saturating CDN edge without touching app servers",
                        "Idempotent batch sync reconciliation even with multi-hour offline edits",
                        "Zero unauthorized plaintext audio extraction or >3-device sharing",
                    ],
                    "constraints": [
                        "Lean team: keep core metadata in PostgreSQL with monotonic sync cursors/version vectors",
                        "DRM license renewal must work cleanly when users regain connectivity briefly",
                    ],
                    "priorities": [
                        "P0: Resumable CDN offline downloads + idempotent reconnect sync + 3-device license enforcement",
                        "P1: Simple conflict resolution (LWW/CRDT-lite per playlist item)",
                    ],
                    "out_of_scope": [
                        "P2P local Wi-Fi track sharing between phones",
                    ],
                    "hidden_context": {
                        "dau": "100k registered / 40k DAU; max 3 offline devices/user; batch reconnect syncs",
                        "constraints": "30-day offline license expiry; encrypted chunks served over CDN",
                    },
                    "expected_components": [
                        "Mobile Client (Encrypted offline player)",
                        "CDN / Edge Cache (Resumable encrypted bundles)",
                        "Object / Blob Storage (AES-encrypted AAC tiers)",
                        "API Gateway",
                        "Stateless App Service (DRM Leases & Delta Sync)",
                        "Auth / IAM Service (3-device quota & revocation)",
                        "Distributed Cache (Redis active license leases)",
                        "Primary Relational DB (Device registry & versioned playlists)",
                    ],
                    "expected_paths": [
                        {
                            "id": "offline_download_path",
                            "title": "Offline Bundle & DRM Lease Path",
                            "steps": [
                                _step(
                                    "mobile_client",
                                    "api_gateway",
                                    "Request offline lease",
                                    "Register device within max 3-device quota.",
                                ),
                                _step(
                                    "api_gateway",
                                    "auth_service",
                                    "Verify device entitlement",
                                    "Reject revoked or 4th offline devices cleanly.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Mint 30-day license key",
                                    "Issue scoped decryption key & resumable signed CDN links.",
                                ),
                                _step(
                                    "app_service",
                                    "distributed_cache",
                                    "Cache lease & rate state",
                                    "Store active lease revocation lists in Redis.",
                                ),
                                _step(
                                    "mobile_client",
                                    "cdn",
                                    "Download encrypted segments (HTTP Range)",
                                    "Resume offline downloads reliably on commuter cellular links.",
                                ),
                                _step(
                                    "cdn",
                                    "object_storage",
                                    "Fetch encrypted audio chunks",
                                    "Serve pre-encrypted AAC bundles without runtime API encryption.",
                                ),
                            ],
                        },
                        {
                            "id": "reconnect_sync_path",
                            "title": "Idempotent Reconnect Sync Path",
                            "steps": [
                                _step(
                                    "mobile_client",
                                    "app_service",
                                    "Push delta ops + play batch",
                                    "Send monotonic sync cursors & idempotency keys upon reconnect.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Reconcile playlist LWW state",
                                    "Apply ordered operations safely without losing offline edits.",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "offline_cdn_drm",
                            "Resumable Encrypted CDN Delivery & Device Quota Auth",
                            "Serve pre-encrypted tracks via CDN/Object Storage while enforcing 3-device DRM leases cleanly in API/Auth.",
                            [["cdn", "object_storage"], ["cdn"], ["object_storage"]],
                        ),
                        _cap(
                            "idempotent_sync",
                            "Idempotent Delta Sync Persistence",
                            "Reconcile offline playlist edits and batch play events cleanly with versioned cursors.",
                            [
                                ["app_service", "relational_db"],
                                ["app_service", "nosql_kv"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Replaying duplicate offline play events or overwriting concurrent mobile+web playlist edits on reconnect",
                        "Encrypting audio files dynamically on backend API servers instead of pre-encrypting at ingestion",
                    ],
                    "over_engineering_traps": [
                        "Deploying distributed Kafka + Flink + Cassandra for 300 reconnect sync writes/sec",
                    ],
                    "defence_questions": [
                        "A user edits the same playlist on a plane on their phone and later on Wi-Fi on their tablet. How do you reconcile without silent data loss?",
                        "If encrypted track bytes are cached on a CDN, how do you stop a revoked 4th device from decrypting previously downloaded files?",
                    ],
                },
                {
                    "variant_id": "lossless-listening-rooms",
                    "title": "Audiophile Lossless & Synced DJ Rooms",
                    "focus_summary": "100k users, heavy FLAC (40MB/track) egress cost control, real-time synchronized listening rooms (<150ms skew)",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "High-fidelity lossless music service for 100k audiophiles featuring live host-controlled listening parties.",
                        "target_users": "100,000 listeners (25k DAU; up to 500 listeners per synchronized DJ room).",
                    },
                    "scale_estimates": {
                        "registered_users": "100,000 users (~25,000 DAU, ~2,000 concurrent rooms/streams)",
                        "bandwidth": "FLAC 24-bit (~1.5 Mbps/stream = ~3 Gbps sustained CDN egress; 40 MB average track)",
                        "sync_events": "~1,500 WebSocket play/pause/seek control broadcasts/sec",
                        "catalog_storage": "500,000 FLAC masters (~20 TB object storage + multi-tier AAC fallbacks)",
                    },
                    "functional_requirements": [
                        "Adaptive FLAC / AAC playback via CDN HTTP range requests",
                        "Host-led live listening rooms with real-time play/pause/seek state synchronization",
                        "Client clock-drift compensation keeping room listeners within < 150ms skew",
                        "Automated bandwidth downgrade when mobile clients experience packet loss",
                    ],
                    "non_functional_requirements": [
                        "Control-plane sync latency < 150ms p95; CDN egress budget strictly minimized via smart tiering",
                        "99.95% availability on room WebSocket state",
                    ],
                    "constraints": [
                        "20 TB FLAC egress is 8x costlier than AAC: avoid cache misses at CDN origin",
                        "Never fan out raw audio bytes through WebSocket control servers",
                    ],
                    "priorities": [
                        "P0: Separate CDN audio byte delivery from lightweight WebSocket room clock-sync control plane",
                        "P1: Egress cost optimization via byte-range prefetching & adaptive downgrade",
                    ],
                    "out_of_scope": [
                        "Creator DAW multitrack live mixing and video concert broadcasting",
                    ],
                    "hidden_context": {
                        "dau": "100k users / 25k DAU; ~3 Gbps CDN FLAC egress; up to 500 users/room",
                        "latency_sla": "Room control sync < 150ms; audio CDN byte-range preload",
                    },
                    "expected_components": [
                        "Web / Browser Client (Audiophile player)",
                        "CDN / Edge Cache (Origin Shield + HTTP Range FLAC)",
                        "Object / Blob Storage (20TB FLAC & AAC fallback masters)",
                        "API Gateway",
                        "Stateless App Service (Catalog, Room control & RTT clock)",
                        "WebSocket / Push Gateway (Room playback state fanout)",
                        "Pub/Sub Fan-out Bus (Redis Streams/PubSub room timestamps)",
                        "Distributed Cache (Redis active room state)",
                        "Primary Relational DB (PostgreSQL catalog & rooms)",
                    ],
                    "expected_paths": [
                        {
                            "id": "flac_delivery_path",
                            "title": "Egress-Optimized FLAC Audio Delivery Path",
                            "steps": [
                                _step(
                                    "web_client",
                                    "cdn",
                                    "HTTP Byte-Range FLAC fetch",
                                    "Prefetch initial segments only so quick skips never pull all 40MB.",
                                ),
                                _step(
                                    "cdn",
                                    "object_storage",
                                    "Origin-shielded master pull",
                                    "Shield S3 FLAC storage behind Origin Shield caching.",
                                ),
                            ],
                        },
                        {
                            "id": "room_sync_control_path",
                            "title": "Synchronized Room Control Plane (<150ms Skew)",
                            "steps": [
                                _step(
                                    "web_client",
                                    "realtime_gateway",
                                    "Host play/pause/seek WS event",
                                    "Keep lightweight JSON timestamps off audio byte delivery.",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "pubsub_bus",
                                    "Broadcast timestamp + RTT offset",
                                    "Fan out control state across gateway pods cleanly.",
                                    "async",
                                ),
                                _step(
                                    "pubsub_bus",
                                    "realtime_gateway",
                                    "Deliver synced state to listeners",
                                    "Align client players within <150ms drift.",
                                    "async",
                                ),
                                _step(
                                    "web_client",
                                    "api_gateway",
                                    "Catalog & persistent room load",
                                    "Manage playlists and room definitions.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Persist room settings",
                                    "Load/update track catalog metadata.",
                                ),
                                _step(
                                    "app_service",
                                    "distributed_cache",
                                    "Cache active room state",
                                    "Keep active room definitions fast in Redis.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Query track & room metadata",
                                    "Store durable catalog & active room definitions.",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "separated_audio_cdn",
                            "Separated Byte Delivery (CDN + Origin Shield / Object Storage)",
                            "Deliver 40MB FLAC files via byte-range HTTP over CDN rather than piping audio through WebSocket pods.",
                            [["cdn", "object_storage"], ["cdn"]],
                        ),
                        _cap(
                            "realtime_room_sync",
                            "Low-Latency Room Control Plane (<150ms)",
                            "Synchronize host play/pause/seek timestamps across up to 500 listeners over WebSockets + Pub/Sub.",
                            [
                                ["realtime_gateway", "pubsub_bus"],
                                ["realtime_gateway", "distributed_cache"],
                                ["realtime_gateway"],
                            ],
                        ),
                        _cap(
                            "catalog_storage",
                            "Catalog & Room Definition Persistence",
                            "Persist tracks and persistent listening rooms via backend API + database.",
                            [
                                ["app_service", "relational_db"],
                                ["app_service", "nosql_kv"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Piping 1.5 Mbps FLAC streams through backend Node/Python WebSocket pods",
                        "Fetching entire 40 MB FLAC files upfront instead of HTTP Range requests when users skip after 5 seconds",
                    ],
                    "over_engineering_traps": [
                        "Building custom WebRTC SFU audio mixing servers for pre-recorded catalog tracks instead of CDN + lightweight WebSocket timestamp sync",
                    ],
                    "defence_questions": [
                        "Why shouldn't the DJ's server stream FLAC audio frames over WebSockets to 500 room participants?",
                        "Half the listeners skip tracks after 10 seconds. How do you avoid paying S3/CDN egress for all 40 MB per skip?",
                    ],
                },
            ],
        },
    },
    {
        "slug": "realtime-notifications",
        "title": "Design a Real-Time Notification System",
        "category": "EVENT_DRIVEN",
        "difficulty": "MEDIUM",
        "prompt_summary": "Design a multi-channel notification platform delivering push, email, SMS, and in-app alerts reliably across millions of events.",
        "initial_prompt": (
            "We need a scalable real-time notification system capable of delivering user alerts across "
            "in-app real-time feeds, mobile push (APNs/FCM), email, and SMS. "
            "Ask clarifying questions to lock down scale, delivery guarantees, and product scope."
        ),
        "tags": ["pub-sub", "websockets", "queues", "idempotency", "fan-out"],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Multi-channel notification delivery platform supporting OTP/security alerts and high-volume product/marketing notifications.",
                "target_users": "Internal producer microservices and 10M DAU end users across push, in-app, email, and SMS.",
            },
            "scale_estimates": {
                "dau": "10M DAU",
                "daily_volume": "~200M notifications/day (60% push, 25% in-app, 12% email, 3% SMS)",
                "qps": "~50,000 notifications/sec peak burst fan-out; ~5,000 reads/sec for in-app inbox",
            },
            "functional_requirements": [
                "Ingest notification events from internal producer services",
                "Enforce user opt-out preferences, quiet hours, and deduplication",
                "Deliver across Push (APNs/FCM), Email, SMS, and In-App WebSockets",
                "Separate priority lanes (critical OTP vs bulk promotional)",
                "In-app notification inbox with read/unread state",
            ],
            "non_functional_requirements": [
                "OTP/security alerts < 2s p99; promotional digests within 60s",
                "99.95% availability; at-least-once delivery with idempotency keys",
                "Priority isolation and circuit breaking against third-party provider outages",
            ],
            "constraints": [
                "External gateways (Twilio/APNs/FCM/SES) have rate limits and intermittent timeouts",
                "Strict per-user rate limits and quiet-hour compliance",
            ],
            "priorities": [
                "P0: Critical OTP/security delivery < 2s p99 unaffected by bulk campaigns",
                "P1: Idempotent at-least-once delivery and DLQ recovery",
            ],
            "out_of_scope": [
                "WYSIWYG marketing campaign drag-and-drop template editor and A/B revenue attribution",
            ],
            "hidden_context": {
                "dau": "10M DAU; ~200M notifications/day across channels (push 60%, in-app 25%, email 12%, SMS 3%)",
                "read_write_ratio": "High burst writes during breaking events (~50k notifications/sec peak fan-out); ~5k in-app unread count reads/sec",
                "latency_sla": "OTP/security alerts < 2 seconds p99; promotional/digest alerts within 60 seconds; strict priority isolation required",
                "availability_target": "99.95% availability; at-least-once delivery with client/channel idempotency",
                "geographic_distribution": "Multi-region Edge WebSocket gateways or regional termination with central preference service",
                "constraints": "User notification preferences (opt-out, quiet hours), per-user rate limiting, third-party provider outages (Twilio/FCM/SES)",
            },
            "expected_functional_requirements": [
                "Ingest notification events from internal producer services",
                "Enforce user opt-out preferences, quiet hours, and deduplication",
                "Route notifications to Push (APNs/FCM), Email, SMS, and In-App WebSockets",
                "Support priority lanes (transactional OTP vs bulk marketing)",
                "Track delivery status and expose in-app notification inbox/read state",
            ],
            "expected_non_functional_requirements": [
                "Priority isolation so bulk campaigns never starve critical security OTPs",
                "At-least-once delivery with idempotency keys to avoid duplicate SMS/emails",
                "Backpressure and circuit breaking against slow third-party gateways",
                "Persistence + DLQ for failed deliveries with exponential backoff",
            ],
            "expected_components": [
                "External System / Webhook (Alert producer services)",
                "Mobile Client (Push & In-App inbox)",
                "API Gateway (Validation & idempotency dedup)",
                "Stateless App Service (Preference routing & priority classifier)",
                "Distributed Cache (Redis user prefs & WS routing map)",
                "Primary Relational DB (Notification inbox & preferences)",
                "Task Queue (Priority-isolated OTP vs Bulk queues)",
                "Background Worker Pool (Channel formatters & retries)",
                "Service Mesh / Circuit Breaker (Third-party gateway protection)",
                "Push / Email / SMS Gateway (APNs / FCM / SMTP / SMS)",
                "WebSocket / Push Gateway (Live in-app alerts)",
                "Pub/Sub Fan-out Bus (Cross-pod socket routing)",
                "Dead-Letter Queue (DLQ) (Failed carrier exhaustion)",
            ],
            "expected_paths": [
                {
                    "id": "priority_dispatch_path",
                    "title": "Priority-Isolated External Delivery Path",
                    "steps": [
                        _step(
                            "webhook_actor",
                            "api_gateway",
                            "POST /notifications",
                            "Ingest alert events with idempotency keys.",
                        ),
                        _step(
                            "api_gateway",
                            "app_service",
                            "Check prefs & classify priority",
                            "Isolate critical 2FA OTPs from bulk campaigns.",
                        ),
                        _step(
                            "app_service",
                            "distributed_cache",
                            "Lookup prefs & dedup key",
                            "Avoid hitting primary DB per notification fan-out.",
                        ),
                        _step(
                            "app_service",
                            "message_queue",
                            "Enqueue to priority lane",
                            "Route OTP vs Promotional lanes to dedicated partitions.",
                            "async",
                        ),
                        _step(
                            "message_queue",
                            "async_worker",
                            "Render template & dispatch",
                            "Process deliveries asynchronously with backoff.",
                            "async",
                        ),
                        _step(
                            "async_worker",
                            "circuit_breaker",
                            "Guard carrier timeouts",
                            "Trip quickly if Twilio/APNs degrades instead of stalling workers.",
                        ),
                        _step(
                            "circuit_breaker",
                            "notification_hub",
                            "Send APNs/FCM/Email/SMS",
                            "Deliver payload with provider idempotency header.",
                        ),
                        _step(
                            "async_worker",
                            "dlq",
                            "Park exhausted retries",
                            "Preserve unrecoverable deliveries for inspection/replay.",
                            "async",
                        ),
                    ],
                },
                {
                    "id": "inapp_realtime_path",
                    "title": "In-App Real-Time Inbox Path",
                    "steps": [
                        _step(
                            "app_service",
                            "relational_db",
                            "Persist inbox notification",
                            "Store durable read/unread notification state.",
                        ),
                        _step(
                            "async_worker",
                            "pubsub_bus",
                            "Publish user-routed alert",
                            "Forward alert to the WS gateway holding user socket.",
                            "async",
                        ),
                        _step(
                            "pubsub_bus",
                            "realtime_gateway",
                            "Route to active socket",
                            "Deliver alert immediately to connected sessions.",
                            "async",
                        ),
                        _step(
                            "realtime_gateway",
                            "mobile_client",
                            "Push live in-app toast",
                            "Display alert immediately without polling.",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "ingest_and_dedup",
                    "Idempotent Ingestion & Priority Classification",
                    "Validate notification events, look up cached user preferences/rate limits, and isolate high-priority OTP lanes from bulk campaigns.",
                    [
                        ["api_gateway", "app_service"],
                        ["app_service"],
                        ["serverless_fn"],
                    ],
                ),
                _cap(
                    "priority_queues_resilience",
                    "Priority Queue Isolation, Carrier Gateway & DLQ",
                    "Buffer deliveries asynchronously across priority lanes with circuit-breaker/retry isolation and dead-letter handling.",
                    [
                        ["message_queue", "async_worker"],
                        ["event_stream", "async_worker"],
                        ["message_queue", "notification_hub"],
                    ],
                ),
                _cap(
                    "inapp_delivery_inbox",
                    "Real-Time In-App Routing & Persistent Inbox",
                    "Route live alerts to active WebSocket/SSE clients and persist inbox history cleanly.",
                    [
                        ["realtime_gateway"],
                        ["pubsub_bus"],
                        ["relational_db"],
                        ["nosql_kv"],
                    ],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Single shared FIFO queue mixing 10M promotional emails with password-reset SMS",
                "Sending duplicate notifications on worker retry because provider calls lack idempotency/dedup checks",
                "Holding WebSocket connection state in a single un-routable gateway instance",
                "Querying main user DB synchronously inside hot fan-out workers without caching preferences",
            ],
            "over_engineering_traps": [
                "Attempting strict distributed exactly-once two-phase commit across external Twilio/APNs APIs (impossible externally; must use at-least-once + dedup)",
            ],
            "defence_questions": [
                "A marketing job queues 5 million emails at 9:00 AM, and at 9:01 AM a user requests a 2FA SMS. How does your design prevent the SMS from being delayed?",
                "Suppose the FCM push gateway times out after processing our request, so our worker retries. How do we avoid spamming the user twice?",
                "How does a backend worker know which WebSocket server holds user #4821's active socket?",
            ],
            "default_variant_meta": {
                "variant_id": "multichannel-saas-alerts",
                "title": "Multi-Channel SaaS Alerts Platform",
                "focus_summary": "10M DAU, 200M/day, push/in-app/email/SMS, strict OTP priority lane isolation (< 2s p99)",
                "difficulty_hint": "MEDIUM",
            },
            "extra_variants": [
                {
                    "variant_id": "fintech-audit-trade-alerts",
                    "title": "Financial Trade & Fraud Execution Alerts",
                    "focus_summary": "2M DAU, strict per-account FIFO ordering, signed delivery audit, < 500ms p99, SMS/Webhook failover",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "Mission-critical brokerage & fraud alert system guaranteeing ordered delivery and regulatory proof of delivery.",
                        "target_users": "2M active retail/institutional traders and compliance auditors.",
                    },
                    "scale_estimates": {
                        "dau": "2M DAU",
                        "daily_volume": "~35M critical alerts/day (~400/s avg, ~8,000/s market-open/close spike)",
                        "latency_sla": "< 500ms p99 end-to-end delivery for fraud/margin-call alerts",
                    },
                    "functional_requirements": [
                        "Strict per-account causal ordering (e.g., Order Placed -> Partially Filled -> Filled)",
                        "Cryptographically signed delivery receipts & 7-year compliance audit log",
                        "Automatic multi-channel escalation fallback (Push -> SMS -> Backup Webhook if ACK missed in 5s)",
                        "Strict zero quiet-hours override rules on critical security/margin events",
                    ],
                    "non_functional_requirements": [
                        "99.99% availability; < 500ms p99 alert latency",
                        "At-least-once with consumer deduplication + out-of-order suppression by sequence_id",
                        "Multi-SMS vendor failover (Twilio primary -> Vonage secondary)",
                    ],
                    "constraints": [
                        "Never drop or reorder alerts for the same account under retry",
                        "Strict PII redaction on third-party mobile push lock-screen payloads",
                    ],
                    "priorities": [
                        "P0: Ordered delivery per account, <500ms latency, and vendor failover",
                        "P1: Immutable audit trail & escalation SLA timers",
                    ],
                    "out_of_scope": [
                        "Promotional newsletter marketing blasts",
                    ],
                    "hidden_context": {
                        "dau": "2M DAU; ~35M alerts/day; ~8,000/s market open peak",
                        "latency_sla": "< 500ms p99; 5s ACK escalation fallback",
                        "consistency": "Per-account partitioned ordering; zero PII on APNs/FCM lock screen",
                    },
                    "expected_components": [
                        "External System / Webhook (Trading engine alerts)",
                        "Mobile Client",
                        "API Gateway",
                        "Stateless App Service (Order & PII redaction)",
                        "Outbox / CDC Pipeline (Atomic DB commit + event publish)",
                        "Event Log / Kafka Stream (Partitioned by account_id)",
                        "Background Worker Pool (Ordered consumers + 5s ACK timer)",
                        "Service Mesh / Circuit Breaker (Multi-SMS carrier failover)",
                        "Push / Email / SMS Gateway (Signed push / Twilio / Vonage)",
                        "Object / Blob Storage (Immutable 7-year WORM audit archive)",
                        "Primary Relational DB (Transactional state + outbox table)",
                    ],
                    "expected_paths": [
                        {
                            "id": "ordered_fintech_path",
                            "title": "Ordered Per-Account Alert & Failover Path (<500ms)",
                            "steps": [
                                _step(
                                    "webhook_actor",
                                    "api_gateway",
                                    "Signed trade/fraud event",
                                    "Receive critical trade fills and fraud triggers.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Commit state + redact PII",
                                    "Commit atomically and strip lock-screen PII.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Transactional outbox insert",
                                    "Guarantee zero event loss on crash.",
                                ),
                                _step(
                                    "relational_db",
                                    "cdc_connector",
                                    "Stream committed outbox",
                                    "Relay committed events reliably off primary transaction.",
                                    "async",
                                ),
                                _step(
                                    "cdc_connector",
                                    "event_stream",
                                    "Publish keyed by account_id",
                                    "Preserve strict causal per-account FIFO ordering.",
                                    "async",
                                ),
                                _step(
                                    "event_stream",
                                    "async_worker",
                                    "Ordered consumer dispatch",
                                    "Enforce sequence_id dedup and 5s ACK escalation.",
                                    "async",
                                ),
                                _step(
                                    "async_worker",
                                    "circuit_breaker",
                                    "Multi-vendor health gate",
                                    "Switch Twilio -> Vonage cleanly on HTTP 503.",
                                ),
                                _step(
                                    "circuit_breaker",
                                    "notification_hub",
                                    "Deliver SMS/Push/Webhook",
                                    "Dispatch with signed payload and delivery receipt.",
                                ),
                                _step(
                                    "notification_hub",
                                    "mobile_client",
                                    "Alert trader device (<500ms)",
                                    "Deliver cryptographically signed execution/fraud alert to client.",
                                ),
                                _step(
                                    "async_worker",
                                    "object_storage",
                                    "Append immutable WORM audit",
                                    "Persist 7-year cryptographically signed compliance log.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "atomic_ordered_ingest",
                            "Atomic Event Capture & Per-Account Causal Ordering",
                            "Guarantee DB+publish atomicity and partition ordering by `account_id` without global ordering bottlenecks.",
                            [
                                ["event_stream"],
                                ["message_queue"],
                                ["cdc_connector", "event_stream"],
                            ],
                        ),
                        _cap(
                            "failover_carrier_audit",
                            "Multi-Carrier Failover, 5s Escalation & 7-Year Audit",
                            "Isolate carrier outages with circuit breakers/failover and append cryptographically verifiable delivery receipts.",
                            [
                                ["notification_hub"],
                                ["circuit_breaker"],
                                ["object_storage"],
                                ["relational_db"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Delivering 'Order Canceled' before 'Order Placed' across parallel unordered queue workers",
                        "Relying on a single SMS vendor during carrier outages",
                    ],
                    "over_engineering_traps": [
                        "Global single-partition ordering across ALL users instead of partitioning by `account_id`",
                    ],
                    "defence_questions": [
                        "How do you guarantee 'Position Liquidated' never arrives after an earlier 'Margin Warning' for the same account?",
                        "If Twilio returns HTTP 503 during a market crash, how does your system failover without duplicating alerts if Twilio actually processed the request?",
                    ],
                },
                {
                    "variant_id": "live-sports-fanout-burst",
                    "title": "Live Sports Goal-Burst WebSocket Fanout",
                    "focus_summary": "40M DAU, 2M concurrent subscribers per match channel, instant thundering-herd fan-out without per-user DB lookups",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "Sports score & breaking-news alert engine delivering match events simultaneously to millions of topic subscribers.",
                        "target_users": "40M DAU sports fans subscribing to teams, leagues, and live matches.",
                    },
                    "scale_estimates": {
                        "dau": "40M DAU; up to 2,000,000 concurrent WebSocket users watching one match",
                        "burst_rate": "50M topic notifications triggered within 3 seconds of a World Cup goal",
                        "in_app_connections": "Up to 5M active concurrent WebSockets across edge gateways",
                    },
                    "functional_requirements": [
                        "Topic-based subscriptions (team_id, match_id, breaking_league)",
                        "Fan-out a single match event to up to 2M subscribed active sockets + push tokens in seconds",
                        "Suppress redundant notifications if user already viewed event in-app",
                        "Regional preference caching for quiet-hour/language localization",
                    ],
                    "non_functional_requirements": [
                        "In-app WebSocket broadcast < 1s p95; mobile push fanout initiated < 5s",
                        "Zero N+1 user-preference SQL queries per goal event",
                        "Edge graceful shedding/jittered reconnect under network blips",
                    ],
                    "constraints": [
                        "Per-event DB lookups across 2M user rows will crash the primary database instantly",
                        "APNs/FCM batch APIs require topic/batch coalescing + token sharding",
                    ],
                    "priorities": [
                        "P0: O(1)/batched topic fan-out architecture for 2M concurrent subscribers",
                        "P1: Connection storm resilience and push gateway rate-limit smoothing",
                    ],
                    "out_of_scope": [
                        "1-on-1 transactional receipts and SMS billing OTPs",
                    ],
                    "hidden_context": {
                        "dau": "40M DAU; 5M concurrent WebSockets; 2M subscribers per single match topic",
                        "burst_rate": "50M fanout deliveries within 3s on breaking goal events",
                    },
                    "expected_components": [
                        "External System / Webhook (Match telemetry feed)",
                        "Mobile Client (5M live sports spectators)",
                        "WebSocket / Push Gateway (Local match_id room maps)",
                        "Event Log / Kafka Stream (Partitioned by match_id)",
                        "Pub/Sub Fan-out Bus (Coalesced topic broadcast)",
                        "Background Worker Pool (Batched pre-sharded push segments)",
                        "Push / Email / SMS Gateway (APNs/FCM batch topics)",
                        "Distributed Cache (Redis subscription shard segments)",
                    ],
                    "expected_paths": [
                        {
                            "id": "goal_burst_fanout_path",
                            "title": "Goal-Burst 2M Subscriber Topic Fan-Out (<1s WS)",
                            "steps": [
                                _step(
                                    "webhook_actor",
                                    "event_stream",
                                    "Match goal trigger",
                                    "Ingest breaking goal event partitioned by match_id.",
                                ),
                                _step(
                                    "event_stream",
                                    "pubsub_bus",
                                    "Topic fanout to edge POPs",
                                    "Avoid expanding 2M per-user SQL queries before edge delivery.",
                                    "async",
                                ),
                                _step(
                                    "pubsub_bus",
                                    "realtime_gateway",
                                    "Local room map broadcast",
                                    "Each gateway pushes locally to subscribed match sockets.",
                                    "async",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "mobile_client",
                                    "Live WebSocket score update",
                                    "Deliver <1s updates with jittered reconnect backoff.",
                                ),
                                _step(
                                    "event_stream",
                                    "async_worker",
                                    "Consume sharded token batch",
                                    "Read pre-materialized push segments without hitting primary DB.",
                                    "async",
                                ),
                                _step(
                                    "async_worker",
                                    "distributed_cache",
                                    "Read sharded token segments",
                                    "Fetch cached push target batches cleanly without DB joins.",
                                ),
                                _step(
                                    "async_worker",
                                    "notification_hub",
                                    "Batched APNs/FCM topic push",
                                    "Send coalesced mobile pushes cleanly under rate limits.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "hierarchical_topic_fanout",
                            "O(1)/Batched Topic Fan-Out (No 2M Row DB Stampede)",
                            "Broadcast one match event to 2M subscribers via gateway room maps + Pub/Sub rather than 2M individual preference SQL queries.",
                            [
                                ["realtime_gateway", "pubsub_bus"],
                                ["realtime_gateway", "event_stream"],
                                ["pubsub_bus"],
                            ],
                        ),
                        _cap(
                            "batch_push_throttling",
                            "Pre-Materialized Batch Mobile Push & Jitter Protection",
                            "Batch push dispatches smoothly across sharded token segments and protect gateways during reconnect storms.",
                            [
                                ["async_worker", "notification_hub"],
                                ["event_stream", "async_worker"],
                                ["distributed_cache"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Expanding a `match_id` event into 2M individual Kafka messages with individual user DB queries before hitting gateways",
                        "Reconnecting 5M mobile WebSockets at exact T=0 after a transient gateway deploy",
                    ],
                    "over_engineering_traps": [
                        "Per-delivery individual SQL `INSERT` tracking for 50M broadcast push events instead of aggregate counters + sampling",
                    ],
                    "defence_questions": [
                        "A goal is scored in a match with 2M subscribed users. Why would querying PostgreSQL for `SELECT user_id FROM subscriptions WHERE match_id = X` and enqueuing 2M individual preference lookups bring down your platform?",
                        "If an edge gateway node holding 200k sockets restarts, how do you prevent a reconnect thundering herd?",
                    ],
                },
            ],
        },
    },
    {
        "slug": "ride-sharing",
        "title": "Design a Ride-Sharing Platform",
        "category": "GEOSPATIAL",
        "difficulty": "HARD",
        "prompt_summary": "Design a real-time rider-driver matching, location tracking, and trip dispatch backend similar to Uber or Lyft.",
        "initial_prompt": (
            "Design the core backend of a ride-sharing platform that tracks driver locations continuously, "
            "matches nearby drivers with riders, and manages trip state transitions. "
            "What questions would you like to ask to define the scope and scale?"
        ),
        "tags": ["geospatial", "geohash", "h3", "matching", "state-machine"],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Real-time rider-driver geospatial matching, GPS location tracking, and trip dispatch state machine.",
                "target_users": "10M riders and 1M peak active drivers globally across metro regions.",
            },
            "scale_estimates": {
                "daily_trips": "5M daily trips",
                "active_fleet": "1M active drivers at peak; 10M riders",
                "write_qps": "~250,000 GPS updates/sec sustained (500,000/sec peak, 4s heartbeat)",
                "matching_qps": "~2,000 ride requests/sec peak globally",
            },
            "functional_requirements": [
                "Ingest continuous driver GPS heartbeats every 4 seconds",
                "Show nearby available drivers to riders",
                "Match ride requests to nearby drivers with offer timeout and fallback",
                "Manage strongly consistent trip lifecycle state transitions",
            ],
            "non_functional_requirements": [
                "Driver location query < 50ms; ride match proposal < 3 seconds",
                "99.99% availability on dispatch and trip transitions",
                "Strong consistency on driver assignment (never double-book a driver)",
            ],
            "constraints": [
                "Workload is partitioned naturally by city/metro region",
                "Location index may be a few seconds stale; trip acceptance must be atomic",
            ],
            "priorities": [
                "P0: Zero double-bookings and <3s dispatch matching under 250k-500k GPS updates/sec",
                "P1: Graceful recovery if a driver disconnects mid-offer",
            ],
            "out_of_scope": [
                "Detailed payments settlement ledger and ML surge-pricing model training",
            ],
            "hidden_context": {
                "dau": "5M daily trips; 1M active drivers at peak globally; 10M riders",
                "location_update_rate": "Drivers emit GPS heartbeat every 4 seconds (~250,000 location updates/sec sustained, 500k peak)",
                "matching_qps": "~2,000 ride requests/sec peak globally",
                "latency_sla": "Driver location query < 50ms; ride match proposal < 3 seconds",
                "availability_target": "99.99% availability on dispatch and active trip state transitions",
                "consistency": "Trip acceptance MUST be strongly consistent (only 1 rider assigned per driver); location index can be seconds-stale",
                "scope_exclusions": "Payments ledger detail and dynamic surge ML modeling can be simplified interfaces unless time permits",
            },
            "expected_functional_requirements": [
                "Ingest real-time driver GPS locations",
                "Display nearby available drivers to riders opening the app",
                "Match a requested ride to optimal nearby available driver(s) with acceptance timeout",
                "Manage trip lifecycle (REQUESTED -> OFFERED -> ACCEPTED -> ARRIVED -> IN_PROGRESS -> COMPLETED)",
            ],
            "expected_non_functional_requirements": [
                "High write throughput (~250k-500k GPS updates/sec) without overwhelming disk-based RDBMS",
                "Geospatial indexing partitioned by city/region (H3/S2/Geohash)",
                "Atomic distributed lock / conditional update so two riders never double-book the same driver",
                "Fault-tolerant dispatch state recovery if a driver drops offline mid-offer",
            ],
            "expected_components": [
                "Mobile Client (Rider & Driver apps)",
                "Load Balancer",
                "API Gateway",
                "WebSocket / Push Gateway (Bidirectional GPS & offers)",
                "Stateless App Service (Location Ingest, Dispatch & Trip State)",
                "Geospatial / Proximity Index (City-sharded Redis Geo / H3)",
                "Primary Relational DB (Strongly consistent Trip DB partitioned by trip_id)",
                "Event Log / Kafka Stream (Trip telemetry & async billing)",
                "Background Worker Pool (ETA archive & receipts)",
            ],
            "expected_paths": [
                {
                    "id": "driver_gps_path",
                    "title": "Driver Location Ingestion Path (250k-500k GPS/s)",
                    "steps": [
                        _step(
                            "mobile_client",
                            "realtime_gateway",
                            "4s GPS ping stream",
                            "Keep persistent driver connections low-overhead.",
                        ),
                        _step(
                            "realtime_gateway",
                            "app_service",
                            "Process driver heartbeat",
                            "Validate coordinates without hammering SQL B-trees.",
                        ),
                        _step(
                            "app_service",
                            "geo_index",
                            "Upsert city-sharded H3 / Redis Geo",
                            "Maintain ephemeral last-known cell index in memory.",
                        ),
                    ],
                },
                {
                    "id": "dispatch_match_path",
                    "title": "Atomic Rider-Driver Dispatch Path (<3s)",
                    "steps": [
                        _step(
                            "mobile_client",
                            "load_balancer",
                            "POST /rides/request",
                            "Accept rider match requests via balanced edge.",
                        ),
                        _step(
                            "load_balancer",
                            "api_gateway",
                            "Route & auth",
                            "Terminate TLS and apply tenant quotas.",
                        ),
                        _step(
                            "api_gateway",
                            "app_service",
                            "Dispatch match workflow",
                            "Run ranked proximity scan and offer lock.",
                        ),
                        _step(
                            "app_service",
                            "geo_index",
                            "Query nearby idle drivers",
                            "Search bounded city cells in sub-milliseconds.",
                        ),
                        _step(
                            "app_service",
                            "relational_db",
                            "Atomic conditional offer & trip lock",
                            "Ensure two dispatchers never double-book one driver.",
                        ),
                        _step(
                            "app_service",
                            "realtime_gateway",
                            "Push offer to driver",
                            "Deliver live accept prompt to winning driver.",
                        ),
                    ],
                },
                {
                    "id": "trip_telemetry_path",
                    "title": "Trip Telemetry & Async Billing Path",
                    "steps": [
                        _step(
                            "app_service",
                            "event_stream",
                            "Publish trip state events",
                            "Emit pickup, dropoff, and route telemetry off hot path.",
                            "async",
                        ),
                        _step(
                            "event_stream",
                            "async_worker",
                            "Compute fare & ETA archive",
                            "Process billing receipts and GPS trip logs asynchronously.",
                            "async",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "gps_ingestion_geo",
                    "High-Frequency GPS Ingestion & City-Sharded Spatial Index",
                    "Ingest 250k+ driver heartbeats/sec into an in-memory Geospatial Index sharded by city rather than hammering B-tree SQL.",
                    [
                        ["realtime_gateway", "geo_index"],
                        ["app_service", "geo_index"],
                        ["geo_index"],
                    ],
                ),
                _cap(
                    "atomic_dispatch",
                    "Atomic Dispatch Matching & Trip State Persistence",
                    "Query nearby drivers, offer/assign atomically without double-booking, and persist durable trip state cleanly.",
                    [
                        ["app_service", "relational_db"],
                        ["app_service", "consensus_store"],
                        ["app_service", "nosql_kv"],
                    ],
                ),
                _cap(
                    "async_trip_events",
                    "Async Trip Event Stream & Billing Decoupling",
                    "Publish trip lifecycle events asynchronously for receipts, analytics, and GPS archival.",
                    [["event_stream"], ["message_queue"]],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Writing 250k GPS updates/second directly into a traditional SQL database with B-tree indexes",
                "Race condition allowing two concurrent dispatch workers to offer/assign the same driver simultaneously",
                "Cross-region latency by storing all global drivers in a single non-partitioned Redis cluster",
                "Not bounding nearby-driver search radius or handling sparse rural areas vs dense Manhattan hotspots",
            ],
            "over_engineering_traps": [
                "Using heavy 2PC across location updates (ephemeral GPS heartbeats only need last-known in-memory state + async archive)",
            ],
            "defence_questions": [
                "Why shouldn't 250,000 driver GPS pings per second go straight into PostgreSQL, and what breaks if Redis crashes?",
                "Two riders press 'Request Ride' 10 milliseconds apart near the only available driver. Walk me through how your system prevents double-booking.",
                "How do you shard your geospatial index so a huge event in New York doesn't degrade matching in London?",
            ],
            "default_variant_meta": {
                "variant_id": "global-on-demand-dispatch",
                "title": "Global Real-Time Rider-Driver Dispatch",
                "focus_summary": "5M trips/day, 1M peak drivers, 250k-500k GPS updates/s, <3s matching, atomic driver lock",
                "difficulty_hint": "HARD",
            },
            "extra_variants": [
                {
                    "variant_id": "scheduled-airport-shuttle-pooling",
                    "title": "Scheduled Airport Shuttle & Pre-Booking Pool",
                    "focus_summary": "500k daily pre-booked trips, time-window route clustering, 30-min advance guaranteed dispatch, no live surge",
                    "difficulty_hint": "MEDIUM",
                    "business_context": {
                        "product_goal": "Advance reservation and shared-shuttle pooling platform guaranteeing airport pickups hours or days ahead.",
                        "target_users": "500k daily scheduled riders and 60k shift-scheduled shuttle drivers across 80 metro airports.",
                    },
                    "scale_estimates": {
                        "daily_trips": "500,000 pre-booked trips/day (~20k active reservations/hour)",
                        "location_update_rate": "60k drivers emitting 10s GPS pings (~6,000 updates/sec)",
                        "optimization_window": "Batch route pooling runs every 60s for pickups in `[now+20m, now+60m]`",
                    },
                    "functional_requirements": [
                        "Book future pickup windows (up to 30 days ahead) with airline flight-delay auto-adjustment",
                        "Cluster nearby passengers sharing destination zones into pooled shuttle routes",
                        "Assign confirmed driver 45 minutes prior with backup standby driver pool for no-shows",
                        "Manage live route ETA updates when airport traffic delays intermediate stops",
                    ],
                    "non_functional_requirements": [
                        "99.99% reservation durability and zero double-scheduled overlapping driver shifts",
                        "Schedule-dispatch lead trigger reliability within 15 seconds of target departure",
                        "Graceful driver no-show reassignment at T-20 min before pickup",
                    ],
                    "constraints": [
                        "Fixed-price upfront quoting (no dynamic real-time surge volatility)",
                        "Drivers follow pre-assigned time-ordered manifests rather than nearest-idle instant pings",
                    ],
                    "priorities": [
                        "P0: Guaranteed on-time advance assignment, non-overlapping driver shift locking, and flight-delay rescheduling",
                        "P1: Geo-temporal route batching efficiency",
                    ],
                    "out_of_scope": [
                        "250k/sec instant street-hail high-frequency heatmap surging",
                    ],
                    "hidden_context": {
                        "dau": "500k daily trips; 60k drivers; 6k GPS updates/sec",
                        "consistency": "Strong temporal interval exclusion on driver schedules",
                    },
                    "expected_components": [
                        "Mobile Client",
                        "External System / Webhook (Airline flight-delay webhooks)",
                        "API Gateway",
                        "Stateless App Service (Reservation & manifest service)",
                        "Primary Relational DB (Schedule DB with driver interval exclusion locks)",
                        "Scheduler / TTL Sweeper (Time-bucketed T-45m dispatch trigger)",
                        "Background Worker Pool (Spatial-temporal pooling optimizer)",
                        "Geospatial / Proximity Index (Modest 6k QPS driver telemetry)",
                        "Push / Email / SMS Gateway (No-show escalation & pickup alerts)",
                    ],
                    "expected_paths": [
                        {
                            "id": "prebook_manifest_path",
                            "title": "Pre-Booking & Flight-Delay Update Path",
                            "steps": [
                                _step(
                                    "mobile_client",
                                    "api_gateway",
                                    "Reserve future pickup window",
                                    "Schedule airport trips up to 30 days ahead.",
                                ),
                                _step(
                                    "webhook_actor",
                                    "api_gateway",
                                    "Airline delay webhook",
                                    "Ingest real-time flight delay schedule shifts.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Validate shift exclusion",
                                    "Enforce non-overlapping driver reservations.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Persist bucketed reservation",
                                    "Store schedule with driver_id exclusion constraints.",
                                ),
                            ],
                        },
                        {
                            "id": "window_pooling_path",
                            "title": "Time-Bucketed Pooling & Reassignment Path",
                            "steps": [
                                _step(
                                    "scheduler",
                                    "relational_db",
                                    "Poll [now+20m, now+60m] partition",
                                    "Scan upcoming time bucket cleanly without scanning 30 days.",
                                    "async",
                                ),
                                _step(
                                    "scheduler",
                                    "async_worker",
                                    "Trigger 60s pooling optimizer",
                                    "Cluster shared corridor passengers into shuttle manifests.",
                                    "async",
                                ),
                                _step(
                                    "async_worker",
                                    "geo_index",
                                    "Check driver live delay ETA",
                                    "Verify driver telemetry for timely pickup.",
                                ),
                                _step(
                                    "async_worker",
                                    "notification_hub",
                                    "Escalate standby driver on no-show",
                                    "Trigger standby reassignment cleanly at T-20m.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "temporal_reservation",
                            "Strong Temporal Reservation Integrity",
                            "Store advance bookings with time-bucketed queries and non-overlapping driver shift exclusion.",
                            [
                                ["app_service", "relational_db"],
                                ["app_service", "consensus_store"],
                            ],
                        ),
                        _cap(
                            "window_optimizer",
                            "Scheduled Time-Bucket Pooling & Flight Re-Optimization",
                            "Run periodic advance dispatch windows + telemetry checks without over-engineering 500k QPS real-time street-hail meshes.",
                            [
                                ["scheduler", "async_worker"],
                                ["scheduler", "geo_index"],
                                ["message_queue", "async_worker"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Using greedy instant-nearest matching instead of time-window optimization (stranding airport shifts)",
                        "Polling all 30-day reservations every second instead of time-bucketed scheduling partitions",
                    ],
                    "over_engineering_traps": [
                        "Designing an extreme 500k GPS/sec custom H3 in-memory sharded mesh when 6k QPS is easily handled cleanly",
                    ],
                    "defence_questions": [
                        "How is matching a 6:00 AM airport reservation fundamentally different from instant on-demand hailing?",
                        "A flight is delayed 90 minutes. How does your scheduler re-optimize the shuttle pool without starving other passengers?",
                    ],
                },
                {
                    "variant_id": "hyperlocal-coldchain-courier",
                    "title": "Hyperlocal Cold-Chain Food & Grocery Dispatch",
                    "focus_summary": "3M orders/day, stacked multi-stop pickup/drop-off routing, kitchen prep-ready sync, <25 min cold-chain SLA",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "Multi-sided marketplace dispatching couriers synchronously with merchant kitchen/packing readiness for hot food & chilled groceries.",
                        "target_users": "8M active shoppers, 400k couriers, and 150k merchants.",
                    },
                    "scale_estimates": {
                        "daily_orders": "3M orders/day (~150 peak dispatches/sec during dinner rush 6pm-8pm)",
                        "location_update_rate": "400k active couriers at dinner peak (~80k GPS updates/sec)",
                        "sla": "Courier arrival at merchant within 2 minutes of food-ready timestamp; total frozen/hot window < 25 minutes",
                    },
                    "functional_requirements": [
                        "Coordinate merchant `prep_ready_eta` with courier travel ETA so food doesn't sit cold or couriers wait idle",
                        "Support stacked batched orders (1 courier picking up 2 adjacent orders cleanly)",
                        "Ingest courier GPS every 5s and support real-time order cancellation/re-dispatch",
                        "Enforce perishability/temperature deadline prioritization",
                    ],
                    "non_functional_requirements": [
                        "Dispatch matching < 2s p99; high write availability during regional meal rushes (12pm & 7pm spikes)",
                        "Atomic order-to-courier batch assignment",
                    ],
                    "constraints": [
                        "Extreme 5x dinner-hour traffic burst in dense metro zones",
                        "Wait-time minimization requires joint courier + merchant state machine",
                    ],
                    "priorities": [
                        "P0: Joint courier-ETA / merchant-prep synchronization and atomic stacked dispatch",
                        "P1: Metro rush-hour load shedding & courier drop-off recovery",
                    ],
                    "out_of_scope": [
                        "Full restaurant POS inventory SKU management",
                    ],
                    "hidden_context": {
                        "dau": "3M orders/day; 400k peak couriers (~80k GPS writes/s); extreme lunch/dinner spikes",
                        "consistency": "Atomic order-batch locking across courier + merchant state",
                    },
                    "expected_components": [
                        "Mobile Client (Shopper & Courier apps)",
                        "External System / Webhook (Merchant kitchen prep tablets)",
                        "API Gateway",
                        "WebSocket / Push Gateway (Courier pings & merchant status)",
                        "Stateless App Service (Prep estimator & stacked batch optimizer)",
                        "Geospatial / Proximity Index (Metro-sharded Redis Geo / H3)",
                        "Primary Relational DB (Atomic stacked order-courier locking)",
                        "Event Log / Kafka Stream (Live tracking & cold-chain SLAs)",
                    ],
                    "expected_paths": [
                        {
                            "id": "prep_sync_dispatch_path",
                            "title": "Prep-Synced Stacked Dispatch Path (<25m Cold Chain)",
                            "steps": [
                                _step(
                                    "webhook_actor",
                                    "api_gateway",
                                    "Merchant prep_ready_eta event",
                                    "Sync kitchen/packing countdown with dispatch timing.",
                                ),
                                _step(
                                    "mobile_client",
                                    "realtime_gateway",
                                    "Courier 5s GPS ping",
                                    "Update courier position smoothly during dinner rush.",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "app_service",
                                    "Sync courier + kitchen ETAs",
                                    "Hold dispatch until courier arrives within 2m of food ready.",
                                ),
                                _step(
                                    "app_service",
                                    "geo_index",
                                    "Query metro couriers & batch pairs",
                                    "Identify 2 adjacent orders cleanly in metro cell.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Atomic stacked batch lock",
                                    "Commit multi-stop assignment without concurrent double-claim.",
                                ),
                                _step(
                                    "app_service",
                                    "event_stream",
                                    "Emit customer ETA events",
                                    "Power live order tracking without blocking dispatch.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "joint_courier_merchant_sync",
                            "Joint Merchant-Prep & Courier Geo Synchronization",
                            "Coordinate merchant prep_ready timelines with metro-sharded courier spatial lookups cleanly.",
                            [
                                ["realtime_gateway", "geo_index"],
                                ["app_service", "geo_index"],
                            ],
                        ),
                        _cap(
                            "atomic_batch_state",
                            "Atomic Multi-Stop Order Batch Locking & Live Tracking",
                            "Lock stacked orders cleanly per metro cell and stream live ETA telemetry off-path.",
                            [
                                ["app_service", "relational_db"],
                                ["app_service", "nosql_kv"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Dispatching courier immediately on order creation so courier waits 20 minutes at the restaurant",
                        "Two dispatchers assigning stacked orders concurrently causing invalid multi-stop routes",
                    ],
                    "over_engineering_traps": [
                        "Solving global multi-city TSP globally instead of partitioned metro-zone 2-stop batching heuristics",
                    ],
                    "defence_questions": [
                        "Why can't you just pick the closest courier the second an order is placed like in passenger rideshare?",
                        "Two merchants are 200m apart and ready 4 minutes apart; how do you safely lock and assign a stacked batch to one courier?",
                    ],
                },
            ],
        },
    },
    {
        "slug": "distributed-job-queue",
        "title": "Design a Distributed Job Processing System",
        "category": "INFRASTRUCTURE",
        "difficulty": "MEDIUM",
        "prompt_summary": "Design a reliable multi-tenant background task execution platform supporting delayed jobs, retries, concurrency limits, and worker heartbeats.",
        "initial_prompt": (
            "Design a distributed job queue and task execution platform (similar to Celery, Temporal queues, or AWS SQS + workers). "
            "Clients submit background jobs and expect reliable execution. "
            "Let's clarify requirements and failure constraints before you design."
        ),
        "tags": ["queues", "visibility-timeout", "dlq", "scheduling", "idempotency"],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Multi-tenant distributed background job execution platform with delayed scheduling, retries, leases, and fair queuing.",
                "target_users": "Internal engineering teams and multi-tenant SaaS workloads submitting async tasks.",
            },
            "scale_estimates": {
                "enqueue_qps": "10,000 jobs/sec average; 50,000 jobs/sec burst",
                "execution_duration": "200ms to 15 minutes per job",
                "scheduling_horizon": "Immediate and delayed jobs up to 30 days ahead",
            },
            "functional_requirements": [
                "Submit immediate, prioritized, and delayed jobs up to 30 days out",
                "Lease jobs to workers with heartbeats / visibility timeout renewal",
                "Retry failed jobs with exponential backoff + jitter and Dead Letter Queue (DLQ)",
                "Query job status, cancel pending jobs, and enforce per-tenant fairness",
            ],
            "non_functional_requirements": [
                "Immediate jobs dispatched within 500ms when workers are available",
                "99.99% enqueue durability (zero silent job loss after ACK)",
                "At-least-once execution with automatic dead-worker lease recovery",
            ],
            "constraints": [
                "Long-running 15-minute jobs must not be prematurely stolen by short fixed timeouts",
                "Noisy-neighbor tenant flooding 1M jobs must not starve other tenants",
            ],
            "priorities": [
                "P0: Durable enqueue, lease-based crash recovery, and tenant isolation",
                "P1: Efficient delayed scheduling and DLQ observability",
            ],
            "out_of_scope": [
                "Distributed DAG workflow UI builder and cron-expression billing",
            ],
            "hidden_context": {
                "throughput": "10,000 jobs enqueued/sec average; 50,000 jobs/sec burst; average job execution duration 200ms to 15 minutes",
                "scheduling": "Immediate jobs plus delayed/scheduled jobs up to 30 days in the future",
                "delivery_guarantee": "At-least-once execution with leases / visibility timeouts; jobs must expose idempotency guidance",
                "multi_tenancy": "Fair scheduling across tenants so one noisy tenant flooding 1M jobs doesn't starve other tenants",
                "latency_sla": "Immediate jobs dispatched within 500ms when workers are available",
                "availability_target": "99.99% enqueue durability (no silent job loss once ACKed to caller)",
            },
            "expected_functional_requirements": [
                "Submit immediate, prioritized, and delayed jobs with payload & metadata",
                "Lease jobs to worker pools with heartbeats / visibility timeout extension",
                "Retry failed jobs with exponential backoff + jitter and move exhausted jobs to a Dead Letter Queue (DLQ)",
                "Query job status and cancel pending jobs",
                "Per-tenant concurrency quotas / fair queuing",
            ],
            "expected_non_functional_requirements": [
                "Zero job loss after enqueue ACK (durable storage / replicated log)",
                "Crash recovery: detect dead workers via lease expiration without human intervention",
                "Noisy-neighbor isolation across tenants",
                "Graceful horizontal scaling of brokers and workers",
            ],
            "expected_components": [
                "External System / Webhook (Tenant job producers)",
                "API Gateway",
                "Rate Limiter (Per-tenant submission quotas)",
                "Stateless App Service (Submission API & Fair-Share Router)",
                "Primary Relational DB (Sharded job state & SKIP LOCKED/metadata)",
                "Scheduler / TTL Sweeper (Delayed timing wheel / future bucket scanner)",
                "Task Queue (Priority & tenant-fair ready partitions)",
                "Background Worker Pool (Lease heartbeats & idempotent execution)",
                "Dead-Letter Queue (DLQ) (Retry exhaustion park)",
                "Metrics, Logs & Tracing (Queue depth & lag SLA alerts)",
            ],
            "expected_paths": [
                {
                    "id": "job_submission_path",
                    "title": "Job Admission & Delayed Scheduling Path",
                    "steps": [
                        _step(
                            "webhook_actor",
                            "api_gateway",
                            "POST /jobs",
                            "Submit immediate or future-scheduled background tasks.",
                        ),
                        _step(
                            "api_gateway",
                            "rate_limiter",
                            "Check tenant quota",
                            "Prevent noisy-neighbor burst enqueue overload.",
                        ),
                        _step(
                            "api_gateway",
                            "app_service",
                            "Validate payload & idempotency",
                            "Enforce payload schema and deduplication key.",
                        ),
                        _step(
                            "app_service",
                            "relational_db",
                            "Persist durable job row",
                            "Ensure zero job loss immediately upon enqueue ACK.",
                        ),
                        _step(
                            "app_service",
                            "message_queue",
                            "Enqueue immediate jobs",
                            "Push ready jobs into fair-share priority queues.",
                            "async",
                        ),
                        _step(
                            "scheduler",
                            "relational_db",
                            "Scan due time bucket",
                            "Move 30-day delayed jobs into ready queues cleanly without full-table scans.",
                            "async",
                        ),
                    ],
                },
                {
                    "id": "worker_lease_dlq_path",
                    "title": "Fair Execution, Lease Heartbeats & DLQ Path",
                    "steps": [
                        _step(
                            "message_queue",
                            "async_worker",
                            "Pull with fair-share lease",
                            "Execute with periodic heartbeats to survive long runs.",
                            "async",
                        ),
                        _step(
                            "async_worker",
                            "relational_db",
                            "Extend lease / mark SUCCEEDED",
                            "Commit completion idempotently.",
                        ),
                        _step(
                            "async_worker",
                            "dlq",
                            "Move exhausted retries",
                            "Park failed tasks safely with exponential jitter.",
                            "async",
                        ),
                        _step(
                            "async_worker",
                            "observability",
                            "Emit lag & duration metrics",
                            "Track per-tenant queue latency SLAs.",
                            "async",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "durable_enqueue_quota",
                    "Admission Rate Limiting & Durable Job Persistence",
                    "Persist jobs durably before ACK while isolating noisy tenants at enqueue time.",
                    [["app_service", "relational_db"], ["app_service", "nosql_kv"]],
                ),
                _cap(
                    "fair_queue_delayed_recovery",
                    "Tenant-Fair Ready Queues, Delayed Trigger & Lease Crash Recovery",
                    "Support delayed triggers, priority isolation, worker heartbeats/leases, and Dead-Letter replay cleanly.",
                    [
                        ["message_queue", "async_worker"],
                        ["event_stream", "async_worker"],
                    ],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Polling `SELECT ... ORDER BY run_at LIMIT 100` across a huge table without `SKIP LOCKED` or partitioned time buckets",
                "Fixed short visibility timeout killing legitimate 10-minute jobs or letting two workers execute the same long job simultaneously",
                "Global FIFO queue causing head-of-line blocking by one tenant",
                "No jitter on retries causing synchronized thundering herds",
            ],
            "over_engineering_traps": [
                "Claiming distributed transactions can magically guarantee single execution of arbitrary external side effects without idempotency keys",
            ],
            "defence_questions": [
                "A worker picks up a 5-minute video encoding job and crashes at minute 2. How does the system recover, and how do we prevent a live 10-minute job from being reassigned too early?",
                "Tenant A dumps 2 million slow jobs into the system at once. How do you ensure Tenant B's fast jobs still run within 500ms?",
                "How do you efficiently trigger millions of jobs scheduled for 7 days in the future without scanning every row every second?",
            ],
            "default_variant_meta": {
                "variant_id": "multitenant-saas-task-queue",
                "title": "Multi-Tenant SaaS Background Job Platform",
                "focus_summary": "10k-50k jobs/s, 200ms-15m duration, lease heartbeats, weighted fair tenant queuing, 30-day delayed jobs",
                "difficulty_hint": "MEDIUM",
            },
            "extra_variants": [
                {
                    "variant_id": "gpu-ml-batch-scheduler",
                    "title": "GPU ML Training & Batch Inference Scheduler",
                    "focus_summary": "200 jobs/s, 1-8h runtime, heterogeneous GPU capability queues, checkpoint preemption, strict concurrency caps",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "Compute cluster scheduler matching ML training & batch inference jobs to heterogeneous GPU pools (A100, H100, T4) with spot preemption resilience.",
                        "target_users": "ML engineers submitting long-running GPU jobs and interactive priority fine-tuning runs.",
                    },
                    "scale_estimates": {
                        "enqueue_qps": "~200 jobs/sec steady; 2,000 batch sweep burst",
                        "execution_duration": "5 minutes to 8 hours per job; multi-node checkpoint sizes 500 MB - 20 GB",
                        "cluster_size": "5,000 GPU workers across 4 hardware capability pools",
                    },
                    "functional_requirements": [
                        "Capability-tag routing (`gpu=h100`, `vram>=80GB`) and strict per-team GPU quota caps",
                        "Spot-instance preemption handling: flush worker progress checkpoint before requeuing",
                        "Priority preemption: allow interactive jobs to pause lower-priority batch sweeps with resume",
                        "Long-lived worker leases with 30s heartbeats & fencing tokens",
                    ],
                    "non_functional_requirements": [
                        "Zero duplicate GPU allocation on split-brain (fencing tokens before saving checkpoints)",
                        "99.95% scheduler control-plane availability",
                        "Minimize wasted GPU idle minutes during failover (< 2 min dead-worker detection)",
                    ],
                    "constraints": [
                        "Re-running an 8-hour job from scratch on spot preemption wastes thousands of dollars: checkpoint resume is mandatory",
                        "Workers differ in VRAM/topology; global undifferentiated queue causes capability starvation",
                    ],
                    "priorities": [
                        "P0: Capability-aware matching, fencing-token state integrity, and checkpointed preemption resume",
                        "P1: Multi-team GPU quota fairness & gang/affinity hints",
                    ],
                    "out_of_scope": [
                        "Low-latency <50ms synchronous RPC serving",
                    ],
                    "hidden_context": {
                        "throughput": "200 jobs/s avg, 5-min to 8-hr GPU tasks; 5,000 workers",
                        "constraints": "Preemptible spot nodes; fencing tokens prevent split-brain overwrite",
                    },
                    "expected_components": [
                        "Web / Browser Client (ML engineers)",
                        "API Gateway",
                        "Rate Limiter (Per-team GPU quota caps)",
                        "Stateless App Service (Scheduler control plane & capability matcher)",
                        "Coordination / Lease Store (Fencing tokens & split-brain guard)",
                        "Primary Relational DB (Job queue metadata & hardware pools)",
                        "Task Queue (Capability-indexed GPU priority queues: H100/A100/T4)",
                        "Background Worker Pool (GPU agents with 30s heartbeats & spot drain)",
                        "Object / Blob Storage (20GB model checkpoint persistence)",
                    ],
                    "expected_paths": [
                        {
                            "id": "gpu_match_fence_path",
                            "title": "Capability-Aware Match & Split-Brain Fencing Path",
                            "steps": [
                                _step(
                                    "web_client",
                                    "api_gateway",
                                    "Submit GPU sweep job",
                                    "Specify capability tags (e.g. gpu=h100, vram>=80GB).",
                                ),
                                _step(
                                    "api_gateway",
                                    "rate_limiter",
                                    "Enforce team GPU quota",
                                    "Prevent team starvation across cluster pools.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Match hardware pool",
                                    "Route into capability-indexed priority queues.",
                                ),
                                _step(
                                    "app_service",
                                    "consensus_store",
                                    "Mint monotonic fencing token",
                                    "Ensure partitioned old workers can never overwrite newer runs.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Commit fenced assignment",
                                    "Record authoritative job lease state.",
                                ),
                                _step(
                                    "app_service",
                                    "message_queue",
                                    "Dispatch to hardware pool",
                                    "Queue job cleanly on matching GPU tier.",
                                    "async",
                                ),
                                _step(
                                    "message_queue",
                                    "async_worker",
                                    "Run training + 30s heartbeats",
                                    "Report live progress & spot interruption drain.",
                                    "async",
                                ),
                                _step(
                                    "async_worker",
                                    "object_storage",
                                    "Save fenced checkpoint",
                                    "Validate fencing token before writing multi-GB checkpoint.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "capability_matching_quotas",
                            "Capability-Indexed Scheduling & Team Quota Governance",
                            "Match jobs to heterogeneous GPU constraints (`H100`, `T4`) with fair team caps rather than one undifferentiated queue.",
                            [
                                ["app_service", "message_queue"],
                                ["app_service", "relational_db"],
                            ],
                        ),
                        _cap(
                            "fenced_spot_recovery",
                            "Fencing Tokens & Checkpointed Spot-Preemption Recovery",
                            "Use monotonic fencing tokens + heartbeats + object storage checkpoints so stale workers never corrupt state.",
                            [
                                ["consensus_store", "object_storage"],
                                ["relational_db", "object_storage"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Fixed visibility timeouts killing 4-hour jobs or keeping dead 80%-cost GPUs unrecovered for hours",
                        "Preempted worker waking up late after network partition and overwriting the new worker's checkpoint",
                    ],
                    "over_engineering_traps": [
                        "Building 50k msg/sec ultra-low-latency Kafka brokers when the bottleneck is stateful GPU matching & checkpoint safety",
                    ],
                    "defence_questions": [
                        "A worker holding a spot GPU loses network connectivity for 3 minutes, the scheduler reassigns the job, and then the old worker comes back and tries to save a checkpoint. How do you stop corruption?",
                        "Why does a single shared ready queue break when jobs specify `H100` vs `T4` constraints?",
                    ],
                },
                {
                    "variant_id": "idempotent-webhook-settlement-runner",
                    "title": "Ordered Financial Webhook & Settlement Runner",
                    "focus_summary": "5k webhooks/s, strict per-merchant FIFO ordering keys, 24h flaky-endpoint backoff, circuit breakers",
                    "difficulty_hint": "MEDIUM",
                    "business_context": {
                        "product_goal": "Payment-gateway outbound webhook and settlement dispatcher delivering ordered financial state notifications to merchant endpoints.",
                        "target_users": "200,000 external merchant servers with wildly varying uptime and latency.",
                    },
                    "scale_estimates": {
                        "enqueue_qps": "~5,000 webhook events/sec average; 20,000/sec flash-sale peak",
                        "retry_horizon": "Exponential backoff with jitter across 24 hours (100M+ dormant retry jobs during major merchant outages)",
                        "latency_sla": "Healthy merchant endpoints receive events within < 1s p95",
                    },
                    "functional_requirements": [
                        "Enforce per-merchant (or per-`entity_id`) sequential ordering when required by merchant config",
                        "Isolate down/slow merchant endpoints via adaptive circuit breakers without stalling healthy merchants",
                        "HMAC-SHA256 payload signing, response inspection, and manual DLQ replay portal",
                        "24-hour multi-stage delayed retries with full jitter",
                    ],
                    "non_functional_requirements": [
                        "99.99% enqueue durability; zero dropped payment settlement webhooks",
                        "Head-of-line isolation across 200,000 destination domains",
                    ],
                    "constraints": [
                        "1 slow merchant taking 30s per TCP timeout can exhaust all worker threads if unisolated",
                        "Merchant downtime creates millions of delayed retry rows simultaneously",
                    ],
                    "priorities": [
                        "P0: Destination circuit-breaker isolation + durable per-entity ordering + 24h retry wheel",
                        "P1: Merchant-facing delivery logs and one-click replay",
                    ],
                    "out_of_scope": [
                        "Long-running CPU compute/transcoding worker autoscaling",
                    ],
                    "hidden_context": {
                        "throughput": "5k/s avg, 20k/s burst across 200k merchant URLs",
                        "constraints": "30s endpoint timeouts threaten worker pools; 24h delayed retry backlog",
                    },
                    "expected_components": [
                        "External System / Webhook (Payment ledger producers & merchant targets)",
                        "API Gateway",
                        "Stateless App Service (Webhook ingestion & HMAC signer)",
                        "Outbox / CDC Pipeline (Atomic settlement ingest)",
                        "Event Log / Kafka Stream (Partitioned by merchant_id)",
                        "Primary Relational DB (24h time-bucketed delayed retry wheel)",
                        "Scheduler / TTL Sweeper (Jittered retry promoter)",
                        "Background Worker Pool (HTTP delivery with per-host semaphore)",
                        "Service Mesh / Circuit Breaker (Down-merchant isolation)",
                        "Dead-Letter Queue (DLQ) (Manual merchant replay portal)",
                    ],
                    "expected_paths": [
                        {
                            "id": "ordered_webhook_path",
                            "title": "Ordered Webhook Dispatch & Host Isolation Path",
                            "steps": [
                                _step(
                                    "webhook_actor",
                                    "api_gateway",
                                    "Payment settlement event",
                                    "Ingest critical webhook payload.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Sign & persist outbox",
                                    "Guarantee atomic ingest + HMAC-SHA256 signature.",
                                ),
                                _step(
                                    "app_service",
                                    "cdc_connector",
                                    "Relay outbox stream",
                                    "Guarantee zero lost webhooks without 2PC.",
                                    "async",
                                ),
                                _step(
                                    "cdc_connector",
                                    "event_stream",
                                    "Partition by merchant_id",
                                    "Preserve per-merchant causal order.",
                                    "async",
                                ),
                                _step(
                                    "event_stream",
                                    "async_worker",
                                    "Deliver via per-host cap",
                                    "Isolate slow 30s merchant timeouts from healthy merchants.",
                                    "async",
                                ),
                                _step(
                                    "async_worker",
                                    "circuit_breaker",
                                    "Isolate degraded domain",
                                    "Trip slow/failing endpoints cleanly into backoff.",
                                ),
                                _step(
                                    "circuit_breaker",
                                    "webhook_actor",
                                    "POST signed merchant webhook",
                                    "Deliver ordered settlement payload (<1s healthy).",
                                ),
                            ],
                        },
                        {
                            "id": "backoff_dlq_path",
                            "title": "24h Jittered Backoff & DLQ Replay Path",
                            "steps": [
                                _step(
                                    "async_worker",
                                    "relational_db",
                                    "Park in retry time bucket",
                                    "Store millions of dormant 24h retries without starving active queues.",
                                    "async",
                                ),
                                _step(
                                    "scheduler",
                                    "event_stream",
                                    "Re-enqueue with full jitter",
                                    "Drain recovered merchants smoothly without a retry storm.",
                                    "async",
                                ),
                                _step(
                                    "async_worker",
                                    "dlq",
                                    "Archive terminal failures",
                                    "Expose merchant replay log portal.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "per_merchant_order",
                            "Durable Ingestion & Logical Key Ordering (by merchant_id)",
                            "Guarantee zero webhook loss and optional per-merchant FIFO ordering without spawning 200k topics.",
                            [
                                ["event_stream", "async_worker"],
                                ["message_queue", "async_worker"],
                            ],
                        ),
                        _cap(
                            "domain_isolation_backoff",
                            "Per-Host Circuit Breaker Isolation & 24h Jittered Retry Drain",
                            "Protect worker pools from 30s merchant hangs and drain backlogs smoothly with jitter + DLQ replay.",
                            [["circuit_breaker"], ["scheduler", "dlq"], ["dlq"]],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "One dead merchant URL filling 100% of worker HTTP connection slots (no per-host concurrency cap)",
                        "Retrying all 50,000 queued events simultaneously the instant a merchant restarts (retry storm)",
                    ],
                    "over_engineering_traps": [
                        "Spinning up 200,000 separate Kafka topics (1 per merchant) instead of logical key-hashing + per-host semaphore",
                    ],
                    "defence_questions": [
                        "Shopify's webhook endpoint starts timing out after 29 seconds for 5 minutes. How do you stop that from delaying Stripe or small-shop webhooks?",
                        "A merchant comes back online with 500k backlogged webhooks—how do you drain safely without DDoSing them?",
                    ],
                },
            ],
        },
    },
    {
        "slug": "video-streaming",
        "title": "Design a Video Streaming Platform",
        "category": "MEDIA_STREAMING",
        "difficulty": "HARD",
        "prompt_summary": "Design a scalable video upload, transcoding DAG pipeline, metadata service, and adaptive bitrate playback architecture like YouTube.",
        "initial_prompt": (
            "Design a video sharing and streaming platform where creators upload videos and viewers "
            "stream them smoothly worldwide on varied network connections. "
            "Ask clarifying questions to narrow down scope, scale, and constraints."
        ),
        "tags": ["hls", "dash", "transcoding", "cdn", "dag-pipeline"],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Global user-generated video upload, parallel transcoding DAG, and adaptive bitrate streaming platform.",
                "target_users": "100M DAU viewers globally and video creators uploading up to 4K 5 GB files.",
            },
            "scale_estimates": {
                "dau": "100M DAU",
                "daily_views": "~500M video views/day (~6,000/sec avg, ~25,000/sec peak)",
                "daily_uploads": "~500,000 uploads/day (~5-10/sec avg; 500 MB avg, up to 5 GB 4K), or ~250 TB/day raw ingress (~91 PB/year) before renditions, replication, or retention",
            },
            "functional_requirements": [
                "Resumable chunked large video uploads directly to object storage",
                "Asynchronous DAG transcoding into multiple HLS/DASH resolutions + thumbnails",
                "Adaptive Bitrate (ABR) playback via global CDN",
                "Video metadata CRUD, search, and eventually consistent view counts",
            ],
            "non_functional_requirements": [
                "Playback start < 500ms; transcoding ready within minutes",
                "99.99% playback availability; 99.9% upload availability",
                "Minimize origin egress via multi-tier CDN caching",
            ],
            "constraints": [
                "Mobile creators experience flaky connections during multi-GB uploads",
                "Viral videos cause extreme hot-key view counter and CDN edge spikes",
            ],
            "priorities": [
                "P0: Fast global ABR playback (<500ms) and reliable resumable uploads",
                "P1: Parallel GOP-chunk transcoding pipeline",
            ],
            "out_of_scope": [
                "ML feed recommendation engine and ultra-low-latency live WebRTC streaming",
            ],
            "hidden_context": {
                "dau": "100M DAU; ~500M video views/day (~6,000 views/sec average, 25k/sec peak)",
                "upload_volume": "~500,000 video uploads/day (~5-10 uploads/sec average); average raw upload 500 MB (up to 4K 5 GB)",
                "raw_ingress_baseline": "~250 TB/day (~91 PB/year) at the stated upload count and average size; retention, rendition expansion, replication, and budget are open requirements to clarify",
                "latency_sla": "Playback start < 500ms; video transcoding ready within minutes (not real-time); resumable uploads",
                "availability_target": "99.99% playback availability; 99.9% upload availability",
                "geographic_distribution": "Global CDN playback; multi-region upload edge acceleration",
                "scope_exclusions": "Recommendation ML models and live low-latency streaming (WebRTC/LL-HLS) are out of scope unless asked",
            },
            "expected_functional_requirements": [
                "Chunked/resumable large video uploads directly to object storage",
                "Asynchronous transcoding pipeline into multiple resolutions & codecs (e.g., 360p/720p/1080p/4K HLS/DASH segments)",
                "Thumbnail generation & manifest creation",
                "Adaptive Bitrate (ABR) streaming via global CDN",
                "Video metadata CRUD, search, and eventually consistent view counters",
            ],
            "expected_non_functional_requirements": [
                "Decouple slow CPU-heavy video transcoding from user-facing APIs",
                "Minimize origin egress costs through CDN edge caching + popular-tier replication",
                "Handle multi-GB uploads reliably on flaky mobile networks",
            ],
            "expected_components": [
                "Web / Browser Client (Creator upload & ABR player)",
                "CDN / Edge Cache (Multi-tier global video delivery)",
                "API Gateway",
                "Stateless App Service (Upload session init & video metadata API)",
                "Object / Blob Storage (Raw multipart bucket & encoded HLS/DASH bucket)",
                "Task Queue (Upload completion DAG orchestrator)",
                "Media / Document Processor (GOP chunk splitter + GPU transcoding workers)",
                "Primary Relational DB (Sharded MySQL/Postgres video metadata)",
                "Full-Text / Geo Search (Video catalog search index)",
                "Distributed Cache (Redis view count buffer & hot metadata)",
            ],
            "expected_paths": [
                {
                    "id": "upload_transcode_dag",
                    "title": "Pre-Signed Resumable Upload & Parallel Transcode DAG",
                    "steps": [
                        _step(
                            "web_client",
                            "api_gateway",
                            "Init multipart upload",
                            "Request pre-signed object storage upload session.",
                        ),
                        _step(
                            "api_gateway",
                            "app_service",
                            "Create metadata row + signed URLs",
                            "Keep multi-GB video streams completely off API pods.",
                        ),
                        _step(
                            "web_client",
                            "object_storage",
                            "Direct multipart chunk upload",
                            "Upload 4K video chunks directly to S3/GCS with resume.",
                        ),
                        _step(
                            "object_storage",
                            "message_queue",
                            "Upload completion event",
                            "Trigger transcode DAG cleanly on upload finish.",
                            "async",
                        ),
                        _step(
                            "message_queue",
                            "media_transcoder",
                            "Split GOPs & encode ABR ladder",
                            "Parallelize 360p-4K HLS/DASH encoding + thumbnails.",
                            "async",
                        ),
                        _step(
                            "media_transcoder",
                            "object_storage",
                            "Write HLS/DASH segments",
                            "Store adaptive bitrate playlists & segments durably.",
                            "async",
                        ),
                        _step(
                            "media_transcoder",
                            "relational_db",
                            "Mark video READY",
                            "Update playback status and index searchable metadata.",
                            "async",
                        ),
                    ],
                },
                {
                    "id": "abr_playback_path",
                    "title": "Adaptive Bitrate Playback & View Counting",
                    "steps": [
                        _step(
                            "web_client",
                            "cdn",
                            "Stream HLS/DASH chunks",
                            "Deliver trending segments from edge POPs cleanly.",
                        ),
                        _step(
                            "cdn",
                            "object_storage",
                            "Origin miss pull",
                            "Serve long-tail segments from encoded object bucket.",
                        ),
                        _step(
                            "app_service",
                            "distributed_cache",
                            "Buffer viral view increments",
                            "Coalesce hot view counts before flushing to metadata DB.",
                        ),
                        _step(
                            "app_service",
                            "search_engine",
                            "Query video search index",
                            "Power fast title/tag discovery queries.",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "direct_upload_object_store",
                    "Pre-Signed Direct-to-Object Upload (No API Proxying)",
                    "Route multi-GB uploads straight from clients to Object Storage via signed URLs instead of choking API servers.",
                    [["app_service", "object_storage"], ["object_storage"]],
                ),
                _cap(
                    "parallel_transcode_dag",
                    "Asynchronous GOP-Chunk Transcoding DAG",
                    "Decouple slow CPU/GPU ABR encoding via queue/DAG workers producing HLS/DASH segments.",
                    [
                        ["message_queue", "media_transcoder"],
                        ["event_stream", "media_transcoder"],
                        ["async_worker", "media_transcoder"],
                    ],
                ),
                _cap(
                    "edge_abr_metadata",
                    "Multi-Tier CDN Playback & Write-Buffered Metadata",
                    "Serve ABR segments over CDN while scaling metadata DB + search + buffered view counts.",
                    [["cdn", "object_storage"], ["relational_db"], ["nosql_kv"]],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Routing multi-GB video uploads through application API pods instead of pre-signed direct-to-object-storage URLs",
                "Transcoding a 2-hour video sequentially on a single worker instead of GOP-splitting chunks in parallel",
                "Database hotspot incrementing `views = views + 1` synchronously on a viral video",
                "Caching long-tail 0-view videos identically to trending viral videos at expensive CDN edge POPs",
            ],
            "over_engineering_traps": [
                "Building custom P2P torrent delivery or custom transport protocol when HTTP/3 + HLS/DASH over CDN is industry standard",
            ],
            "defence_questions": [
                "Why do we split uploaded videos into GOP segments before transcoding rather than processing the whole MP4 file on one machine?",
                "How does Adaptive Bitrate (ABR) work without backend servers continuously rewriting streams per user?",
                "If a creator's Wi-Fi drops at 82% of a 4 GB upload, how does your architecture resume without restarting from 0?",
            ],
            "default_variant_meta": {
                "variant_id": "global-ugc-vod",
                "title": "Global User-Generated VOD Platform",
                "focus_summary": "100M DAU, 500M views/day, 500k 4K uploads/day, parallel GOP-chunk transcoding DAG + global ABR CDN",
                "difficulty_hint": "HARD",
            },
            "extra_variants": [
                {
                    "variant_id": "enterprise-compliance-lms",
                    "title": "Enterprise Corporate Training & DRM LMS",
                    "focus_summary": "200k employees, strict SSO/DRM signed HLS segments, watch-time completion checkpoints, single/dual region YAGNI",
                    "difficulty_hint": "MEDIUM",
                    "business_context": {
                        "product_goal": "Secure internal corporate video learning platform hosting confidential executive townhalls and mandatory compliance training.",
                        "target_users": "200,000 authenticated corporate employees (40k DAU during quarterly compliance windows).",
                    },
                    "scale_estimates": {
                        "dau": "200k employees; 40k DAU (peaks to 80k concurrent streams during annual CEO townhall)",
                        "daily_uploads": "~500 admin-uploaded training/meeting videos/day (1080p, ~800 MB avg)",
                        "watch_telemetry": "~5,000 watch-progress heartbeat writes/sec (10s checkpoint intervals)",
                    },
                    "functional_requirements": [
                        "OIDC/SSO access-controlled playback using encrypted HLS/AES-128 + short-lived CDN signed cookies",
                        "Exact watch-time completion checkpoints & quiz-gate audit tracking for regulatory compliance",
                        "Office-local HTTP caching proxy awareness + ABR transcoding (360p/720p/1080p)",
                        "Instant takedown / access revocation propagation",
                    ],
                    "non_functional_requirements": [
                        "Playback start < 500ms; 99.95% availability; zero unauthenticated video segment leakage",
                        "Accurate completion ledger (no lost watch-progress heartbeats)",
                    ],
                    "constraints": [
                        "Corporate videos are strictly confidential: raw MP4/HLS segments must NOT be publicly URL-guessable",
                        "Lean enterprise infra: PostgreSQL + managed transcode queue + S3/CDN suffices without hyperscale shards",
                    ],
                    "priorities": [
                        "P0: Signed CDN playback security + accurate watch-progress compliance persistence",
                        "P1: Smooth 80k-user townhall VOD/replay peak without saturating office WAN links",
                    ],
                    "out_of_scope": [
                        "Public viral recommendation feeds and ad-insertion auctions",
                    ],
                    "hidden_context": {
                        "dau": "200k employees / 40k DAU; 500 uploads/day; 5k watch heartbeats/sec",
                        "security": "Short-lived signed cookies + DRM/HLS key rotation on revocation",
                    },
                    "expected_components": [
                        "Web / Browser Client",
                        "CDN / Edge Cache (Private CDN + Signed Cookies)",
                        "Auth / IAM Service (SSO Gateway & HLS DRM Key Rotation)",
                        "Stateless App Service (Playback auth & compliance API)",
                        "Object / Blob Storage (Encrypted HLS training segments)",
                        "Task Queue (Admin batch upload queue)",
                        "Media / Document Processor (Encrypted HLS + VTT captions)",
                        "Distributed Cache (Redis watch-progress coalescing buffer)",
                        "Primary Relational DB (Compliance watch-completion records)",
                    ],
                    "expected_paths": [
                        {
                            "id": "private_hls_playback",
                            "title": "SSO-Gated Signed Cookie Playback & Key Rotation",
                            "steps": [
                                _step(
                                    "web_client",
                                    "auth_service",
                                    "SSO login + Signed Cookie",
                                    "Validate corporate employee session and issue short-lived keys.",
                                ),
                                _step(
                                    "web_client",
                                    "cdn",
                                    "GET encrypted HLS + Signed Cookie",
                                    "Serve segments privately via ECDN/Edge without public sharing.",
                                ),
                                _step(
                                    "cdn",
                                    "object_storage",
                                    "Fetch encrypted HLS chunks",
                                    "Serve encrypted chunks safely.",
                                ),
                                _step(
                                    "web_client",
                                    "app_service",
                                    "GET per-segment decryption key",
                                    "Enforce live employee access checks on key server.",
                                ),
                            ],
                        },
                        {
                            "id": "watch_heartbeat_path",
                            "title": "Watch-Progress Coalescing Path (5k/sec -> DB)",
                            "steps": [
                                _step(
                                    "app_service",
                                    "distributed_cache",
                                    "Buffer 5s progress heartbeats",
                                    "Coalesce 5,000/s updates in Redis before flushing to SQL.",
                                ),
                                _step(
                                    "app_service",
                                    "relational_db",
                                    "Flush milestone compliance records",
                                    "Persist auditable course completion cleanly without primary contention.",
                                ),
                                _step(
                                    "message_queue",
                                    "media_transcoder",
                                    "Batch encode encrypted HLS + VTT",
                                    "Process 500 daily admin uploads cleanly.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "revokable_private_drm",
                            "SSO Auth, Signed Cookies & Revocable HLS Key Access",
                            "Prevent terminated employees from watching cached CDN segments using short-lived cookies and DRM/key verification.",
                            [
                                ["auth_service", "cdn"],
                                ["auth_service", "app_service"],
                                ["cdn", "object_storage"],
                            ],
                        ),
                        _cap(
                            "coalesced_compliance_progress",
                            "Write-Coalesced Progress Tracking & Lean Admin Transcoding",
                            "Buffer high-frequency 5s watch heartbeats before flushing compliance records to SQL.",
                            [
                                ["distributed_cache", "relational_db"],
                                ["app_service", "relational_db"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "80,000 employees hammering primary PostgreSQL with synchronous `UPDATE progress` every 5 seconds",
                        "Issuing static public CDN URLs allowing terminated employees to download videos",
                    ],
                    "over_engineering_traps": [
                        "Deploying 4K planetary Cassandra + Kafka clusters for 500 daily admin uploads",
                    ],
                    "defence_questions": [
                        "If HLS `.ts` segments are cached on CloudFront for 24 hours, how do you stop a revoked user from watching?",
                        "How do you record 5,000 watch-progress checkpoints/sec accurately without melting PostgreSQL?",
                    ],
                },
                {
                    "variant_id": "live-low-latency-broadcast",
                    "title": "Live Sports Low-Latency Broadcast + Instant DVR",
                    "focus_summary": "<3s glass-to-glass latency (LL-HLS/CMAF), 10M concurrent viewers joining in 60s, live-to-VOD instant replay",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "Live championship sports streaming platform delivering <3s latency broadcasts to millions while supporting DVR scrub-back.",
                        "target_users": "Live event broadcasters and 10M peak concurrent global spectators.",
                    },
                    "scale_estimates": {
                        "concurrent_viewers": "10,000,000 peak concurrent live viewers (5M joining within 60 seconds pre-kickoff)",
                        "ingest_streams": "500 concurrent live RTMP/SRT broadcast ingest feeds (real-time transcoding required)",
                        "latency_sla": "< 3 seconds glass-to-glass latency (LL-HLS / CMAF chunked encoding)",
                    },
                    "functional_requirements": [
                        "Ingest live broadcast RTMP/SRT feeds with redundant primary+backup ingest POPs",
                        "Real-time GPU ladder transcoding (360p..4K) outputting 200ms CMAF partial chunks immediately",
                        "Multi-tier Origin Shield + CDN delivery supporting live-edge playback AND DVR rewind",
                        "Seamless Live-to-VOD transition the moment the match ends without re-encoding",
                    ],
                    "non_functional_requirements": [
                        "99.99% live stream continuity; automatic failover within 2 seconds on encoder drop",
                        "< 3s end-to-end latency with synchronized segment numbering across ABR bitrates",
                    ],
                    "constraints": [
                        "Pre-match thundering herd: 5M clients request manifests & tokens simultaneously at T-60s",
                        "Origin servers collapse immediately unless shielded behind multi-tier edge collapsing",
                    ],
                    "priorities": [
                        "P0: Real-time chunked transcode pipeline + Origin Shield request coalescing for 10M viewers",
                        "P1: Manifest auth spike absorption and DVR ring-buffer persistence",
                    ],
                    "out_of_scope": [
                        "Creator non-live mobile multipart multi-GB resume flows",
                    ],
                    "hidden_context": {
                        "scale": "10M concurrent viewers; 5M joining in 60s; <3s live latency (LL-HLS)",
                    },
                    "expected_components": [
                        "External System / Webhook (Redundant RTMP/SRT broadcast encoders)",
                        "Web / Browser Client (10M live viewers + instant DVR)",
                        "DNS / GeoDNS (Multi-CDN switching router)",
                        "Media / Document Processor (Real-time synchronized GPU ABR + CMAF)",
                        "CDN / Edge Cache (Multi-tier Origin Shield + Request Collapsing)",
                        "API Gateway (Edge stateless JWT playback validation)",
                        "Object / Blob Storage (Live DVR ring-buffer -> instant VOD)",
                    ],
                    "expected_paths": [
                        {
                            "id": "live_ingest_transcode",
                            "title": "Real-Time Live Broadcast Ingest & DVR Flush (<3s)",
                            "steps": [
                                _step(
                                    "webhook_actor",
                                    "media_transcoder",
                                    "Redundant RTMP/SRT live feed",
                                    "Fail over automatically within 2s on encoder drop.",
                                ),
                                _step(
                                    "media_transcoder",
                                    "object_storage",
                                    "Flush aligned 200ms CMAF chunks",
                                    "Persist aligned keyframes for seamless DVR rewind and instant VOD.",
                                    "async",
                                ),
                            ],
                        },
                        {
                            "id": "origin_shield_delivery",
                            "title": "Thundering-Herd Request-Collapsing Live Delivery (10M)",
                            "steps": [
                                _step(
                                    "web_client",
                                    "dns",
                                    "Multi-CDN traffic steering",
                                    "Distribute 10M kickoff viewers across redundant CDN providers.",
                                ),
                                _step(
                                    "web_client",
                                    "api_gateway",
                                    "Stateless JWT manifest token",
                                    "Validate entitlement at edge without backend DB bottleneck.",
                                ),
                                _step(
                                    "dns",
                                    "cdn",
                                    "Route to edge POPs",
                                    "Serve edge manifest/chunks locally with Origin Shield coalescing.",
                                ),
                                _step(
                                    "cdn",
                                    "object_storage",
                                    "Single collapsed origin pull",
                                    "Collapse millions of identical 500ms playlist polls into one origin fetch.",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "realtime_cmaf_ingest",
                            "Redundant Live Ingest, Keyframe-Aligned ABR & DVR Persistence",
                            "Transcode RTMP/SRT streams in real time with synchronized IDR keyframes and flush immutable chunks for DVR -> VOD.",
                            [
                                ["media_transcoder", "object_storage"],
                                ["media_transcoder"],
                            ],
                        ),
                        _cap(
                            "origin_shield_multicdn",
                            "Multi-CDN Steering, Edge JWT Validation & Origin-Shield Collapsing",
                            "Protect live origin packagers when 5M viewers connect in 60 seconds polling manifests every 500ms.",
                            [["cdn", "object_storage"], ["dns", "cdn"], ["cdn"]],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "10M viewers polling origin every 500ms for uncached dynamic LL-HLS playlists without request coalescing",
                        "Unaligned IDR keyframes across 1080p vs 720p encoders causing ABR player stalls on live switch",
                    ],
                    "over_engineering_traps": [
                        "Trying to maintain 10M stateful peer-to-peer WebRTC mesh connections on origin servers instead of chunked LL-HLS over Multi-CDN",
                    ],
                    "defence_questions": [
                        "At 8:00 PM kickoff, 5 million fans open the stream in 60 seconds and request manifests every 500ms. What protects your packager origin from dying immediately?",
                        "Why MUST keyframes stay strictly synchronized across the 480p and 1080p live transcoders?",
                    ],
                },
            ],
        },
    },
    {
        "slug": "chat-system",
        "title": "Design a Real-Time Chat System",
        "category": "REALTIME_MESSAGING",
        "difficulty": "MEDIUM",
        "prompt_summary": "Design a 1:1 and group messaging application with online presence, message ordering, read receipts, and multi-device sync.",
        "initial_prompt": (
            "Design a real-time chat system like WhatsApp or Slack supporting 1-on-1 conversations, "
            "group chats, online/offline presence indicators, and multi-device message history sync. "
            "What clarifying questions do you have?"
        ),
        "tags": ["websockets", "ordering", "presence", "fan-out", "cassandra"],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Real-time 1:1 and group messaging platform with presence indicators, read receipts, and multi-device sync.",
                "target_users": "50M DAU messaging across up to 5 synced devices per user.",
            },
            "scale_estimates": {
                "dau": "50M DAU",
                "daily_messages": "~20B messages/day (~230k/sec average, ~700k/sec peak; ~200 bytes avg text; ~4 TB/day raw text bodies before metadata, indexes, or replicas)",
                "group_and_devices": "Typical groups 5-50 members (max 500); up to 5 devices/user",
            },
            "functional_requirements": [
                "1:1 and group real-time messaging (up to 500 members)",
                "Persistent message history and multi-device catch-up sync",
                "Offline message queueing and push notification fallback",
                "Per-conversation message ordering, delivery/read receipts, and online presence",
            ],
            "non_functional_requirements": [
                "Online message delivery < 150ms p99",
                "99.99% availability with per-conversation monotonic/causal ordering",
                "Encrypted in transit and durable persistent history",
            ],
            "constraints": [
                "Presence heartbeats can cause thundering-herd fan-out storms unless throttled",
                "Media attachments must stay off the text message payload path",
            ],
            "priorities": [
                "P0: Sub-150ms p99 delivery, strict per-conversation ordering, and multi-device sync",
                "P1: Bandwidth-efficient presence and offline push fallback",
            ],
            "out_of_scope": [
                "End-to-end voice/video calling and enterprise eDiscovery compliance export",
            ],
            "hidden_context": {
                "dau": "50M DAU; ~20B messages/day (~230k messages/sec average, 700k/sec peak; ~4 TB/day raw text bodies before metadata, indexes, or replicas)",
                "group_size": "Typical groups 5-50 members; max group size capped at 500 members",
                "message_size": "Text messages average 200 bytes; media attachments stored via object storage + URL reference",
                "retention_and_storage": "~4 TB/day raw text bodies (~1.46 PB/year) before metadata, indexes, replication, or media; retention and deletion policy are open requirements to clarify",
                "devices_per_user": "Up to 5 synced devices per user (phone, web, desktop)",
                "latency_sla": "Message delivery to online recipient < 150ms p99",
                "availability_target": "99.99% availability; strict per-conversation causal/monotonic ordering; encrypted in transit and stored reliably",
            },
            "expected_functional_requirements": [
                "1:1 and group real-time messaging (up to 500 members)",
                "Persistent message history & multi-device synchronization",
                "Offline message queueing & push notification fallback",
                "Per-conversation message ordering & delivery/read receipts",
                "Online / last-seen presence indicator with privacy/fan-out control",
            ],
            "expected_non_functional_requirements": [
                "Low-latency bidirectional delivery over WebSockets",
                "Write-heavy message storage partitioned by `conversation_id`; preserve ordering within each conversation without requiring a global message sequence",
                "Debounced/throttled presence updates to avoid connection storm cascading failures",
            ],
            "expected_components": [
                "Mobile Client (Phone, web & up to 5 synced devices)",
                "WebSocket / Push Gateway (Stateful bidirectional chat POPs)",
                "Distributed Cache (Redis WS session routing & presence TTL)",
                "Stateless App Service (Message ingest, fan-out & presence debounce)",
                "Unique ID / Key Generator (Monotonic Snowflake/HLC IDs)",
                "NoSQL / Wide-Column / KV DB (Partitioned by channel_id, message_id)",
                "Task Queue (Offline push & sync catch-up buffer)",
                "Push / Email / SMS Gateway (APNs/FCM offline fallback)",
                "Object / Blob Storage (Media attachments off text path)",
                "CDN / Edge Cache (Fast encrypted attachment fetch)",
            ],
            "expected_paths": [
                {
                    "id": "realtime_message_path",
                    "title": "Real-Time Delivery & Causal Ordering Path (<150ms p99)",
                    "steps": [
                        _step(
                            "mobile_client",
                            "realtime_gateway",
                            "WS send_message",
                            "Transmit 200-byte message over persistent WebSocket.",
                        ),
                        _step(
                            "realtime_gateway",
                            "app_service",
                            "Authorize & fan-out",
                            "Validate membership cleanly in stateless chat service.",
                        ),
                        _step(
                            "app_service",
                            "id_generator",
                            "Assign Snowflake / HLC ID",
                            "Guarantee per-conversation deterministic chronological order.",
                        ),
                        _step(
                            "app_service",
                            "nosql_kv",
                            "Persist partitioned by channel_id",
                            "Commit durable history for fast sequential range scans.",
                        ),
                        _step(
                            "app_service",
                            "distributed_cache",
                            "Lookup recipient gateway",
                            "Locate online receiver's active WebSocket host.",
                        ),
                        _step(
                            "app_service",
                            "realtime_gateway",
                            "Deliver message to online peer",
                            "Push directly to active sockets across devices.",
                        ),
                    ],
                },
                {
                    "id": "offline_sync_media_path",
                    "title": "Offline Push Fallback & Out-of-Band Media Path",
                    "steps": [
                        _step(
                            "app_service",
                            "message_queue",
                            "Enqueue offline recipients",
                            "Avoid blocking WS gateways on 500-member mobile pushes.",
                            "async",
                        ),
                        _step(
                            "message_queue",
                            "notification_hub",
                            "Trigger APNs/FCM push",
                            "Alert offline devices while holding catch-up cursor.",
                            "async",
                        ),
                        _step(
                            "mobile_client",
                            "object_storage",
                            "Direct upload media attachment",
                            "Keep heavy blobs off text message Kafka/DB hot path.",
                        ),
                        _step(
                            "mobile_client",
                            "cdn",
                            "Fetch media via URL ref",
                            "Stream attachments fast over edge CDN.",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "ws_routing_presence",
                    "Stateful WebSocket Routing & Throttled Presence",
                    "Maintain persistent sockets mapped via fast session directory while debouncing presence updates to avoid connection storms.",
                    [
                        ["realtime_gateway", "distributed_cache"],
                        ["realtime_gateway", "pubsub_bus"],
                        ["realtime_gateway"],
                    ],
                ),
                _cap(
                    "ordered_chat_persistence",
                    "Server-Assigned Ordering & Channel-Partitioned History",
                    "Order messages consistently per conversation/channel (Snowflake/HLC) in write-optimized partitioned storage + 5-device sync.",
                    [
                        ["id_generator", "nosql_kv"],
                        ["app_service", "nosql_kv"],
                        ["app_service", "relational_db"],
                    ],
                ),
                _cap(
                    "offline_push_media_split",
                    "Async Offline Push Fallback & Out-of-Band Media",
                    "Decouple offline APNs/FCM pushes asynchronously and serve large media outside the chat payload stream.",
                    [
                        ["message_queue", "notification_hub"],
                        ["event_stream", "notification_hub"],
                        ["object_storage"],
                    ],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Storing all user presence updates with synchronous fan-out bursts when 10M users reconnect after an ISP blip (thundering herd)",
                "Using random UUIDs or unsynchronized client timestamps for message ordering instead of server-assigned Snowflake/sequence IDs",
                "Indexing or partitioning messages by `sender_id` instead of `channel_id`",
                "Blocking WebSocket gateway threads waiting synchronously for 500 group members' push receipts",
            ],
            "over_engineering_traps": [
                "Trying to enforce global linearizable ordering across unrelated conversations worldwide instead of per-conversation ordering",
            ],
            "defence_questions": [
                "How do you assign message IDs so two users replying at the same millisecond see the exact same order across web and mobile?",
                "How do you prevent presence heartbeats ('User is online') from consuming 10x more bandwidth than actual chat messages?",
                "How does multi-device sync catch up reliably when a laptop wakes up after being offline for 3 days?",
            ],
            "default_variant_meta": {
                "variant_id": "consumer-e2e-messaging",
                "title": "Consumer Multi-Device Messaging (WhatsApp-Style)",
                "focus_summary": "50M DAU, 20B msgs/day, max 500/group, up to 5 synced devices, per-conversation Snowflake ordering",
                "difficulty_hint": "MEDIUM",
            },
            "extra_variants": [
                {
                    "variant_id": "enterprise-workspace-channels",
                    "title": "Enterprise Workspace Channels (Slack-Style)",
                    "focus_summary": "5M DAU workspaces, up to 10k-member channels, threaded replies, full-text search, compliance retention, SSO",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "Multi-tenant corporate team collaboration platform with public/private channels, threads, search, and legal-hold retention.",
                        "target_users": "5M daily active corporate knowledge workers across 50,000 tenant organizations.",
                    },
                    "scale_estimates": {
                        "dau": "5M DAU across 50,000 enterprise workspaces",
                        "channel_size": "Typical 20-200 members; all-hands `#announcements` channels up to 25,000 members",
                        "message_rate": "~1.5B messages/day (~20k avg / 80k peak msgs/sec); heavy read/search queries (~30k search QPS)",
                    },
                    "functional_requirements": [
                        "Workspace multi-tenant isolation, threaded conversations, and channel membership ACLs",
                        "Full-text message + file metadata search scoped cleanly by `workspace_id` + accessible channels",
                        "Fan-out to 25,000-member channels without blowing up WebSockets or presence storms",
                        "Enterprise eDiscovery export, edits/deletions audit log, and unread-badge tracking per channel",
                    ],
                    "non_functional_requirements": [
                        "Live message delivery < 200ms p99; search results < 300ms p95",
                        "99.99% availability; zero cross-tenant search/message leakage",
                    ],
                    "constraints": [
                        "Large `#general` channels (25k users) make naive write-time inbox replication prohibitively expensive",
                        "Client startup downloads metadata for 100+ joined channels simultaneously ('thundering workspace boot')",
                    ],
                    "priorities": [
                        "P0: Multi-tenant search/ACL indexing, thread/unread state scalability, and large-channel fanout",
                        "P1: Boot-time lazy hydration & compliance retention hooks",
                    ],
                    "out_of_scope": [
                        "Client-only opaque E2E encryption that blocks server-side enterprise full-text search",
                    ],
                    "hidden_context": {
                        "dau": "5M DAU; 50k workspaces; up to 25k users/channel; 30k search QPS",
                        "search": "Server-side indexed full-text search required (so E2E opaque payloads are out of scope)",
                    },
                    "expected_components": [
                        "Web / Browser Client (5M workspace users)",
                        "API Gateway (SSO + Lazy workspace boot)",
                        "WebSocket / Push Gateway (Channel-subscription multiplexing)",
                        "Pub/Sub Fan-out Bus (25k-member channel broadcast)",
                        "Stateless App Service (Threads, ACLs & lazy unread cursors)",
                        "NoSQL / Wide-Column / KV DB (Partitioned by workspace_id, channel_id)",
                        "Distributed Cache (Redis read-watermark / unread counters)",
                        "Event Log / Kafka Stream (Async indexing & eDiscovery)",
                        "Full-Text / Geo Search (Tenant-scoped Elasticsearch / OpenSearch)",
                    ],
                    "expected_paths": [
                        {
                            "id": "large_channel_fanout",
                            "title": "Multiplexed Large-Channel Broadcast Path (25k Users)",
                            "steps": [
                                _step(
                                    "web_client",
                                    "api_gateway",
                                    "Workspace boot & SSO",
                                    "Lazy-hydrate workspace metadata via tenant gateway.",
                                ),
                                _step(
                                    "api_gateway",
                                    "app_service",
                                    "Load workspace metadata",
                                    "Fetch joined channels cleanly with tenant ACLs.",
                                ),
                                _step(
                                    "web_client",
                                    "realtime_gateway",
                                    "Post to #announcements",
                                    "Send message over multiplexed channel WS connection.",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "app_service",
                                    "Verify tenant ACL + persist watermark",
                                    "Enforce workspace isolation without 25k inbox row writes.",
                                ),
                                _step(
                                    "app_service",
                                    "nosql_kv",
                                    "Write channel message",
                                    "Store partitioned by (workspace_id, channel_id, message_id).",
                                ),
                                _step(
                                    "app_service",
                                    "distributed_cache",
                                    "Compare lazy read cursors",
                                    "Compute unread badges cleanly across 200 channels.",
                                ),
                                _step(
                                    "app_service",
                                    "pubsub_bus",
                                    "Publish once per channel",
                                    "Avoid write-amplifying 25k user inbox rows.",
                                    "async",
                                ),
                                _step(
                                    "pubsub_bus",
                                    "realtime_gateway",
                                    "Fan out to subscribed POPs",
                                    "Push live message to active channel viewers.",
                                    "async",
                                ),
                            ],
                        },
                        {
                            "id": "tenant_search_path",
                            "title": "Workspace-Scoped Async Search Indexing (<300ms)",
                            "steps": [
                                _step(
                                    "app_service",
                                    "event_stream",
                                    "Stream indexable message + ACL",
                                    "Keep post latency low while feeding search off-path.",
                                    "async",
                                ),
                                _step(
                                    "event_stream",
                                    "search_engine",
                                    "Index partitioned by workspace_id",
                                    "Serve fast ACL-filtered search queries cleanly.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "channel_multiplex_fanout",
                            "Channel-Multiplexed Fan-Out & Lazy Unread Watermarks",
                            "Broadcast to 25k-member channels and compute 200-channel unread badges without 25k inbox row writes or login COUNT(*) storms.",
                            [
                                ["realtime_gateway", "pubsub_bus"],
                                ["distributed_cache", "nosql_kv"],
                                ["realtime_gateway"],
                            ],
                        ),
                        _cap(
                            "tenant_search_compliance",
                            "Tenant-Isolated Full-Text Search & Compliance Persistence",
                            "Persist threads partitioned by workspace+channel and index asynchronously for sub-300ms scoped search.",
                            [
                                ["event_stream", "search_engine"],
                                ["search_engine"],
                                ["nosql_kv"],
                                ["relational_db"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Performing write-time inbox fanout into 25,000 user-unread rows for one `#general` announcement",
                        "Fetching full message history for all 150 channels synchronously on Slack web app boot",
                    ],
                    "over_engineering_traps": [
                        "Trying to keep server-blind zero-knowledge encryption while simultaneously requiring sub-300ms server full-text search",
                    ],
                    "defence_questions": [
                        "In consumer WhatsApp, max group size is 500; here `#engineering` has 25,000 members. Why does per-recipient write fanout break down?",
                        "How does your unread badge service stay fast when someone joins 200 channels without running 200 `COUNT(*)` queries on login?",
                    ],
                },
                {
                    "variant_id": "ephemeral-gaming-lobby-chat",
                    "title": "Ephemeral Low-Latency Gaming Match Lobby Chat",
                    "focus_summary": "30M DAU, short-lived match rooms purged on game end, zero cold-disk history, <50ms p99 broadcast + toxicity filter",
                    "difficulty_hint": "MEDIUM",
                    "business_context": {
                        "product_goal": "Ultra-low-latency in-game squad/match chat where rooms exist only for the 15-45 minute match lifecycle.",
                        "target_users": "30M DAU multiplayer gamers communicating during active matches.",
                    },
                    "scale_estimates": {
                        "dau": "30M DAU (~4M concurrent WebSocket players, ~400k active match rooms)",
                        "message_rate": "~1.2M messages/sec peak burst across match rooms; zero cross-match history needed",
                        "latency_sla": "< 50ms regional WebSocket fan-out p99 + real-time toxicity/profanity check < 5ms",
                    },
                    "functional_requirements": [
                        "Create and tear down ephemeral match chat rooms cleanly when matches start/end",
                        "In-line ultra-fast toxicity/profanity filtering & rate-limiting per player",
                        "Temporary rolling memory buffer (last 50 messages for reconnects during the live match)",
                        "Async abuse-report snapshot archival *only* when a player flags a toxic match",
                    ],
                    "non_functional_requirements": [
                        "< 50ms p99 regional fan-out latency; 99.95% regional availability",
                        "In-memory first design (avoid writing 1.2M transient msg/s forever to cold wide-column disk)",
                    ],
                    "constraints": [
                        "Persisting 100% of 1.2M transient 'gg/glhf' messages forever on disk destroys unit economics",
                        "Latency budget < 50ms prohibits cross-region consensus or slow external moderation HTTP calls",
                    ],
                    "priorities": [
                        "P0: Sub-50ms regional memory-first WebSocket routing & automatic room TTL garbage collection",
                        "P1: Snapshot-on-report abuse evidence capture + spam protection",
                    ],
                    "out_of_scope": [
                        "Multi-year searchable message archives and 5-device laptop offline sync",
                    ],
                    "hidden_context": {
                        "dau": "30M DAU / 4M concurrent; 1.2M msgs/s peak; 15-45 min ephemeral room TTL",
                        "latency_sla": "< 50ms p99; <5ms inline toxicity filter",
                    },
                    "expected_components": [
                        "Web / Browser Client (30M DAU players)",
                        "WebSocket / Push Gateway (Region-pinned consistent-hashed rooms)",
                        "URL / Payload Safety Filter (Inline <5ms Aho-Corasick toxicity filter)",
                        "Rate Limiter (Per-player flood token bucket)",
                        "Local / L1 In-Process Cache (Pod-memory last-50 match buffer)",
                        "Distributed Cache (Redis short-lived room TTL fallback)",
                        "Task Queue (On-demand flagged match archive)",
                        "Object / Blob Storage (Snapshot transcripts on abuse reports)",
                    ],
                    "expected_paths": [
                        {
                            "id": "ephemeral_lobby_chat_path",
                            "title": "Sub-50ms In-Memory Room Broadcast Path",
                            "steps": [
                                _step(
                                    "web_client",
                                    "realtime_gateway",
                                    "WS match chat message",
                                    "Consistent-hash player traffic to region-pinned match host.",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "rate_limiter",
                                    "Per-player flood check",
                                    "Drop spam bursts locally in sub-milliseconds.",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "content_filter",
                                    "<5ms local profanity check",
                                    "Screen toxic text inline without slow external LLM HTTP calls.",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "local_cache",
                                    "Append 50-msg ring buffer",
                                    "Support fast match reconnects in RAM without disk writes.",
                                ),
                                _step(
                                    "realtime_gateway",
                                    "distributed_cache",
                                    "Fallback Redis TTL room key",
                                    "Rehydrate ephemeral buffer if pod restarts mid-match.",
                                ),
                            ],
                        },
                        {
                            "id": "abuse_snapshot_path",
                            "title": "On-Demand Abuse Report Archival Path",
                            "steps": [
                                _step(
                                    "realtime_gateway",
                                    "message_queue",
                                    "Enqueue flagged match report",
                                    "Persist transcripts ONLY when players file toxicity reports.",
                                    "async",
                                ),
                                _step(
                                    "message_queue",
                                    "object_storage",
                                    "Flush evidence snapshot to S3",
                                    "Archive reported room evidence without persisting 1.2M msgs/s forever.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "memory_first_room_routing",
                            "Memory-First Ephemeral Routing (<50ms, Zero Unbounded Disk Writes)",
                            "Keep ephemeral match chat in pod memory / TTL Redis via region-pinned sockets rather than hammering persistent DBs at 1.2M msgs/s.",
                            [
                                ["realtime_gateway", "local_cache"],
                                ["realtime_gateway", "distributed_cache"],
                                ["realtime_gateway"],
                            ],
                        ),
                        _cap(
                            "inline_moderation_snapshot",
                            "<5ms Inline Spam/Toxicity Filtering & Report-Triggered Archival",
                            "Screen flood/profanity locally under latency budget and snapshot transcripts only when abuse is flagged.",
                            [
                                ["content_filter"],
                                ["rate_limiter"],
                                ["message_queue", "object_storage"],
                            ],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Forcing 1.2M ephemeral messages/sec through synchronous Cassandra quorums when rooms vanish in 30 minutes",
                        "Calling a slow external LLM moderation API inline inside a <50ms game chat path",
                    ],
                    "over_engineering_traps": [
                        "Designing multi-region active-active persistent Cassandra + Elasticsearch clusters for ephemeral disposable match rooms",
                    ],
                    "defence_questions": [
                        "Why would persisting all 1.2M game-chat messages/sec to multi-region Cassandra be huge waste here, and how do you still support player abuse reports?",
                        "How do you moderate toxic spam inside a strict <50ms latency budget?",
                    ],
                },
            ],
        },
    },
    {
        "slug": "rate-limiter",
        "title": "Design a Distributed API Rate Limiter",
        "category": "INFRASTRUCTURE",
        "difficulty": "MEDIUM",
        "prompt_summary": "Design a low-latency distributed rate limiting layer protecting public APIs from abuse, traffic spikes, and noisy tenants.",
        "initial_prompt": (
            "Design a distributed API rate limiter to protect an enterprise SaaS API gateway from "
            "abuse, accidental client loops, and traffic spikes while adding minimal latency. "
            "What clarifying questions should we resolve first?"
        ),
        "tags": [
            "token-bucket",
            "sliding-window",
            "redis-lua",
            "api-gateway",
            "fail-open",
        ],
        "interviewer_brief": {
            "business_context": {
                "product_goal": "Low-latency distributed API rate-limiting layer protecting enterprise SaaS gateways from abuse and traffic spikes.",
                "target_users": "Enterprise API consumers, public gateway traffic, and platform security/ops teams.",
            },
            "scale_estimates": {
                "peak_qps": "1,000,000 API requests/sec peak across multi-zone clusters",
                "rules_count": "100,000 dynamic rate-limit rules (by user_id, api_key, IP, or route)",
                "latency_budget": "< 2ms p99 added decision overhead",
            },
            "functional_requirements": [
                "Enforce configurable rate-limit rules per user, IP, API key, route, and plan tier",
                "Return HTTP 429 with `X-RateLimit-Remaining` and `Retry-After` headers",
                "Dynamic rule updates without restarting API gateway instances",
            ],
            "non_functional_requirements": [
                "Rate-limit decision overhead < 2ms p99",
                "Atomic check-and-increment counters without read-then-write race conditions",
                "Fail-open for core traffic if central store degrades (fail-closed/local fallback for auth routes)",
            ],
            "constraints": [
                "1-5% counter drift during split-brain is acceptable in exchange for <2ms latency",
                "Cannot perform synchronous DB lookups or cross-region Raft consensus per request",
            ],
            "priorities": [
                "P0: <2ms p99 decision latency, atomic counter updates, and safe failure fallback",
                "P1: Hot-reloadable rules across gateway nodes",
            ],
            "out_of_scope": [
                "Full WAF deep-packet inspection and customer usage-based billing invoicing",
            ],
            "hidden_context": {
                "throughput": "1,000,000 API requests/sec peak across multi-zone clusters",
                "latency_budget": "Rate limit decision overhead must add < 2ms p99 to API request latency",
                "rules_scope": "100,000 dynamic rules per user_id, api_key, IP, or endpoint route",
                "accuracy": "Exact fairness is NOT mandatory globally; ~1-5% drift under split-brain is acceptable in exchange for sub-2ms latency",
                "failure_mode": "Fail-open preferred on rate limiter outage for core traffic (except strict auth/brute-force routes which fail-closed or use local fallback)",
            },
            "expected_functional_requirements": [
                "Enforce configurable rate-limit rules (user, IP, API key, route, tiered plans)",
                "Return standard headers (`X-RateLimit-Remaining`, `Retry-After`) and HTTP 429",
                "Dynamic rule configuration reload without restarting API gateways",
            ],
            "expected_non_functional_requirements": [
                "Sub-2ms p99 decision overhead on every API request",
                "Atomic counter check-and-increment eliminating read-then-write race conditions",
                "Clear fail-open vs local in-memory fallback strategy if central Redis degrades",
            ],
            "expected_components": [
                "Web / Browser Client (Enterprise API consumers)",
                "API Gateway (Envoy / Gateway enforcing HTTP 429 + headers)",
                "Rate Limiter (Middleware executing token bucket / sliding window)",
                "Local / L1 In-Process Cache (Hot rules & fail-open emergency fallback)",
                "Distributed Cache (Redis Cluster sharded with atomic Lua scripts)",
                "Coordination / Lease Store (Hot-reloadable rule control plane)",
                "Stateless App Service (Protected backend APIs)",
            ],
            "expected_paths": [
                {
                    "id": "rate_limit_decision_path",
                    "title": "Sub-2ms Request Admission & Atomic Counter Path",
                    "steps": [
                        _step(
                            "web_client",
                            "api_gateway",
                            "API request + API key",
                            "Hit ingress gateway edge under 1M req/s peak.",
                        ),
                        _step(
                            "api_gateway",
                            "rate_limiter",
                            "Check Token Bucket / Sliding Window",
                            "Enforce per-user/IP/route quota in <2ms.",
                        ),
                        _step(
                            "rate_limiter",
                            "distributed_cache",
                            "EVALSHA atomic Lua counter",
                            "Prevent read-then-write race conditions on sharded Redis Cluster.",
                        ),
                        _step(
                            "rate_limiter",
                            "local_cache",
                            "Emergency local counter fallback",
                            "Fail-open or enforce bounded local limits if Redis spikes >5ms.",
                        ),
                        _step(
                            "api_gateway",
                            "app_service",
                            "Forward admitted request",
                            "Return HTTP 429 + Retry-After on excess; proxy allowed calls cleanly.",
                        ),
                    ],
                },
                {
                    "id": "rule_control_plane_path",
                    "title": "Dynamic Rule Hot-Reload Path (100k Rules)",
                    "steps": [
                        _step(
                            "consensus_store",
                            "local_cache",
                            "Push/stream rule snapshot",
                            "Update gateway rule tables dynamically without restarts.",
                            "async",
                        ),
                    ],
                },
            ],
            "required_capabilities": [
                _cap(
                    "gateway_middleware_decision",
                    "Edge Gateway Decision Tier (<2ms p99 Overhead)",
                    "Evaluate 100k rules inline inside API Gateway/sidecar with HTTP 429 + `Retry-After` responses and hot-reloadable local rules.",
                    [
                        ["api_gateway", "rate_limiter"],
                        ["rate_limiter"],
                        ["api_gateway"],
                    ],
                ),
                _cap(
                    "atomic_sharded_counters",
                    "Race-Free Sharded Counters & Degraded Fail-Open Cushion",
                    "Update distributed counters atomically (e.g., Redis Cluster + Lua token bucket) with bounded local fallback if central cache stalls.",
                    [["distributed_cache", "local_cache"], ["distributed_cache"]],
                ),
            ],
            "common_bottlenecks_and_spofs": [
                "Two separate Redis commands (`GET` then `SET`/`INCR`) creating race conditions under concurrent requests",
                "Storing full timestamp logs for 1M QPS (Sliding Window Log blowing up Redis RAM)",
                "Unsharded single Redis instance saturating NIC or single-thread CPU at 1M ops/s",
                "Synchronous rule DB lookup per request or failing closed globally if Redis restarts",
            ],
            "over_engineering_traps": [
                "Using distributed Raft/Paxos consensus on every single counter increment across regions (violates the <2ms budget completely)",
            ],
            "defence_questions": [
                "Compare Fixed Window Counter, Sliding Window Log, and Token Bucket—which did you choose and why?",
                "How do you avoid the classic race condition where two concurrent requests read counter=9/10 and both get allowed?",
                "If Redis latency spikes from 0.5ms to 50ms, what happens to your entire SaaS API gateway?",
            ],
            "default_variant_meta": {
                "variant_id": "global-saas-api-guard",
                "title": "Global SaaS API Gateway Protection",
                "focus_summary": "1M req/s peak, 100k rules, <2ms p99 overhead, 1-5% drift OK, fail-open on core traffic",
                "difficulty_hint": "MEDIUM",
            },
            "extra_variants": [
                {
                    "variant_id": "strict-banking-auth-guard",
                    "title": "Strict Multi-Region Banking & Transfer Guard",
                    "focus_summary": "50k req/s, zero/minimal drift, fail-closed on auth/transfer routes, strong audit logs, cross-region attacker blocking",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "High-integrity security rate-limiting & brute-force shield protecting bank login, MFA verification, and wire-transfer endpoints.",
                        "target_users": "Retail/commercial banking apps facing credential-stuffing bots distributed across multiple cloud regions.",
                    },
                    "scale_estimates": {
                        "peak_qps": "50,000 security-sensitive auth/transfer reqs/sec across 3 active regions",
                        "rules_scope": "Dynamic IP, device fingerprint, card/account ID, and ASN rules",
                        "latency_budget": "< 15ms p99 budget allowed in exchange for strong global quota enforcement",
                    },
                    "functional_requirements": [
                        "Block credential stuffing globally across regions (attacker rotating across US-East and EU POPs shares one quota)",
                        "Fail-closed (or ultra-tight emergency local circuit cap) if rate-limit store fails on `/login` and `/wire-transfer`",
                        "Audit log every 429 block with triggering rule & actor metadata for SOC fraud investigations",
                        "Exponential progressive lockout penalties on repeated failed MFA attempts",
                    ],
                    "non_functional_requirements": [
                        "99.995% availability; zero silent fail-open exposure on authentication endpoints",
                        "Near-zero cross-region quota drift for account-level lockout rules",
                    ],
                    "constraints": [
                        "Cannot fail open on `/v1/mfa/verify` — that would let attackers brute-force 6-digit OTPs during a Redis blip",
                        "Users logging in genuinely need predictable deterministic lockouts even across edge regions",
                    ],
                    "priorities": [
                        "P0: Fail-closed / tight fallback safety, global consistency per `account_id`, and SOC audit trail",
                        "P1: Progressive lockout penalties without cross-account lock amplification",
                    ],
                    "out_of_scope": [
                        "Soft 1-5% best-effort approximate marketing API throttling",
                    ],
                    "hidden_context": {
                        "throughput": "50k req/s across 3 regions; <15ms p99 budget; strict fail-closed auth",
                    },
                    "expected_components": [
                        "Web / Browser Client (Multi-region banking users)",
                        "WAF / DDoS Shield (Edge credential-stuffing shield)",
                        "API Gateway (Auth-aware ingress)",
                        "Rate Limiter (Conservative in-memory emergency fail-closed cap)",
                        "Coordination / Lease Store (Region-homed / Raft quota partition)",
                        "Pub/Sub Fan-out Bus (Async cross-region blocklist sync)",
                        "Event Log / Kafka Stream (Immutable SOC 429 audit log)",
                        "Object / Blob Storage (Security compliance archive)",
                    ],
                    "expected_paths": [
                        {
                            "id": "strict_auth_guard_path",
                            "title": "Zero-Drift Cross-Region Fail-Closed Auth Shield (<15ms)",
                            "steps": [
                                _step(
                                    "web_client",
                                    "waf_ddos",
                                    "POST /v1/mfa/verify",
                                    "Mitigate distributed IP/botnet floods at edge POPs.",
                                ),
                                _step(
                                    "waf_ddos",
                                    "api_gateway",
                                    "Route to auth-aware gateway",
                                    "Inspect account_id, device fingerprint, and IP.",
                                ),
                                _step(
                                    "api_gateway",
                                    "rate_limiter",
                                    "Enforce strict auth quota",
                                    "Fail closed / tighten emergency local cap on store partition.",
                                ),
                                _step(
                                    "rate_limiter",
                                    "consensus_store",
                                    "Atomic region-homed account check",
                                    "Eliminate 3x multi-region OTP retry drift via home-region routing.",
                                ),
                                _step(
                                    "rate_limiter",
                                    "event_stream",
                                    "Emit SOC block audit log",
                                    "Record rule ID & actor metadata for fraud investigation.",
                                    "async",
                                ),
                                _step(
                                    "event_stream",
                                    "object_storage",
                                    "Retain immutable SOC logs",
                                    "Archive verifiable security block records.",
                                    "async",
                                ),
                                _step(
                                    "rate_limiter",
                                    "pubsub_bus",
                                    "Broadcast high-confidence attackers",
                                    "Replicate banned fingerprints globally.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "failclosed_edge_shield",
                            "Edge WAF & Fail-Closed Auth Protection",
                            "Never silently fail open on login/MFA/wire routes; layer WAF + strict local emergency caps if central quota fails.",
                            [
                                ["waf_ddos", "rate_limiter"],
                                ["api_gateway", "rate_limiter"],
                                ["rate_limiter"],
                            ],
                        ),
                        _cap(
                            "cross_region_account_quota",
                            "Region-Homed Consistent Account Quota & SOC Audit",
                            "Prevent attackers spreading retries across US/EU/APAC POPs and audit-log every 429 security block.",
                            [["consensus_store"], ["nosql_kv"], ["relational_db"]],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Failing open globally when central Redis hiccups, handing attackers unlimited OTP attempts",
                        "Keeping uncoordinated independent per-region counters letting an attacker get N×retries across N regions",
                    ],
                    "over_engineering_traps": [
                        "Running cross-region consensus on coarse CDN static assets instead of scoping strong consistency to account/auth keys",
                    ],
                    "defence_questions": [
                        "An attacker scripts 10,000 bots split evenly across US, EU, and APAC endpoints to brute-force one account's 6-digit PIN. How does your limiter stop `3 × limit` drift?",
                        "Why does failing open completely break requirements here, and what happens to legitimate bank logins if your Redis cluster experiences a network partition?",
                    ],
                },
                {
                    "variant_id": "llm-token-compute-quota",
                    "title": "LLM Token & Streaming Compute Quota Gateway",
                    "focus_summary": "100k req/s, variable post-response token cost (reserve-then-settle), concurrent stream caps, TPM/RPM dual windows",
                    "difficulty_hint": "HARD",
                    "business_context": {
                        "product_goal": "AI inference API gateway enforcing dual Requests-Per-Minute (RPM), Tokens-Per-Minute (TPM), and Max Concurrent Streams per tenant.",
                        "target_users": "SaaS AI platform tenants calling expensive GPU-backed streaming LLM endpoints.",
                    },
                    "scale_estimates": {
                        "peak_qps": "100,000 AI gateway requests/sec; average SSE stream lasts 2-15 seconds",
                        "token_throughput": "Up to 200M input+output tokens/minute across 50,000 tenant API keys",
                        "latency_budget": "< 5ms admission overhead before forwarding to GPU cluster",
                    },
                    "functional_requirements": [
                        "Admit requests against three simultaneous limits: RPM, estimated TPM, and active concurrent SSE streams",
                        "Reserve `max_tokens` (or input + buffer) upfront, then **reconcile/refund** unused tokens after stream completes/disconnects",
                        "Release concurrent-stream semaphore cleanly even if a client disconnects abruptly or gateway crashes (TTL leases)",
                        "Return `Retry-After` + remaining TPM/RPM headers",
                    ],
                    "non_functional_requirements": [
                        "Atomic multi-counter reserve + settle without leaking leaked concurrency slots on client drops",
                        "< 5ms p99 pre-flight check overhead",
                    ],
                    "constraints": [
                        "True output token count is UNKNOWN at request arrival (cannot use simple fixed `+1` counter before calling upstream)",
                        "Leaked concurrent stream slots would permanently lock out paying tenants after network drops",
                    ],
                    "priorities": [
                        "P0: Reserve-then-settle atomic TPM accounting + lease-backed concurrent stream tracking",
                        "P1: Protecting downstream expensive GPUs during retry storms",
                    ],
                    "out_of_scope": [
                        "GPU model weight sharding and training pipelines",
                    ],
                    "hidden_context": {
                        "throughput": "100k req/s; 2-15s SSE streams; 200M tokens/min; unknown output token cost upfront",
                    },
                    "expected_components": [
                        "Web / Browser Client (AI SaaS API callers)",
                        "API Gateway (Streaming AI proxy + prompt tokenizer)",
                        "Rate Limiter (Reserve max_tokens + RPM + stream semaphore)",
                        "Distributed Cache (Redis Cluster atomic reserve/settle Lua)",
                        "Scheduler / TTL Sweeper (Reap leaked SSE stream leases)",
                        "LLM / AI Model Gateway (GPU upstream inference proxy)",
                    ],
                    "expected_paths": [
                        {
                            "id": "reserve_settle_llm_path",
                            "title": "Reserve-Then-Settle LLM Quota & SSE Lease Path (<5ms)",
                            "steps": [
                                _step(
                                    "web_client",
                                    "api_gateway",
                                    "POST /v1/chat/completions (SSE)",
                                    "Tokenize prompt input upfront at streaming proxy.",
                                ),
                                _step(
                                    "api_gateway",
                                    "rate_limiter",
                                    "Admit RPM + est. TPM + active stream",
                                    "Reject excess before hitting expensive GPU clusters.",
                                ),
                                _step(
                                    "rate_limiter",
                                    "distributed_cache",
                                    "Atomic reserve + leased slot Lua",
                                    "Decrement estimated TPM reserve & record TTL-leased stream slot.",
                                ),
                                _step(
                                    "api_gateway",
                                    "llm_gateway",
                                    "Stream GPU tokens (2-15s SSE)",
                                    "Proxy SSE deltas cleanly after admission.",
                                ),
                                _step(
                                    "llm_gateway",
                                    "distributed_cache",
                                    "Post-stream refund & release slot",
                                    "Reconcile actual output tokens once at stream end (zero DB writes per delta).",
                                ),
                                _step(
                                    "scheduler",
                                    "distributed_cache",
                                    "Reap crashed half-open stream leases",
                                    "Guarantee dropped TCP clients never permanently exhaust tenant concurrency.",
                                    "async",
                                ),
                            ],
                        },
                    ],
                    "required_capabilities": [
                        _cap(
                            "pre_flight_token_reserve",
                            "Upfront Reserve-Then-Settle TPM + RPM + Concurrency Admission",
                            "Reserve estimated tokens and leased concurrency upfront before calling GPU inference, then settle unused tokens once post-stream.",
                            [
                                ["api_gateway", "rate_limiter"],
                                ["rate_limiter", "distributed_cache"],
                                ["api_gateway", "llm_gateway"],
                            ],
                        ),
                        _cap(
                            "lease_reaper_safety",
                            "Abrupt-Disconnect Concurrency Lease Reaper",
                            "Auto-expire or sweep abandoned SSE stream semaphores cleanly without touching transactional SQL per streamed token.",
                            [["distributed_cache", "scheduler"], ["distributed_cache"]],
                        ),
                    ],
                    "common_bottlenecks_and_spofs": [
                        "Checking token quota AFTER the 15-second GPU generation completes (allowing bursts to bankrupt GPU capacity)",
                        "Incrementing `active_streams` on open and forgetting client crash / half-open TCP drops leaving stuck slots forever",
                    ],
                    "over_engineering_traps": [
                        "Calling a SQL database transaction synchronously on every streamed SSE token chunk (`delta`) instead of one post-stream settlement",
                    ],
                    "defence_questions": [
                        "Unlike normal REST endpoints where every request costs 1 unit, a prompt can generate 50 or 8,000 tokens. How do you enforce Tokens-Per-Minute *before* forwarding while still keeping counts accurate afterward?",
                        "A client kills their connection mid-stream 500 times—how do you ensure their `max_concurrent_streams` counter doesn't permanently deadlock at full?",
                    ],
                },
            ],
        },
    },
]


_BRIEF_VARIANT_KEYS = (
    "business_context",
    "scale_estimates",
    "functional_requirements",
    "non_functional_requirements",
    "constraints",
    "priorities",
    "out_of_scope",
    "hidden_context",
    "expected_components",
    "expected_paths",
    "required_capabilities",
    "bonus_capabilities",
    "diagram_palette_extensions",
    "common_bottlenecks_and_spofs",
    "over_engineering_traps",
    "defence_questions",
)


def _materialize_challenge_variants() -> None:
    """Normalizes each curated challenge's interviewer_brief to carry a 3-entry variants list."""
    for challenge in CURATED_CHALLENGES:
        brief = challenge.get("interviewer_brief")
        if not isinstance(brief, dict) or "variants" in brief:
            continue
        default_meta = brief.pop("default_variant_meta", None) or {}
        extra_variants = brief.pop("extra_variants", None) or []
        primary_variant = {
            "variant_id": default_meta.get("variant_id", "default"),
            "title": default_meta.get("title", "Standard Scenario"),
            "focus_summary": default_meta.get(
                "focus_summary", challenge.get("description", "")
            ),
        }
        for key in _BRIEF_VARIANT_KEYS:
            if key in brief:
                primary_variant[key] = brief[key]
        brief["variants"] = [primary_variant, *extra_variants]


_materialize_challenge_variants()


def _bonus(
    capability_id: str,
    title: str,
    goal: str,
    groups: list[list[str]],
    tradeoff: str,
    points: int = 1,
) -> dict[str, Any]:
    return {
        "id": capability_id,
        "title": title,
        "goal": goal,
        "accepted_type_groups": groups,
        "points": points,
        "defence_tradeoff": tradeoff,
    }


_CURATED_BONUS_CAPABILITIES: dict[str, list[dict[str, Any]]] = {
    "url-shortener": [
        _bonus(
            "creator_abuse_controls",
            "Protect link creation from abuse",
            "Apply quotas or edge controls to creation without making public redirects depend on authentication.",
            [["rate_limiter"], ["waf_ddos"]],
            "Where are quotas enforced, and how do you avoid throttling legitimate redirects?",
        ),
        _bonus(
            "creator_identity",
            "Add ownership for account features",
            "Use identity for custom aliases or account management only; keep anonymous redirects public.",
            [["auth_service"]],
            "Which operations require identity, and how does auth stay off the public redirect path?",
        ),
        _bonus(
            "analytics_recovery",
            "Recover analytics without slowing redirects",
            "Keep click analytics asynchronous, preserve failed events for replay, and land aggregates in an analytical store.",
            [
                ["message_queue", "dlq", "olap_warehouse"],
                ["event_stream", "dlq", "olap_warehouse"],
            ],
            "Explain delivery guarantees, idempotent aggregation, retention, and replay operations.",
            points=2,
        ),
        _bonus(
            "redirect_observability",
            "Measure redirect health",
            "Track redirect p99, cache hit rate, origin errors, and analytics lag with actionable alerts.",
            [["observability"]],
            "Which SLO alert detects user impact, and which signals diagnose cache or origin failure?",
        ),
    ],
    "spotify-100k": [
        _bonus(
            "media_origin_resilience",
            "Protect media origin capacity",
            "Use edge delivery and durable media origins so popular audio does not overload application services.",
            [["cdn", "object_storage"]],
            "How do cache invalidation, rights restrictions, and origin failover affect cost and freshness?",
        ),
        _bonus(
            "media_pipeline_recovery",
            "Recover failed media processing",
            "Bound retries and isolate poison ingestion or transcoding jobs for safe replay.",
            [["message_queue", "dlq"], ["event_stream", "dlq"]],
            "How are duplicate jobs made safe and failed tracks made visible to operators?",
        ),
        _bonus(
            "media_observability",
            "Observe playback quality",
            "Correlate startup latency, rebuffering, CDN errors, and ingestion lag with user-facing SLOs.",
            [["observability"]],
            "Which client-side and server-side signals identify a regional playback incident?",
        ),
    ],
    "realtime-notifications": [
        _bonus(
            "notification_delivery_recovery",
            "Recover failed notification delivery",
            "Use bounded retries and a dead-letter or replay path without duplicating user-visible alerts.",
            [["message_queue", "dlq"], ["event_stream", "dlq"]],
            "How do idempotency, provider limits, and poison messages affect delivery guarantees?",
        ),
        _bonus(
            "notification_tenant_fairness",
            "Protect tenants and providers from bursts",
            "Enforce tenant-aware quotas or provider concurrency limits so one source cannot starve others.",
            [["rate_limiter"], ["distributed_cache", "rate_limiter"]],
            "How do quota keys, fairness windows, and limiter failures affect delivery?",
        ),
        _bonus(
            "notification_observability",
            "Track delivery SLOs",
            "Measure end-to-end delivery latency, provider errors, queue age, and duplicate rates.",
            [["observability"]],
            "Which alert detects user-impacting delay before the queue becomes unrecoverable?",
        ),
    ],
    "ride-sharing": [
        _bonus(
            "location_ingestion_recovery",
            "Handle late or duplicated location events",
            "Retain or replay location updates safely when consumers lag or a region briefly fails.",
            [["event_stream", "object_storage"], ["message_queue", "dlq"]],
            "How do event time, deduplication, and retention affect matching freshness and storage cost?",
        ),
        _bonus(
            "ride_request_protection",
            "Protect dispatch from request bursts",
            "Apply admission control or tenant-aware limits while preserving urgent dispatch traffic.",
            [["rate_limiter"], ["waf_ddos"]],
            "What is shed first under overload, and how do you avoid rejecting high-priority rides?",
        ),
        _bonus(
            "dispatch_observability",
            "Observe dispatch health",
            "Track match latency, location freshness, regional errors, and queue lag against explicit SLOs.",
            [["observability"]],
            "Which signals distinguish stale GPS data from a matching-service bottleneck?",
        ),
    ],
    "distributed-job-queue": [
        _bonus(
            "poison_job_recovery",
            "Isolate and replay poison jobs",
            "Add bounded retries, a dead-letter path, and operator-controlled replay for permanently failing jobs.",
            [["message_queue", "dlq"], ["event_stream", "dlq"]],
            "How do idempotency, retry backoff, and replay prevent duplicate side effects?",
        ),
        _bonus(
            "tenant_fairness",
            "Prevent noisy-neighbor starvation",
            "Enforce per-tenant concurrency or queue quotas with fair scheduling.",
            [["rate_limiter"], ["distributed_cache", "rate_limiter"]],
            "How do fairness and utilization trade off when one tenant has a large backlog?",
        ),
        _bonus(
            "queue_observability",
            "Make queue health actionable",
            "Expose queue age, retry volume, consumer saturation, and dead-letter growth with alerts.",
            [["observability"]],
            "Which lag threshold predicts an SLA miss rather than harmless burst absorption?",
        ),
    ],
    "video-streaming": [
        _bonus(
            "transcode_recovery",
            "Recover failed transcodes",
            "Make media jobs retryable and isolate corrupt inputs without blocking healthy playback.",
            [["message_queue", "dlq"], ["event_stream", "dlq"]],
            "How do you avoid duplicate renditions and detect a permanently invalid source asset?",
        ),
        _bonus(
            "origin_protection",
            "Shield origins during traffic spikes",
            "Use cache hierarchy and durable object storage to protect media origins during hot releases.",
            [["cdn", "object_storage"]],
            "How do cache stampedes, invalidation, and regional origin failure change the design?",
        ),
        _bonus(
            "playback_observability",
            "Measure playback quality",
            "Track startup time, rebuffer ratio, CDN cache hit rate, and regional playback failures.",
            [["observability"]],
            "Which user-side metric is the SLO and how does it map to server-side causes?",
        ),
    ],
    "chat-system": [
        _bonus(
            "message_replay",
            "Recover missed message processing",
            "Retain replayable events or isolate failed deliveries while preserving message ordering guarantees.",
            [["event_stream", "object_storage"], ["message_queue", "dlq"]],
            "How do retention, replay, deduplication, and per-conversation ordering interact?",
        ),
        _bonus(
            "chat_abuse_controls",
            "Limit spam and connection abuse",
            "Apply rate or edge controls to message sends and connection establishment without penalizing normal chat.",
            [["rate_limiter"], ["waf_ddos"]],
            "Which identity or conversation key is limited, and how do reconnect storms degrade?",
        ),
        _bonus(
            "chat_observability",
            "Observe real-time delivery",
            "Measure message delivery latency, offline backlog, reconnect rates, and regional gateway health.",
            [["observability"]],
            "How do you detect delayed delivery without treating every disconnected client as an outage?",
        ),
    ],
    "rate-limiter": [
        _bonus(
            "limiter_failure_policy",
            "Define safe behavior during limiter failure",
            "Protect critical downstreams during state-store or policy-service failures with an explicit fail-open or fail-closed strategy.",
            [["circuit_breaker"], ["observability", "distributed_cache"]],
            "Which routes fail open or closed, and how are stale policy and store outages surfaced?",
        ),
        _bonus(
            "policy_change_recovery",
            "Make policy changes recoverable",
            "Version or replay policy updates so distributed enforcement converges after delayed or failed propagation.",
            [
                ["event_stream", "dlq"],
                ["message_queue", "dlq"],
                ["cdc_connector", "event_stream"],
            ],
            "How do propagation delay, ordering, and rollback affect temporary quota inconsistency?",
        ),
        _bonus(
            "limiter_observability",
            "Make quota decisions explainable",
            "Monitor limiter latency, decision volume, backend errors, and false-positive signals.",
            [["observability"]],
            "How do you troubleshoot decisions without logging sensitive request data?",
        ),
    ],
}


def _attach_curated_bonus_capabilities() -> None:
    for challenge in CURATED_CHALLENGES:
        capabilities = _CURATED_BONUS_CAPABILITIES.get(challenge["slug"], [])
        variants = (challenge.get("interviewer_brief") or {}).get("variants") or []
        for variant in variants:
            if not variant.get("bonus_capabilities"):
                variant["bonus_capabilities"] = [
                    {
                        **capability,
                        "accepted_type_groups": [
                            list(group) for group in capability["accepted_type_groups"]
                        ],
                    }
                    for capability in capabilities
                ]


_attach_curated_bonus_capabilities()


async def seed_system_design_challenges(db: AsyncSession) -> int:
    """Idempotently seeds curated built-in system design challenges.

    Inserts missing challenges and keeps built-in metadata synchronized by slug.
    Returns the number of newly inserted challenges.
    """
    slugs = [item["slug"] for item in CURATED_CHALLENGES]
    stmt = select(SystemDesignChallengeModel).where(
        SystemDesignChallengeModel.slug.in_(slugs)
    )
    result = await db.execute(stmt)
    existing_by_slug = {c.slug: c for c in result.scalars().all()}

    inserted = 0
    for item in CURATED_CHALLENGES:
        existing = existing_by_slug.get(item["slug"])
        if existing is None:
            db.add(
                SystemDesignChallengeModel(
                    slug=item["slug"],
                    title=item["title"],
                    category=item["category"],
                    difficulty=item["difficulty"],
                    prompt_summary=item["prompt_summary"],
                    initial_prompt=item["initial_prompt"],
                    tags=list(item["tags"]),
                    interviewer_brief=dict(item["interviewer_brief"]),
                    is_builtin=True,
                )
            )
            inserted += 1
        elif existing.is_builtin:
            existing.title = item["title"]
            existing.category = item["category"]
            existing.difficulty = item["difficulty"]
            existing.prompt_summary = item["prompt_summary"]
            existing.initial_prompt = item["initial_prompt"]
            existing.tags = list(item["tags"])
            existing.interviewer_brief = dict(item["interviewer_brief"])
            existing.is_archived = False

    await db.commit()
    return inserted
