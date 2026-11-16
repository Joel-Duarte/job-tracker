import {
  Activity,
  AlertTriangle,
  BarChart3,
  Box,
  Brain,
  Clock,
  Cog,
  Compass,
  Copy,
  Cpu,
  Database,
  DoorOpen,
  Eye,
  Film,
  Filter,
  Gauge,
  GitCommitHorizontal,
  Globe,
  HardDrive,
  Hash,
  Inbox,
  KeyRound,
  Layers,
  Lock,
  Network,
  Radio,
  Repeat,
  Search,
  Server,
  Share2,
  Shield,
  ShieldAlert,
  Smartphone,
  Sparkles,
  Table,
  Workflow,
  Zap,
} from 'lucide-vue-next'

export const DIAGRAM_ICON_MAP = {
  globe: Globe,
  smartphone: Smartphone,
  compass: Compass,
  zap: Zap,
  bolt: Zap,
  shield: Shield,
  'shield-alert': ShieldAlert,
  network: Network,
  'door-open': DoorOpen,
  gauge: Gauge,
  'key-round': KeyRound,
  radio: Radio,
  server: Server,
  cog: Cog,
  clock: Clock,
  hash: Hash,
  brain: Brain,
  film: Film,
  cpu: Cpu,
  layers: Layers,
  filter: Filter,
  database: Database,
  copy: Copy,
  table: Table,
  'hard-drive': HardDrive,
  activity: Activity,
  sparkles: Sparkles,
  lock: Lock,
  inbox: Inbox,
  'git-commit-horizontal': GitCommitHorizontal,
  'share-2': Share2,
  workflow: Workflow,
  'alert-triangle': AlertTriangle,
  search: Search,
  'bar-chart-3': BarChart3,
  repeat: Repeat,
  eye: Eye,
  box: Box,
}

export function resolveDiagramIcon(iconName) {
  return DIAGRAM_ICON_MAP[String(iconName || '').toLowerCase()] || Box
}

export const CUSTOM_ICON_OPTIONS = [
  { value: 'box', label: 'Generic Box' },
  { value: 'server', label: 'Service / Compute' },
  { value: 'database', label: 'Database / Store' },
  { value: 'bolt', label: 'Cache / Memory' },
  { value: 'git-commit-horizontal', label: 'Stream / Queue' },
  { value: 'network', label: 'Gateway / LB' },
  { value: 'brain', label: 'AI / ML Model' },
  { value: 'globe', label: 'Edge / Client' },
  { value: 'search', label: 'Search / Analytics' },
  { value: 'shield', label: 'Security / Policy' },
]

export const EDGE_PROTOCOL_OPTIONS = [
  'HTTPS',
  'gRPC',
  'SQL Query',
  'Redis RESP',
  'Async Queue',
  'Kafka Event',
  'Pub/Sub',
  'WebSocket',
  'CDC WAL',
  'Internal RPC',
]

export const CATEGORY_ACCENTS = {
  clients_edge: { label: 'Clients & Edge', color: '#0284c7' },
  traffic_api: { label: 'Traffic & API', color: '#7c3aed' },
  compute_services: { label: 'Compute & Services', color: '#2563eb' },
  caching_memory: { label: 'Caching & Memory', color: '#d97706' },
  databases_storage: { label: 'Databases & Storage', color: '#059669' },
  messaging_streaming: { label: 'Messaging & Streaming', color: '#db2777' },
  search_analytics_ops: { label: 'Search, Analytics & Ops', color: '#4f46e5' },
}

export const DEFAULT_DIAGRAM_CATEGORIES = [
  { id: 'clients_edge', label: 'Clients & Edge' },
  { id: 'traffic_api', label: 'Traffic & API' },
  { id: 'compute_services', label: 'Compute & Services' },
  { id: 'caching_memory', label: 'Caching & Memory' },
  { id: 'databases_storage', label: 'Databases & Storage' },
  { id: 'messaging_streaming', label: 'Messaging & Streaming' },
  { id: 'search_analytics_ops', label: 'Search, Analytics & Ops' },
]

export const DEFAULT_DIAGRAM_BLOCKS = [
  { type_id: 'web_client', label: 'Web / Browser Client', category: 'clients_edge', icon: 'globe', default_role: 'Browser SPA or SSR web client initiating user traffic.' },
  { type_id: 'mobile_client', label: 'Mobile Client', category: 'clients_edge', icon: 'smartphone', default_role: 'iOS/Android mobile application sending API or WebSocket traffic.' },
  { type_id: 'dns', label: 'DNS / GeoDNS', category: 'clients_edge', icon: 'compass', default_role: 'Resolves domain names to nearest healthy regional PoP or VIP.' },
  { type_id: 'cdn', label: 'CDN / Edge Cache', category: 'clients_edge', icon: 'zap', default_role: 'Caches static assets, media segments, or cacheable responses near users.' },
  { type_id: 'waf_ddos', label: 'WAF / DDoS Shield', category: 'clients_edge', icon: 'shield', default_role: 'Filters malicious payloads, bot bursts, and L7/L4 volumetric attacks.' },
  { type_id: 'load_balancer', label: 'Load Balancer', category: 'traffic_api', icon: 'network', default_role: 'Distributes inbound traffic across healthy backend instances (L4/L7).' },
  { type_id: 'api_gateway', label: 'API Gateway', category: 'traffic_api', icon: 'door-open', default_role: 'Terminates TLS, routes REST/GraphQL/gRPC calls, and enforces auth & quotas.' },
  { type_id: 'rate_limiter', label: 'Rate Limiter', category: 'traffic_api', icon: 'gauge', default_role: 'Throttles per-user/IP/tenant requests using token bucket or sliding window.' },
  { type_id: 'auth_service', label: 'Auth / IAM Service', category: 'traffic_api', icon: 'key-round', default_role: 'Issues/validates JWTs, OAuth2 tokens, API keys, and RBAC policies.' },
  { type_id: 'realtime_gateway', label: 'WebSocket / Push Gateway', category: 'traffic_api', icon: 'radio', default_role: 'Holds persistent WebSocket/SSE/MQTT connections for real-time delivery.' },
  { type_id: 'content_filter', label: 'URL / Payload Safety Filter', category: 'traffic_api', icon: 'shield-alert', default_role: 'Validates URLs/payloads against malware/phishing blocklists and policy rules before persistence or redirect.' },
  { type_id: 'app_service', label: 'Stateless App Service', category: 'compute_services', icon: 'server', default_role: 'Core domain microservice handling stateless business logic.' },
  { type_id: 'async_worker', label: 'Background Worker Pool', category: 'compute_services', icon: 'cog', default_role: 'Consumes async jobs for retries, enrichment, notifications, or ETL.' },
  { type_id: 'scheduler', label: 'Scheduler / TTL Sweeper', category: 'compute_services', icon: 'clock', default_role: 'Triggers delayed tasks, link TTL/expiration sweeps, billing runs, or periodic jobs.' },
  { type_id: 'id_generator', label: 'Unique ID / Key Generator', category: 'compute_services', icon: 'hash', default_role: 'Generates globally unique sortable IDs or collision-free short codes.' },
  { type_id: 'ml_inference', label: 'ML / Ranking Service', category: 'compute_services', icon: 'brain', default_role: 'Scores embeddings, fraud risk, personalization ranking, or LLM inference.' },
  { type_id: 'media_transcoder', label: 'Media / Document Processor', category: 'compute_services', icon: 'film', default_role: 'Chunks, transcodes, thumbnails, or parses uploaded binaries.' },
  { type_id: 'distributed_cache', label: 'Distributed Cache (Redis)', category: 'caching_memory', icon: 'bolt', default_role: 'In-memory KV store for hot reads, sessions, locks, and sub-ms lookups.' },
  { type_id: 'local_cache', label: 'Local / L1 In-Process Cache', category: 'caching_memory', icon: 'cpu', default_role: 'Ultra-fast local memory cache shielding remote cache/DB from hot keys.' },
  { type_id: 'feature_store', label: 'Feature / State Store', category: 'caching_memory', icon: 'layers', default_role: 'Low-latency online store for ML features, counters, or session state.' },
  { type_id: 'bloom_filter', label: 'Bloom Filter / Dedup Index', category: 'caching_memory', icon: 'filter', default_role: 'Compact probabilistic membership check avoiding costly DB misses.' },
  { type_id: 'relational_db', label: 'Primary Relational DB', category: 'databases_storage', icon: 'database', default_role: 'ACID relational store with primary-replica or sharded topology.' },
  { type_id: 'read_replica', label: 'DB Read Replica', category: 'databases_storage', icon: 'copy', default_role: 'Serves scaled read queries asynchronously replicated from the primary.' },
  { type_id: 'nosql_kv', label: 'NoSQL / Wide-Column / KV DB', category: 'databases_storage', icon: 'table', default_role: 'Horizontally partitioned KV/document/wide-column store (Dynamo/Cassandra).' },
  { type_id: 'object_storage', label: 'Object / Blob Storage', category: 'databases_storage', icon: 'hard-drive', default_role: 'Durable S3-compatible blob store for media, backups, and data lake files.' },
  { type_id: 'timeseries_db', label: 'Time-Series DB', category: 'databases_storage', icon: 'activity', default_role: 'Append-optimized store for metrics, telemetry, or IoT event series.' },
  { type_id: 'vector_db', label: 'Vector Index / DB', category: 'databases_storage', icon: 'sparkles', default_role: 'ANN similarity index (HNSW/IVF) for semantic retrieval and RAG.' },
  { type_id: 'consensus_store', label: 'Coordination / Lease Store', category: 'databases_storage', icon: 'lock', default_role: 'Raft/Paxos metadata store for leader election, locks, and shard maps.' },
  { type_id: 'message_queue', label: 'Task Queue', category: 'messaging_streaming', icon: 'inbox', default_role: 'Decouples producers from consumers with at-least-once delivery & visibility timeout.' },
  { type_id: 'event_stream', label: 'Event Log / Kafka Stream', category: 'messaging_streaming', icon: 'git-commit-horizontal', default_role: 'Partitioned append-only log for high-throughput replayable event streams.' },
  { type_id: 'pubsub_bus', label: 'Pub/Sub Fan-out Bus', category: 'messaging_streaming', icon: 'share-2', default_role: 'Broadcasts topic events to multiple independent downstream subscribers.' },
  { type_id: 'stream_processor', label: 'Stream Processor (Flink)', category: 'messaging_streaming', icon: 'workflow', default_role: 'Stateful windowed aggregation, joins, and CEP over live event streams.' },
  { type_id: 'dlq', label: 'Dead-Letter Queue (DLQ)', category: 'messaging_streaming', icon: 'alert-triangle', default_role: 'Isolates poison messages exceeding retry bounds for replay and triage.' },
  { type_id: 'search_engine', label: 'Full-Text / Geo Search', category: 'search_analytics_ops', icon: 'search', default_role: 'Inverted/spatial index (Elasticsearch/OpenSearch) for search and filtering.' },
  { type_id: 'olap_warehouse', label: 'Analytics / OLAP Store', category: 'search_analytics_ops', icon: 'bar-chart-3', default_role: 'Columnar analytical warehouse (BigQuery/ClickHouse/Snowflake) for rollups.' },
  { type_id: 'cdc_connector', label: 'Outbox / CDC Pipeline', category: 'search_analytics_ops', icon: 'repeat', default_role: 'Streams DB WAL changes reliably (Debezium/Outbox) without dual-write races.' },
  { type_id: 'observability', label: 'Metrics, Logs & Tracing', category: 'search_analytics_ops', icon: 'eye', default_role: 'Collects OpenTelemetry traces, p99 latency SLO metrics, alerts, and audit logs.' },
]

export const DEFAULT_CLOUD_PROVIDERS = [
  { id: 'generic', label: 'Generic (Cloud-Agnostic)', short_label: 'Generic' },
  { id: 'aws', label: 'Amazon Web Services (AWS)', short_label: 'AWS' },
  { id: 'azure', label: 'Microsoft Azure', short_label: 'Azure' },
  { id: 'gcp', label: 'Google Cloud (GCP)', short_label: 'GCP' },
  { id: 'cloudflare', label: 'Cloudflare', short_label: 'CF' },
  { id: 'oci', label: 'Oracle Cloud (OCI)', short_label: 'OCI' },
]

export const CLOUD_EQUIVALENTS_BY_TYPE = {
  web_client: { aws: 'CloudFront + S3 SPA / Amplify', azure: 'Azure Static Web Apps', gcp: 'Firebase Hosting / GCS SPA', cloudflare: 'Cloudflare Pages', oci: 'OCI Object Storage + Web App' },
  mobile_client: { aws: 'AWS Amplify / Mobile SDK', azure: 'Azure Mobile Apps', gcp: 'Firebase Mobile SDK', cloudflare: 'Mobile App + Cloudflare Edge', oci: 'Mobile Client + OCI Edge' },
  dns: { aws: 'Amazon Route 53', azure: 'Azure DNS / Traffic Manager', gcp: 'Google Cloud DNS', cloudflare: 'Cloudflare Authoritative DNS', oci: 'OCI DNS & Traffic Management' },
  cdn: { aws: 'Amazon CloudFront', azure: 'Azure Front Door / CDN', gcp: 'Google Cloud CDN', cloudflare: 'Cloudflare Global CDN', oci: 'OCI Edge / Akamai CDN' },
  waf_ddos: { aws: 'AWS WAF & Shield Advanced', azure: 'Azure WAF & DDoS Protection', gcp: 'Google Cloud Armor', cloudflare: 'Cloudflare WAF & DDoS', oci: 'OCI Web Application Firewall' },
  load_balancer: { aws: 'AWS ALB / NLB (ELB)', azure: 'Azure Application Gateway / LB', gcp: 'Google Cloud Load Balancing', cloudflare: 'Cloudflare Load Balancing', oci: 'OCI Flexible Load Balancer' },
  api_gateway: { aws: 'Amazon API Gateway', azure: 'Azure API Management (APIM)', gcp: 'Apigee / GCP API Gateway', cloudflare: 'Cloudflare API Gateway', oci: 'OCI API Gateway' },
  rate_limiter: { aws: 'AWS WAF / API GW Usage Plans', azure: 'Azure APIM Rate-Limit Policy', gcp: 'Cloud Armor Rate Limiting', cloudflare: 'Cloudflare Rate Limiting', oci: 'OCI API Gateway Rate Limit' },
  auth_service: { aws: 'Amazon Cognito / AWS IAM', azure: 'Microsoft Entra ID (Azure AD)', gcp: 'GCP Identity Platform', cloudflare: 'Cloudflare Access (Zero Trust)', oci: 'OCI IAM Identity Domains' },
  realtime_gateway: { aws: 'API Gateway WebSockets', azure: 'Azure Web PubSub / SignalR', gcp: 'Cloud Run WebSockets', cloudflare: 'Cloudflare Durable Objects (WS)', oci: 'OCI API GW / LB WebSockets' },
  content_filter: { aws: 'AWS GuardDuty / Lambda Filter', azure: 'Azure AI Content Safety', gcp: 'Google Web Risk API', cloudflare: 'Cloudflare Gateway / URL Scanner', oci: 'OCI Threat Intel / Functions' },
  app_service: { aws: 'AWS ECS / EKS / EC2', azure: 'Azure App Service / AKS', gcp: 'Google Cloud Run / GKE', cloudflare: 'Cloudflare Workers', oci: 'OCI Container Engine (OKE)' },
  async_worker: { aws: 'AWS Lambda / ECS Workers', azure: 'Azure Functions / Container Apps', gcp: 'Cloud Run / Cloud Functions Workers', cloudflare: 'Cloudflare Queue Consumer Workers', oci: 'OCI Functions / Container Instances' },
  scheduler: { aws: 'Amazon EventBridge Scheduler', azure: 'Azure Logic Apps / Timer Functions', gcp: 'Google Cloud Scheduler', cloudflare: 'Cloudflare Cron Triggers', oci: 'OCI Resource Scheduler' },
  id_generator: { aws: 'ECS Key Service + DynamoDB Counter', azure: 'Azure Container Apps Key Service', gcp: 'Cloud Run Key Range Allocator', cloudflare: 'Durable Objects Coordinator', oci: 'OKE Key Generator Service' },
  ml_inference: { aws: 'Amazon SageMaker / Bedrock', azure: 'Azure ML / OpenAI Service', gcp: 'Google Vertex AI', cloudflare: 'Cloudflare Workers AI', oci: 'OCI Data Science / GenAI' },
  media_transcoder: { aws: 'AWS Elemental MediaConvert', azure: 'Azure Media / Container Batch', gcp: 'Google Transcoder API', cloudflare: 'Cloudflare Stream', oci: 'OCI Vision / Media Services' },
  distributed_cache: { aws: 'Amazon ElastiCache (Redis)', azure: 'Azure Cache for Redis', gcp: 'Google Cloud Memorystore', cloudflare: 'Cloudflare Workers KV / Durable Objects', oci: 'OCI Cache (Managed Redis)' },
  local_cache: { aws: 'In-Process RAM (ECS/EKS Pod)', azure: 'In-Memory Cache (App Service)', gcp: 'In-Process Memory (Cloud Run)', cloudflare: 'Cloudflare Edge Cache API', oci: 'In-Process Cache (OKE Pod)' },
  feature_store: { aws: 'SageMaker Feature Store', azure: 'Azure Managed Redis / Cosmos', gcp: 'Vertex AI Feature Store', cloudflare: 'Workers KV Online State', oci: 'OCI NoSQL / Cache Store' },
  bloom_filter: { aws: 'ElastiCache RedisBloom', azure: 'Azure Managed Redis (RedisBloom)', gcp: 'Memorystore / In-Memory Filter', cloudflare: 'Durable Objects / Workers Filter', oci: 'OCI Cache (Redis Modules)' },
  relational_db: { aws: 'Amazon RDS / Aurora PostgreSQL', azure: 'Azure Database for PostgreSQL', gcp: 'Google Cloud SQL / Spanner', cloudflare: 'Cloudflare D1', oci: 'OCI Autonomous Database' },
  read_replica: { aws: 'Amazon Aurora / RDS Read Replica', azure: 'Azure PostgreSQL Read Replica', gcp: 'Cloud SQL Read Replica', cloudflare: 'Cloudflare D1 Read Replication', oci: 'OCI MySQL / Autonomous Replica' },
  nosql_kv: { aws: 'Amazon DynamoDB', azure: 'Azure Cosmos DB', gcp: 'Google Firestore / Bigtable', cloudflare: 'Cloudflare Workers KV / DO', oci: 'OCI NoSQL Database Cloud' },
  object_storage: { aws: 'Amazon S3', azure: 'Azure Blob Storage', gcp: 'Google Cloud Storage (GCS)', cloudflare: 'Cloudflare R2', oci: 'OCI Object Storage' },
  timeseries_db: { aws: 'Amazon Timestream', azure: 'Azure Data Explorer (Kusto)', gcp: 'Cloud Bigtable Time-Series', cloudflare: 'Cloudflare Analytics Engine', oci: 'OCI Logging Analytics TS' },
  vector_db: { aws: 'OpenSearch Vector / Aurora pgvector', azure: 'Azure AI Search / Cosmos pgvector', gcp: 'Vertex AI Vector Search', cloudflare: 'Cloudflare Vectorize', oci: 'OCI Database 23ai Vector Search' },
  consensus_store: { aws: 'AWS etcd / DynamoDB Lock Table', azure: 'Azure Blob Leases / etcd', gcp: 'Cloud Spanner / etcd', cloudflare: 'Durable Objects Coordination', oci: 'OCI etcd / Autonomous Lock' },
  message_queue: { aws: 'Amazon SQS', azure: 'Azure Service Bus Queues', gcp: 'Google Cloud Tasks / Pub/Sub', cloudflare: 'Cloudflare Queues', oci: 'OCI Queue Service' },
  event_stream: { aws: 'Amazon Kinesis / MSK (Kafka)', azure: 'Azure Event Hubs', gcp: 'Google Cloud Pub/Sub', cloudflare: 'Cloudflare Pipelines', oci: 'OCI Streaming (Kafka-compat)' },
  pubsub_bus: { aws: 'Amazon SNS', azure: 'Azure Event Grid / Service Bus', gcp: 'Google Cloud Pub/Sub Topics', cloudflare: 'Cloudflare Queues Fan-out', oci: 'OCI Notifications & Streaming' },
  stream_processor: { aws: 'AWS Managed Apache Flink', azure: 'Azure Stream Analytics', gcp: 'Google Cloud Dataflow', cloudflare: 'Cloudflare Pipelines Stream', oci: 'OCI GoldenGate Stream Analytics' },
  dlq: { aws: 'Amazon SQS DLQ', azure: 'Azure Service Bus DLQ', gcp: 'Google Pub/Sub Dead-Letter', cloudflare: 'Cloudflare Queue DLQ', oci: 'OCI Queue Dead-Letter Channel' },
  search_engine: { aws: 'Amazon OpenSearch Service', azure: 'Azure AI Search', gcp: 'Vertex AI Search / Elastic', cloudflare: 'Cloudflare Vectorize / D1 FTS', oci: 'OCI Search Service (OpenSearch)' },
  olap_warehouse: { aws: 'Amazon Redshift / Athena', azure: 'Azure Synapse / Fabric', gcp: 'Google BigQuery', cloudflare: 'R2 + Workers Analytics Engine', oci: 'OCI Autonomous Data Warehouse' },
  cdc_connector: { aws: 'AWS DMS / MSK Debezium', azure: 'Azure Data Factory CDC / Event Hubs', gcp: 'Google Datastream (CDC)', cloudflare: 'D1 Export / Worker Outbox', oci: 'OCI GoldenGate CDC' },
  observability: { aws: 'Amazon CloudWatch & X-Ray', azure: 'Azure Monitor & App Insights', gcp: 'Google Cloud Monitoring & Trace', cloudflare: 'Cloudflare Logpush & Analytics', oci: 'OCI Monitoring, Logging & APM' },
}

export function getProviderShortLabel(providerId, providers = DEFAULT_CLOUD_PROVIDERS) {
  const list = providers?.length ? providers : DEFAULT_CLOUD_PROVIDERS
  const found = list.find((p) => p.id === providerId)
  return found ? found.short_label : 'Generic'
}

export function getBlockEquivalents(typeId, catalogBlocks = []) {
  const fromCatalog = (catalogBlocks || []).find((b) => b.type_id === typeId)?.cloud_equivalents
  const map = fromCatalog && Object.keys(fromCatalog).length ? fromCatalog : CLOUD_EQUIVALENTS_BY_TYPE[typeId]
  if (!map) return []
  return DEFAULT_CLOUD_PROVIDERS.filter((p) => p.id !== 'generic' && map[p.id]).map((p) => ({
    id: p.id,
    shortLabel: p.short_label,
    label: p.label,
    serviceName: map[p.id],
  }))
}

export function resolveBlockCloudDisplay(item, cloudProvider = 'generic', catalogBlocks = [], providers = DEFAULT_CLOUD_PROVIDERS) {
  const typeId = String(item?.type_id || 'custom')
  const catalogBlock = (catalogBlocks || []).find((b) => b.type_id === typeId) ||
    DEFAULT_DIAGRAM_BLOCKS.find((b) => b.type_id === typeId)
  const genericLabel = String(item?.generic_label || catalogBlock?.label || item?.label || item?.name || 'Custom Block')
  const eqs = getBlockEquivalents(typeId, catalogBlocks)
  const activeEq = cloudProvider && cloudProvider !== 'generic' ? eqs.find((e) => e.id === cloudProvider) : null
  return {
    displayTitle: activeEq ? activeEq.serviceName : genericLabel,
    genericLabel,
    cloudProvider: activeEq ? cloudProvider : 'generic',
    cloudBadge: activeEq ? getProviderShortLabel(cloudProvider, providers) : '',
    cloudService: activeEq ? activeEq.serviceName : '',
    equivalentsList: eqs,
  }
}

export function serializeFlowNodes(vueFlowNodes) {
  return (vueFlowNodes || []).map((n) => ({
    id: String(n.id),
    type_id: String(n.data?.type_id || 'custom'),
    label: String(n.data?.label || 'Component'),
    generic_label: String(n.data?.generic_label || ''),
    cloud_provider: String(n.data?.cloud_provider || 'generic'),
    category: String(n.data?.category || 'compute_services'),
    icon: String(n.data?.icon || 'box'),
    tech_stack: String(n.data?.tech_stack || ''),
    notes: String(n.data?.notes || ''),
    is_custom: Boolean(n.data?.is_custom),
    position: {
      x: Math.round(Number(n.position?.x || 0) * 10) / 10,
      y: Math.round(Number(n.position?.y || 0) * 10) / 10,
    },
  }))
}

export function serializeFlowEdges(vueFlowEdges) {
  return (vueFlowEdges || []).map((e) => ({
    id: String(e.id),
    source: String(e.source),
    target: String(e.target),
    source_handle: e.sourceHandle || null,
    target_handle: e.targetHandle || null,
    protocol: String(e.data?.protocol || ''),
    delivery_mode: e.data?.delivery_mode === 'async' ? 'async' : 'sync',
    label: String(e.data?.text_label || ''),
  }))
}

export function formatEdgeDisplayLabel(protocol, deliveryMode, labelText) {
  const trimmed = String(labelText || '').trim()
  const isAsync = deliveryMode === 'async'
  const protoPart = String(protocol || '').trim()
  if (trimmed && isAsync) return `${trimmed} (async)`
  if (trimmed) return trimmed
  if (protoPart && isAsync) return `${protoPart} (async)`
  if (protoPart) return protoPart
  return isAsync ? 'Async flow' : ''
}
