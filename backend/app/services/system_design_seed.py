from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_design import SystemDesignChallengeModel

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
                "payload_and_storage": "~500 bytes per URL mapping record; 7-char Base62 short codes; ~300M active records over 5 years (~1.5 TB raw mapping data)",
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
                "retention": "Default 5-year retention (~300M total records over 5 years, ~1.5 TB raw mapping data) plus optional user-specified TTL",
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
                        "API Gateway / Internal Load Balancer with OIDC/SSO middleware",
                        "Monolith or modular Link Service (create, resolve, audit, RBAC check)",
                        "Managed PostgreSQL (relational link table + ACL mappings + partitioned audit log)",
                        "Redis cache for short-lived SSO session tokens & hot `go/alias` lookups",
                        "Periodic S3 Glacier/cold object archive job for >90-day audit partitions",
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
                        "Multi-region Anycast / Edge CDN Workers + L1 in-memory hot-key cache",
                        "Sharded Distributed Cache (Redis Cluster) with hot-key replication/local cache mitigation",
                        "Distributed Link Metadata Store (DynamoDB / Cassandra / sharded CockroachDB)",
                        "High-throughput Event Stream (Kafka / Kinesis) -> Stream Processor (Flink) for bot filtering & 5s windowing",
                        "OLAP Analytics Store (ClickHouse / Druid) for real-time advertiser attribution queries",
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
                "Client mobile/web app with local chunk buffer",
                "Object Storage (S3/GCS) for transcoded audio segments",
                "CDN (CloudFront/Cloudflare) serving audio files directly via signed URLs",
                "Modular monolith or 2-3 cohesive backend services behind a Load Balancer",
                "Managed PostgreSQL (with read replica if needed) using trigram/full-text search for 500k tracks",
                "Single Redis instance for session/hot playlist metadata",
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
                        "API Gateway / Modular Backend (Device Auth, License Key Service, Sync Endpoint)",
                        "CDN + Object Storage serving AES-encrypted audio segments via signed URLs",
                        "PostgreSQL storing device registrations, playlist operation versions, and idempotency keys",
                        "Redis for active signed license lease cache and rate limits",
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
                        "CDN + Origin Shield (reducing S3 FLAC egress) + Object Storage",
                        "Stateless REST API + PostgreSQL for catalog & persistent room definitions",
                        "Stateful WebSocket Room Gateways + Redis Pub/Sub / Streams for room playback timestamps",
                        "NTP-style RTT estimation endpoint for client playback clock alignment",
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
                "Ingestion API with validation & idempotency key deduplication",
                "User Preference & Rate-Limit Cache/Service (PostgreSQL + Redis)",
                "Priority-partitioned Message Broker (Kafka / SQS queues per priority tier & channel)",
                "Channel Workers (Push, Email, SMS) with circuit breakers + Dead Letter Queues",
                "WebSocket / SSE Gateway cluster + Redis Pub/Sub for active online user routing",
                "Notification Store (Cassandra/PostgreSQL partitioned by user_id) for in-app feed",
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
                        "Outbox-backed Ingestion Service guaranteeing DB commit + event publish atomicity",
                        "Kafka partitioned by `account_id` for per-account FIFO ordering",
                        "Escalation / ACK Timer Store + Channel Dispatchers with multi-vendor circuit breakers",
                        "Immutable Append-Only Compliance Audit Log (Object Storage WORM / partitioned SQL)",
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
                        "Hierarchical Pub/Sub Fanout (Edge WebSocket Gateways keeping local match_id room maps)",
                        "Coalesced Topic-Partitioned Push Workers querying sharded pre-materialized token segments",
                        "Local Gateway Subscription Registry + Reconnect Jitter Controller",
                        "Redis Cluster / Kafka topic partitions by `match_id` + `token_bucket_shard`",
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
                "API Gateway / Persistent WebSocket or gRPC connection managers for drivers and riders",
                "Location Ingestion Service writing to in-memory Geospatial Index (Redis Geo / H3 sharded by city)",
                "Dispatch / Matching Service orchestrating sequential/ranked driver offers",
                "Trip State Service backed by strongly consistent DB (PostgreSQL / CockroachDB / Spanner) partitioned by city/trip_id",
                "Kafka / Event stream for trip state events, ETA telemetry, and async billing/analytics",
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
                        "Reservation API & Flight-Status Webhook Consumer",
                        "Strongly Consistent Schedule DB (PostgreSQL with time-bucketed exclusion/interval locks by driver_id)",
                        "Time-Bucketed Dispatch Scheduler + Spatial-Temporal Pooling Optimizer Worker",
                        "Driver Telemetry Service (Redis Geo/Streams at modest 6k QPS) + Alert Escalation for no-shows",
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
                        "Edge Connection Gateways (Couriers + Merchant Tablets)",
                        "Region-Sharded In-Memory Geospatial Index (Redis Geo / H3)",
                        "Merchant Prep-Time Estimator + Batched Route Dispatch Optimizer",
                        "Strongly Consistent Order-Trip State DB + Event Stream for live customer tracking",
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
                "Job Submission API + Admission Rate Limiter",
                "Durable Metadata & Job State Store (PostgreSQL sharded / DynamoDB / Cassandra)",
                "Ready Queues / Partitions per priority & tenant fairness scheduler",
                "Delayed Job Timing Wheel / Sorted Set / DB index scanner moving due jobs to Ready Queue",
                "Worker Fleet with lease renewal heartbeats and idempotent task execution",
                "Dead Letter Queue (DLQ) & observability dashboard",
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
                        "Scheduler Admission API + Quota Accountant",
                        "Capability-Indexed Priority Queues / Matcher + Team Fair-Share Arbiter",
                        "Strongly Consistent Job State & Fencing-Token Store (PostgreSQL / CockroachDB / etcd-leased DB)",
                        "Checkpoint Artifact Storage (S3/GCS) + GPU Agent Sidecar managing heartbeats & preemption drain",
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
                        "Outbox Event Ingester + Partitioned Ordered Queue (keyed by merchant_id)",
                        "Destination Health Monitor / Adaptive Circuit Breaker (Redis token/concurrency per host)",
                        "Time-Bucketed Delayed Retry Store (partitioned DB / timing wheel)",
                        "Stateless HTTP Delivery Workers + Cryptographic Signing + DLQ Replay Store",
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
                "daily_uploads": "~500,000 uploads/day (~5-10/sec avg; 500 MB avg, up to 5 GB 4K)",
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
                "Metadata API Servers (upload session init, video metadata)",
                "Direct-to-Object-Storage Pre-signed Multipart Upload (S3/GCS)",
                "Upload Completion Event -> DAG Transcoding Orchestrator / Queue",
                "Stateless Chunk Splitter + GPU/CPU Transcoding Workers producing HLS/DASH segments + thumbnails",
                "Encoded Video Bucket + Multi-Tier CDN for global edge playback",
                "Metadata DB (MySQL/PostgreSQL sharded by video_id) + Search Index + Redis view count buffer",
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
                        "Auth/SSO Gateway issuing short-lived CDN Signed Cookies / Key-Server tokens",
                        "Managed Object Storage + Private CDN Distribution + Office ECDN Proxy Support",
                        "Batch Transcode Worker Queue producing Encrypted HLS segments + VTT captions",
                        "PostgreSQL + Redis write-coalescing buffer for watch-completion compliance records",
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
                        "Redundant Edge Ingest POPs (RTMP/SRT) -> Real-Time GPU Transcode Pipeline (aligned keyframes)",
                        "Low-Latency CMAF Packager + Origin Shield Layer (request collapsing on live manifest/chunks)",
                        "Multi-CDN Switching Router + Edge-Cached Stateless JWT Playback Validation",
                        "DVR Ring-Buffer Storage continuously flushing immutable chunks to Object Storage for instant VOD",
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
                "daily_messages": "~20B messages/day (~230k/sec average, ~700k/sec peak; ~200 bytes avg text)",
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
                "dau": "50M DAU; ~20B messages/day (~230k messages/sec average, 700k/sec peak)",
                "group_size": "Typical groups 5-50 members; max group size capped at 500 members",
                "message_size": "Text messages average 200 bytes; media attachments stored via object storage + URL reference",
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
                "Massive write-heavy message storage partitioned by `channel_id` / `conversation_id` + monotonically increasing `message_id`",
                "Debounced/throttled presence updates to avoid connection storm cascading failures",
            ],
            "expected_components": [
                "Stateful WebSocket Chat Gateways + Service Discovery / Session Routing Store (Redis)",
                "Stateless Chat / Message Ingestion & Fan-out Services",
                "Distributed ID Generator (Snowflake / HLC) scoped for chronological sorting",
                "Wide-Column / Partitioned Message Store (Cassandra / ScyllaDB / sharded PostgreSQL by `channel_id, message_id`)",
                "Offline Sync Queue + Push Notification Adapter (APNs/FCM)",
                "Presence Service with heartbeat TTLs and lazy pull/coalesced fan-out",
                "Media Upload Service + Object Storage + CDN (outside message payload path)",
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
                        "Gateway WebSocket Fleet with Channel-Subscription Multiplexing (fan-out at gateway/channel level)",
                        "Channel Message & Thread Store partitioned by `(workspace_id, channel_id, message_id)`",
                        "Read-Cursor / Unread-Watermark Store (lazy-loaded per channel vs write-amplifying 25k user inbox rows)",
                        "Async Search Indexing Pipeline (Kafka -> Elasticsearch/OpenSearch partitioned by workspace)",
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
                        "Region-Pinned Stateful Room Gateways (consistent-hashed by `match_id` so one pod/shard owns each room)",
                        "In-Memory Ring Buffer (Redis / Pod Memory) holding last N messages + match-end TTL sweep",
                        "Embedded Aho-Corasick / local lightweight toxicity classifier + per-player flood bucket",
                        "On-Demand Report Snapshotting Queue flushing flagged match transcripts to S3",
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
                "Rate-Limiter Middleware inside API Gateway / Envoy sidecar",
                "Algorithm choice justification (Token Bucket / Sliding Window Counter vs Sliding Window Log vs Fixed Window)",
                "Redis Cluster sharded by rate-limit key executing atomic Lua scripts",
                "Rules Control Plane + Local Config Cache (pushed or polled via CDN/etcd/Redis PubSub)",
                "Local in-memory token bucket fallback / async batch sync mode discussion for extreme scale",
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
                        "Edge WAF + Auth-Aware API Gateway with Conservative In-Memory Emergency Cap",
                        "Region-Homed / Strongly Consistent Account Quota Partition (Raft-replicated store / DynamoDB conditional / pinned home Redis)",
                        "Async Cross-Region Blocklist Broadcaster + Immutable Security Block Audit Stream",
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
                        "Streaming AI Gateway Proxy (tokenizing prompt input length quickly upfront)",
                        "Redis Cluster executing Atomic Reserve / Reconcile Lua Scripts (RPM + TPM + Leased Concurrency Set)",
                        "Stream-End Settlement Hook + TTL Lease Reaper preventing permanently leaked concurrency slots",
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
