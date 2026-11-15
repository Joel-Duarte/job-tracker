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
            "hidden_context": {
                "dau": "20M daily active users; ~100M new shortened URLs created per month",
                "read_write_ratio": "100:1 read-heavy (~4,000 redirect QPS average, ~12,000 peak QPS; ~40 writes/s average, ~120 peak)",
                "payload_size": "~500 bytes per URL mapping record; short code length 7 chars (Base62)",
                "retention": "Default 5-year retention (~300M total records over 5 years, ~1.5 TB raw mapping data)",
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
                "API Gateway / Load Balancer",
                "Application servers separated or scaled independently for write vs redirect paths",
                "Distributed Key Generation Service (KGS) or Snowflake/counter + Base62 encoding (or hash + collision check)",
                "Distributed cache (Redis) for hot short-to-long URL mappings",
                "Primary database (PostgreSQL / DynamoDB / Cassandra) keyed on short_code",
                "Async queue / stream for click analytics aggregation",
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
        },
    },
]


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

    await db.commit()
    return inserted
