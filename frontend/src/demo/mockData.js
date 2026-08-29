export const INITIAL_MOCK_DATA = {
  candidate_profile: {
    id: "cv_demo_001",
    full_name: "John Souls",
    email: "john.souls.demo@example.com",
    phone: "+1 (555) 234-5678",
    title: "Staff Distributed Systems Engineer",
    location: "San Francisco, CA / Remote",
    summary: "High-impact systems architect specializing in high-throughput distributed state management, low-latency microservices, and cloud-native infrastructure in Go, Rust, and Python.",
    raw_text: "John Souls\nStaff Distributed Systems Engineer\njohn.souls.demo@example.com | (555) 234-5678\nSan Francisco, CA / Remote\n\nSummary:\nHigh-impact systems architect specializing in high-throughput distributed state management, low-latency microservices, and cloud-native infrastructure in Go, Rust, and Python. Proven track record leading infrastructure architecture and real-time state synchronization engines at scale.\n\nSkills:\n- Core Languages & Frameworks: Go, Rust, Python, TypeScript, gRPC, SQL\n- Infrastructure & Cloud: Kubernetes, Docker, Terraform, AWS, GCP, Distributed Tracing\n- Streaming & Storage: Apache Kafka, PostgreSQL, Redis, Elasticsearch, Raft Consensus\n\nExperience:\n- Senior Infrastructure Engineer @ ScaleGrid (2021 - Present)\n  * Architected sub-15ms real-time event streaming pipeline processing 10B+ daily events in Rust and Kafka.\n  * Reduced cloud infrastructure compute expenditure by 38% via eBPF kernel packet inspection.\n- Systems Engineer @ CloudCore (2017 - 2021)\n  * Built fault-tolerant gRPC microservices and automated multi-region PostgreSQL failover orchestration.",
    extracted_skills: ["Go", "Rust", "Kubernetes", "Distributed Systems", "Apache Kafka", "PostgreSQL", "gRPC", "AWS", "Terraform", "Distributed Tracing"],
    spoken_languages: [
      { language: "English", proficiency: "Native" },
      { language: "Spanish", proficiency: "Working Proficiency (B2)" }
    ],
    parsed_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
  },

  applications: [
    {
      id: "app_stripe_001",
      company_id: "comp_stripe",
      company_name: "Stripe",
      company: { id: "comp_stripe", name: "Stripe", domain: "stripe.com" },
      position: "Staff Infrastructure Engineer - Core Platform",
      status: "OFFER",
      location: "San Francisco, CA (Hybrid)",
      work_model: "Hybrid",
      salary_min: 240000,
      salary_max: 290000,
      currency: "USD",
      url: "https://stripe.com/jobs/staff-infra-engineer",
      job_url: "https://stripe.com/jobs/staff-infra-engineer",
      application_date: new Date(Date.now() - 86400000 * 25).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 1).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: new Date(Date.now() + 86400000 * 3).toISOString(),
      has_action_required: true,
      match_score: 94,
      fit_score: 94,
      programmatic_match_score: 92,
      description: "### Position Overview\nStripe is hiring a Staff Infrastructure Engineer to lead our Core Platform team. You will be responsible for building high-availability storage systems, optimizing request routing, and driving reliability across our global financial infrastructure.\n\n### Key Requirements\n- 8+ years experience in distributed backend systems.\n- Expertise in Go or Rust.\n- Deep understanding of consensus protocols (Raft/Paxos) and relational DB internals.",
      job_posting: {
        id: "jp_stripe_001",
        title: "Staff Infrastructure Engineer - Core Platform",
        company_name: "Stripe",
        description_markdown: "### Position Overview\nStripe is hiring a Staff Infrastructure Engineer to lead our Core Platform team. You will be responsible for building high-availability storage systems, optimizing request routing, and driving reliability across our global financial infrastructure.\n\n### Key Requirements\n- 8+ years experience in distributed backend systems.\n- Expertise in Go or Rust.\n- Deep understanding of consensus protocols (Raft/Paxos) and relational DB internals.",
        salary_min: 240000,
        salary_max: 290000,
        currency: "USD",
        location: "San Francisco, CA (Hybrid)",
        work_model: "Hybrid",
        required_skills: ["Go", "Rust", "Distributed Systems", "PostgreSQL", "Raft"],
        structured_spec: {
          compensation_text: "$240,000 - $290,000 USD",
          location_text: "San Francisco, CA",
          workplace_type: "Hybrid",
          why_hiring: "Scaling global financial infrastructure for higher throughput and zero downtime.",
          what_you_will_build: "High-availability storage systems, idempotent request routing, and consensus protocols.",
          responsibilities: [
            "Lead architecture of distributed core storage systems in Go and Rust",
            "Optimize request routing and low-latency database consensus protocols",
            "Drive high availability across Stripe's global financial ledger"
          ],
          requirements: [
            "8+ years experience in distributed backend engineering",
            "Expertise in Go or Rust",
            "Deep understanding of consensus protocols (Raft/Paxos)"
          ],
          extracted_skills: ["Go", "Rust", "Distributed Systems", "PostgreSQL", "Raft"]
        }
      },
      match_analysis_payload: {
        match_score: 94,
        fit_score: 94,
        programmatic_match_score: 92,
        recommendation: "APPLY_STRONGLY",
        seniority_fit: "MATCHES",
        critical_risks: [],
        pros: [
          "Extensive 10+ years background in Go and Rust distributed systems",
          "Deep hands-on experience with high-throughput event streaming",
          "Strong architecture alignment for financial platform reliability"
        ],
        cons: [
          "Minor gap in proprietary internal Stripe financial ledger tooling"
        ],
        matching_skills: ["Go", "Rust", "Distributed Systems", "PostgreSQL", "Raft"],
        missing_skills: [],
        summary: "Outstanding technical alignment with verified 8.5 years in distributed systems."
      },
      interview_guide_markdown: "## Stripe Technical Interview Preparation Guide\n\n### Company Architecture Focus\nStripe's core ledger operates on idempotent, ACID-compliant distributed databases. Expect questions around consensus protocols (Raft/Paxos), multi-region replication, and rate-limiting gateway proxies.\n\n### Strategic STAR Story Scenarios\n1. **High-Throughput Idempotency:** Detail how you handled duplicate financial event delivery at scale.\n2. **Database Migration Under Load:** Describe zero-downtime database schema migrations.",
      cover_letter_text: "Dear Hiring Team at Stripe,\n\nI am thrilled to express my enthusiasm for the Staff Infrastructure Engineer position. With over a decade of hands-on experience designing high-throughput distributed systems in Go and Rust, I have consistently delivered fault-tolerant platform services that scale to millions of requests per minute.\n\nSincerely,\nJohn Souls",
      cover_letter_status: "COMPLETED",
      cover_letter_generated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      events: [
        {
          id: "evt_stripe_1",
          application_id: "app_stripe_001",
          email_event_type: "OFFER_RECEIVED",
          event_type: "OFFER_RECEIVED",
          title: "Received Formal Written Offer",
          description: "Offer package received: $265,000 Base + $120,000/yr Equity RSUs + $30,000 Signing Bonus.",
          email_summary: "Offer package received: $265,000 Base + $120,000/yr Equity RSUs + $30,000 Signing Bonus.",
          email_sender: "recruiting@stripe.com",
          email_sender_name: "Stripe Recruiting",
          created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
          raw_payload: {
            decision_deadline: new Date(Date.now() + 86400000 * 3).toISOString()
          }
        },
        {
          id: "evt_stripe_2",
          application_id: "app_stripe_001",
          email_event_type: "INTERVIEW_COMPLETED",
          event_type: "INTERVIEW_COMPLETED",
          title: "System Design & Executive Onsite",
          description: "Completed 4-round virtual onsite interview with Bar Raiser and VP of Engineering.",
          email_summary: "Completed 4-round virtual onsite interview with Bar Raiser and VP of Engineering.",
          email_sender: "recruiting@stripe.com",
          email_sender_name: "Stripe Recruiting",
          created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
          raw_payload: {}
        },
        {
          id: "evt_stripe_3",
          application_id: "app_stripe_001",
          email_event_type: "EMAIL_RECEIVED",
          event_type: "EMAIL_RECEIVED",
          title: "Recruiter Scheduling Confirmation",
          description: "From: recruiting@stripe.com\nSubject: Stripe Onsite Interview Schedule\nHi Alex, Attached is your schedule for the upcoming core platform system design loop.",
          email_summary: "Hi Alex, Attached is your schedule for the upcoming core platform system design loop.",
          email_subject: "Stripe Onsite Interview Schedule",
          email_sender: "recruiting@stripe.com",
          email_sender_name: "Stripe Recruiting",
          created_at: new Date(Date.now() - 86400000 * 8).toISOString(),
          raw_payload: {
            sender: "recruiting@stripe.com",
            subject: "Stripe Onsite Interview Schedule"
          }
        }
      ]
    },
    {
      id: "app_linear_002",
      company_id: "comp_linear",
      company_name: "Linear",
      company: { id: "comp_linear", name: "Linear", domain: "linear.app" },
      position: "Principal Backend Engineer - Real-time Sync",
      status: "APPLIED",
      location: "Remote (US/EU)",
      work_model: "Remote",
      salary_min: 220000,
      salary_max: 270000,
      currency: "USD",
      url: "https://linear.app/careers/principal-backend",
      job_url: "https://linear.app/careers/principal-backend",
      application_date: new Date(Date.now() - 86400000 * 18).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 18).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: null,
      has_action_required: false,
      match_score: 91,
      fit_score: 91,
      programmatic_match_score: 89,
      description: "### About Linear\nLinear is designing the future of issue tracking and project management. We are seeking a Principal Backend Engineer to evolve our local-first real-time synchronization engine and WebSocket infrastructure.",
      job_posting: {
        id: "jp_linear_002",
        title: "Principal Backend Engineer - Real-time Sync",
        company_name: "Linear",
        description_markdown: "### About Linear\nLinear is designing the future of issue tracking and project management. We are seeking a Principal Backend Engineer to evolve our local-first real-time synchronization engine and WebSocket infrastructure.",
        salary_min: 220000,
        salary_max: 270000,
        currency: "USD",
        location: "Remote (US/EU)",
        work_model: "Remote",
        required_skills: ["Rust", "TypeScript", "WebSocket", "CRDT", "Distributed Systems"],
        structured_spec: {
          compensation_text: "$220,000 - $270,000 USD",
          location_text: "Remote (US/EU)",
          workplace_type: "Remote",
          why_hiring: "Scaling local-first real-time issue sync for global enterprise teams.",
          what_you_will_build: "Local-first optimistic state replication engine and WebSocket infrastructure.",
          responsibilities: [
            "Evolve conflict-free replicated data type (CRDT) sync engine",
            "Optimize low-latency WebSocket connection pools in Rust",
            "Maintain high availability for multi-tenant state synchronization"
          ],
          requirements: [
            "7+ years experience in distributed systems and realtime protocols",
            "Hands-on expertise in Rust or C++",
            "Experience with local-first databases or CRDTs"
          ],
          extracted_skills: ["Rust", "WebSocket", "CRDT", "TypeScript"]
        }
      },
      match_analysis_payload: {
        match_score: 91,
        fit_score: 91,
        programmatic_match_score: 88,
        recommendation: "APPLY_STRONGLY",
        seniority_fit: "MATCHES",
        critical_risks: [],
        pros: [
          "Proven expertise in real-time distributed state sync",
          "Strong Rust / WebAssembly performance optimization background"
        ],
        cons: [
          "Limited exposure to Linear's specific GraphQL schema mesh"
        ],
        matching_skills: ["Rust", "WebSocket", "TypeScript"],
        missing_skills: ["CRDT"],
        summary: "Excellent candidate fit for real-time multiplayer systems sync."
      },
      interview_guide_markdown: "## Linear System Architecture Interview Guide\n\n### Key Focus Areas\n- **CRDT Sync Protocols:** Local-first optimistic updates & conflict-free state resolution.\n- **WebSocket Backpressure:** Managing multi-tenant connection pools in Rust.",
      events: [
        {
          id: "evt_linear_1",
          application_id: "app_linear_002",
          email_event_type: "APPLICATION_CONFIRMATION",
          event_type: "APPLICATION_CONFIRMATION",
          title: "Application Received Confirmation",
          description: "From: careers@linear.app\nSubject: Thank you for applying to Linear\nHi John, We have received your application for the Principal Backend Engineer position.",
          email_summary: "Thank you for applying to Linear. We have received your application for Principal Backend Engineer.",
          email_subject: "Thank you for applying to Linear",
          email_sender: "careers@linear.app",
          email_sender_name: "Linear Careers",
          created_at: new Date(Date.now() - 86400000 * 18).toISOString(),
          raw_payload: {
            sender: "careers@linear.app",
            subject: "Thank you for applying to Linear"
          }
        }
      ]
    },
    {
      id: "app_figma_003",
      company_id: "comp_figma",
      company_name: "Figma",
      company: { id: "comp_figma", name: "Figma", domain: "figma.com" },
      position: "Staff Systems Engineer - Multiplayer Engine",
      status: "APPLIED",
      location: "San Francisco, CA",
      work_model: "Hybrid",
      salary_min: 230000,
      salary_max: 280000,
      currency: "USD",
      url: "https://figma.com/careers/staff-systems-multiplayer",
      job_url: "https://figma.com/careers/staff-systems-multiplayer",
      application_date: new Date(Date.now() - 86400000 * 8).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 8).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: null,
      has_action_required: false,
      has_interview_guide: true,
      match_score: 88,
      fit_score: 88,
      programmatic_match_score: 87,
      description: "### Role Overview\nFigma's Multiplayer Engine powers real-time collaboration for millions of designers simultaneously. Join us to scale C++/Rust server workers, low-latency WebSocket clusters, and memory-efficient document stores.",
      job_posting: {
        id: "jp_figma_003",
        title: "Staff Systems Engineer - Multiplayer Engine",
        company_name: "Figma",
        description_markdown: "### Role Overview\nFigma's Multiplayer Engine powers real-time collaboration for millions of designers simultaneously. Join us to scale C++/Rust server workers, low-latency WebSocket clusters, and memory-efficient document stores.",
        salary_min: 230000,
        salary_max: 280000,
        currency: "USD",
        location: "San Francisco, CA",
        work_model: "Hybrid",
        required_skills: ["C++", "Rust", "WebAssembly", "Low Latency"],
        structured_spec: {
          compensation_text: "$230,000 - $280,000 USD",
          location_text: "San Francisco, CA",
          workplace_type: "Hybrid",
          why_hiring: "Expanding real-time multiplayer collaborative document infrastructure.",
          what_you_will_build: "Multiplayer document sync servers and WebAssembly vector rendering pipelines.",
          responsibilities: [
            "Architect C++/Rust multiplayer document servers",
            "Optimize memory layout and low-latency network protocols"
          ],
          requirements: [
            "8+ years experience in systems programming (C++, Rust)",
            "Deep understanding of browser performance and WebAssembly"
          ],
          extracted_skills: ["C++", "Rust", "WebAssembly"]
        }
      },
      match_analysis_payload: {
        match_score: 88,
        fit_score: 88,
        programmatic_match_score: 85,
        recommendation: "APPLY_STRONGLY",
        seniority_fit: "MATCHES",
        critical_risks: [],
        pros: [
          "Deep systems programming skill set in C++ and Rust",
          "Experience with micro-second latency optimizations"
        ],
        cons: [
          "C++ desktop runtime memory alignment"
        ],
        matching_skills: ["Rust", "WebAssembly"],
        missing_skills: ["C++"],
        summary: "Strong systems architecture match for high-performance canvas engine."
      },
      interview_guide_markdown: "## Figma Multiplayer Engine Technical Interview Guide\n\n### System Architecture Focus\n- **Multiplayer State Sync:** C++/Rust document servers and WASM rendering.\n- **Low Latency Messaging:** WebSocket connection fan-out and spatial memory management.",
      interview_guide_html: "<h2>Figma Multiplayer Engine Technical Interview Guide</h2><h3>System Architecture Focus</h3><ul><li><strong>Multiplayer State Sync:</strong> C++/Rust document servers and WASM rendering.</li><li><strong>Low Latency Messaging:</strong> WebSocket connection fan-out and spatial memory management.</li></ul>",
      interview_guide_language: "en",
      interview_guide_generated_at: new Date(Date.now() - 86400000 * 4).toISOString(),
      events: [
        {
          id: "evt_figma_1",
          application_id: "app_figma_003",
          email_event_type: "APPLICATION_SUBMITTED",
          event_type: "APPLICATION_SUBMITTED",
          title: "Submitted Online Application",
          description: "Submitted application via referral link.",
          email_summary: "Submitted application via referral link.",
          email_sender: "careers@figma.com",
          email_sender_name: "Figma Recruiting",
          created_at: new Date(Date.now() - 86400000 * 8).toISOString(),
          raw_payload: {}
        }
      ]
    },
    {
      id: "app_datacamp_004",
      company_id: "comp_datacamp",
      company_name: "Datadog",
      company: { id: "comp_datacamp", name: "Datadog", domain: "datadoghq.com" },
      position: "Senior Lead Engineer - Telemetry Pipeline",
      status: "TECHNICAL_INTERVIEW",
      location: "New York, NY (Remote)",
      work_model: "Remote",
      salary_min: 210000,
      salary_max: 250000,
      currency: "USD",
      url: "https://datadoghq.com/careers/lead-telemetry",
      job_url: "https://datadoghq.com/careers/lead-telemetry",
      application_date: new Date(Date.now() - 86400000 * 12).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 3).toISOString(),
      scheduled_interview_at: new Date(Date.now() + 86400000 * 2).toISOString(),
      nearest_due_date: new Date(Date.now() + 86400000 * 2).toISOString(),
      has_action_required: true,
      has_interview_guide: true,
      match_score: 65,
      fit_score: 65,
      programmatic_match_score: 55,
      description: "### Role Summary\nLead engineer responsible for processing petabyte-scale metric, trace, and log telemetry ingestion. You will optimize Vector/FluentBit aggregators and Kafka cluster backpressure.",
      job_posting: {
        id: "jp_dd_004",
        title: "Senior Lead Engineer - Telemetry Pipeline",
        company_name: "Datadog",
        description_markdown: "### Role Summary\nLead engineer responsible for processing petabyte-scale metric, trace, and log telemetry ingestion. You will optimize Vector/FluentBit aggregators and Kafka cluster backpressure.",
        salary_min: 210000,
        salary_max: 250000,
        currency: "USD",
        location: "New York, NY (Remote)",
        work_model: "Remote",
        required_skills: ["Go", "Apache Kafka", "Observability", "Telemetry"],
        structured_spec: {
          compensation_text: "$210,000 - $250,000 USD",
          location_text: "New York, NY (Remote)",
          workplace_type: "Remote",
          why_hiring: "Scaling petabyte-scale telemetry ingestion platform.",
          what_you_will_build: "High-throughput log and metric intake pipelines using Kafka and Go.",
          responsibilities: [
            "Maintain high-throughput telemetry intake workers",
            "Optimize Kafka backpressure and storage caching"
          ],
          requirements: [
            "6+ years experience in distributed telemetry systems",
            "Proficiency in Go or C++"
          ],
          extracted_skills: ["Go", "Apache Kafka", "Telemetry"]
        }
      },
      match_analysis_payload: {
        match_score: 65,
        fit_score: 65,
        programmatic_match_score: 55,
        recommendation: "STRETCH_ROLE",
        seniority_fit: "MATCHES",
        critical_risks: [
          "Missing hands-on production experience with eBPF Linux kernel tracing",
          "Heavy telemetry aggregation SLA expectations"
        ],
        pros: [
          "Kafka stream processing mastery",
          "Strong observability & distributed tracing background"
        ],
        cons: [
          "eBPF kernel probe development required on day 1"
        ],
        matching_skills: ["Go", "Apache Kafka", "Telemetry"],
        missing_skills: ["eBPF", "Linux Kernel Probing"],
        summary: "Solid backend and Kafka background, but lacks specialized kernel eBPF tracing depth."
      },
      interview_guide_markdown: "## Datadog Telemetry Pipeline Technical Interview Guide\n\n### System Architecture & Telemetry Focus\n- **Petabyte-Scale Ingestion:** Kafka backpressure, zero-copy socket buffers, and Vector aggregator topology.\n- **eBPF Kernel Inspection:** High-throughput packet parsing and low-overhead trace collection.",
      interview_guide_html: "<h2>Datadog Telemetry Pipeline Technical Interview Guide</h2><h3>System Architecture & Telemetry Focus</h3><ul><li><strong>Petabyte-Scale Ingestion:</strong> Kafka backpressure, zero-copy socket buffers, and Vector aggregator topology.</li><li><strong>eBPF Kernel Inspection:</strong> High-throughput packet parsing and low-overhead trace collection.</li></ul>",
      interview_guide_language: "en",
      interview_guide_generated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      events: [
        {
          id: "evt_dd_1",
          application_id: "app_datacamp_004",
          email_event_type: "INTERVIEW_SCHEDULED",
          event_type: "INTERVIEW_SCHEDULED",
          title: "Technical Systems Deep Dive Scheduled",
          description: "Technical screen scheduled with Telemetry Lead Engineer.",
          email_summary: "Technical screen scheduled with Telemetry Lead Engineer.",
          email_sender: "recruiting@datadoghq.com",
          email_sender_name: "Datadog Talent",
          created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
          raw_payload: {
            scheduled_at: new Date(Date.now() + 86400000 * 2).toISOString()
          }
        }
      ]
    },
    {
      id: "app_snowflake_005",
      company_id: "comp_snowflake",
      company_name: "Snowflake",
      company: { id: "comp_snowflake", name: "Snowflake", domain: "snowflake.com" },
      position: "Principal Distributed Database Engineer",
      status: "REJECTED",
      location: "San Mateo, CA",
      work_model: "On-site",
      salary_min: 250000,
      salary_max: 310000,
      currency: "USD",
      url: "https://snowflake.com/careers/db-principal",
      job_url: "https://snowflake.com/careers/db-principal",
      application_date: new Date(Date.now() - 86400000 * 40).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 15).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: null,
      has_action_required: false,
      match_score: 45,
      fit_score: 45,
      programmatic_match_score: 40,
      description: "### Description\nFocus on query engine execution optimization and cloud storage caching layers.",
      job_posting: {
        id: "jp_sf_005",
        title: "Principal Distributed Database Engineer",
        company_name: "Snowflake",
        description_markdown: "### Description\nFocus on query engine execution optimization and cloud storage caching layers.",
        salary_min: 250000,
        salary_max: 310000,
        currency: "USD",
        location: "San Mateo, CA",
        work_model: "On-site",
        required_skills: ["C++", "SQL Engine", "Distributed Databases"],
        structured_spec: {
          compensation_text: "$250,000 - $310,000 USD",
          location_text: "San Mateo, CA",
          workplace_type: "On-site",
          why_hiring: "Evolving core cloud data warehouse query engine.",
          what_you_will_build: "Vectorized query execution operators and cloud micro-partition caching.",
          responsibilities: [
            "Optimize vectorized C++ query engine execution",
            "Design multi-tenant cloud micro-partition caching"
          ],
          requirements: [
            "10+ years database kernel development experience"
          ],
          extracted_skills: ["C++", "SQL Engine", "Distributed Databases"]
        }
      },
      match_analysis_payload: {
        match_score: 45,
        fit_score: 45,
        programmatic_match_score: 40,
        recommendation: "DO_NOT_APPLY",
        seniority_fit: "UNDERQUALIFIED",
        critical_risks: [
          "Missing 10+ years dedicated C++ database kernel engineering experience",
          "Language barrier: Role requires Fluent German (C1) not listed on candidate profile",
          "On-site requirement mismatch"
        ],
        language_match: {
          is_matched: false,
          detected_jd_language: "German",
          required_languages: [
            { language: "German", requirement: "mandatory", proficiency: "Fluent / C1" },
            { language: "English", requirement: "mandatory", proficiency: "Fluent" }
          ],
          missing_mandatory: ["German"],
          missing_preferred: [],
          warning: "Role requires Fluent / C1 German (job posting written in German), which is not listed on your candidate profile."
        },
        pros: [
          "Database query processing concepts and distributed systems background"
        ],
        cons: [
          "Requires low-level C++ database kernel internals",
          "Strict on-site presence in San Mateo, CA"
        ],
        matching_skills: ["Distributed Databases"],
        missing_skills: ["C++ Kernel Engine", "SIMD Operators"],
        summary: "Underqualified for Principal Database Kernel role due to language and kernel specialization gaps."
      },
      events: [
        {
          id: "evt_sf_1",
          application_id: "app_snowflake_005",
          email_event_type: "REJECTION_RECEIVED",
          event_type: "REJECTION_RECEIVED",
          title: "Application Status Update",
          description: "Thank you for interviewing. We have decided to proceed with another candidate.",
          email_summary: "Thank you for interviewing. We have decided to proceed with another candidate.",
          email_sender: "careers@snowflake.com",
          email_sender_name: "Snowflake Talent",
          created_at: new Date(Date.now() - 86400000 * 15).toISOString(),
          raw_payload: {}
        }
      ]
    }
  ],

  action_items: [
    {
      id: "action_001",
      application_id: "app_stripe_001",
      company_name: "Stripe",
      position: "Staff Infrastructure Engineer - Core Platform",
      title: "Review & Sign Stripe Written Offer",
      description: "Verify compensation terms ($265k base, equity schedule) and execute signing before decision deadline.",
      due_date: new Date(Date.now() + 86400000 * 3).toISOString(),
      urgency: "HIGH",
      manual_urgency: "HIGH",
      status: "PENDING",
      created_at: new Date(Date.now() - 86400000 * 1).toISOString()
    },
    {
      id: "action_002",
      application_id: "app_linear_002",
      company_name: "Linear",
      position: "Principal Backend Engineer - Real-time Sync",
      title: "Prepare System Architecture Whiteboard Scenarios",
      description: "Review CRDT conflict resolution algorithms and WebSocket backpressure strategies for Linear interview.",
      due_date: new Date(Date.now() + 86400000 * 1.5).toISOString(),
      urgency: "HIGH",
      manual_urgency: "HIGH",
      status: "PENDING",
      created_at: new Date(Date.now() - 86400000 * 2).toISOString()
    },
    {
      id: "action_003",
      application_id: "app_datacamp_004",
      company_name: "Datadog",
      position: "Senior Lead Engineer - Telemetry Pipeline",
      title: "Complete Telemetry Architecture Take-Home Assessment",
      description: "Submit online technical challenge link before timer expires.",
      due_date: new Date(Date.now() + 86400000 * 1).toISOString(),
      urgency: "HIGH",
      manual_urgency: "HIGH",
      status: "PENDING",
      created_at: new Date(Date.now() - 86400000 * 3).toISOString()
    },
    {
      id: "action_004",
      application_id: "app_figma_003",
      company_name: "Figma",
      position: "Staff Systems Engineer - Multiplayer Engine",
      title: "Send Follow-up Email to Recruiter",
      description: "Check status of application submitted 8 days ago.",
      due_date: new Date(Date.now() + 86400000 * 4).toISOString(),
      urgency: "MEDIUM",
      manual_urgency: "MEDIUM",
      status: "PENDING",
      created_at: new Date(Date.now() - 86400000 * 4).toISOString()
    },
    {
      id: "action_005",
      application_id: "app_stripe_001",
      company_name: "Stripe",
      position: "Staff Infrastructure Engineer - Core Platform",
      title: "Send Thank You Note to Bar Raiser",
      description: "Sent post-onsite appreciation note to interviewing manager.",
      due_date: new Date(Date.now() - 86400000 * 4).toISOString(),
      urgency: "LOW",
      manual_urgency: "LOW",
      status: "COMPLETED",
      created_at: new Date(Date.now() - 86400000 * 6).toISOString()
    }
  ],

  staging_items: [
    {
      id: "stage_001",
      source: "EMAIL_INTAKE",
      subject: "Interview Invitation: Cloudflare - Systems Performance",
      company_name: "Cloudflare",
      position: "Staff Performance Engineer",
      raw_content: "Hi Alex, We reviewed your profile and would love to schedule a 45-minute technical intro call regarding the Staff Performance Engineer role at Cloudflare.",
      extracted_data: {
        company: "Cloudflare",
        position: "Staff Performance Engineer",
        suggested_stage: "TECHNICAL_INTERVIEW",
        confidence: 0.88
      },
      status: "PENDING",
      created_at: new Date(Date.now() - 86400000 * 1).toISOString()
    },
    {
      id: "stage_002",
      source: "EXTENSION",
      subject: "Vercel - Lead Edge Infrastructure",
      company_name: "Vercel",
      position: "Lead Edge Infrastructure Engineer",
      raw_content: "URL: https://vercel.com/careers/lead-edge\nExtracted Job Spec: Building Next.js edge runtime routing.",
      extracted_data: {
        company: "Vercel",
        position: "Lead Edge Infrastructure Engineer",
        suggested_stage: "APPLIED",
        confidence: 0.95
      },
      status: "PENDING",
      created_at: new Date(Date.now() - 86400000 * 2).toISOString()
    },
    {
      id: "stage_003",
      source: "EMAIL_INTAKE",
      subject: "Ambiguous Title: Recruiter Reachout",
      company_name: "Uncertain Scaleup Inc",
      position: "Senior Engineer",
      raw_content: "Hey Alex! Loved your Rust background. Are you open to exploring new engineering leadership opportunities?",
      extracted_data: {
        company: "Uncertain Scaleup Inc",
        position: "Senior Backend / Infra Engineer",
        suggested_stage: "APPLIED",
        confidence: 0.62
      },
      status: "PENDING",
      created_at: new Date(Date.now() - 86400000 * 3).toISOString()
    },
    {
      id: "stage_004",
      source: "EMAIL_INTAKE",
      subject: "Application Update: Supabase Database Engineer",
      company_name: "Supabase",
      position: "Senior Postgres Kernel Engineer",
      raw_content: "Thank you for applying to Supabase. We are currently evaluating candidates.",
      extracted_data: {
        company: "Supabase",
        position: "Senior Postgres Kernel Engineer",
        suggested_stage: "APPLIED",
        confidence: 0.82
      },
      status: "RESOLVED",
      created_at: new Date(Date.now() - 86400000 * 5).toISOString()
    }
  ],

  intake_evaluations: [
    {
      id: "task_eval_101",
      task_type: "JOB_ASSESSMENT",
      job_url: "https://stripe.com/jobs/staff-infra-engineer",
      company_name: "Stripe",
      position: "Staff Infrastructure Engineer - Core Platform",
      title_hint: "Stripe - Staff Infrastructure Engineer",
      status: "COMPLETED",
      stage: "COMPLETED",
      progress: 100,
      match_score: 94,
      fit_score: 94,
      raw_text: "Stripe Staff Infrastructure Engineer core platform posting details...",
      error_message: null,
      created_at: new Date(Date.now() - 86400000 * 25).toISOString(),
      completed_at: new Date(Date.now() - 86400000 * 25).toISOString(),
      result_json: {
        application_id: "app_stripe_001",
        company: "Stripe",
        company_domain: "stripe.com",
        position: "Staff Infrastructure Engineer - Core Platform",
        summary: "Exceptional qualification match. Over 10 years experience in Go/Rust distributed systems aligns directly with Stripe core platform infrastructure requirements.",
        match_score: 94,
        fit_score: 94,
        programmatic_match_score: 92,
        recommendation: "APPLY_STRONGLY",
        seniority_fit: "MATCHES",
        critical_risks: [],
        salary_min: 240000,
        salary_max: 290000,
        currency: "USD",
        location: "San Francisco, CA (Hybrid)",
        work_model: "Hybrid",
        matching_skills: ["Go", "Rust", "Distributed Systems", "PostgreSQL", "System Architecture"],
        missing_skills: ["Proprietary Stripe Financial Ledger Tooling"],
        pros: [
          "10+ years experience building fault-tolerant backend platforms",
          "Deep expertise in event-driven streaming and Raft/Paxos consensus",
          "Strong compensation alignment ($240k - $290k)"
        ],
        cons: [
          "Requires hybrid attendance in San Francisco office"
        ],
        tailoring_strategy: {
          impact_reframing: [
            {
              bullet_point: "Maintained Kafka event streaming clusters for backend services.",
              suggested_rewrite: "Architected high-throughput Kafka streaming pipelines processing 10B+ daily financial events with zero data loss.",
              reason: "Emphasize financial scale and zero-loss reliability."
            }
          ],
          structural_adjustments: [
            "Highlight Raft consensus implementation in top experience section."
          ],
          vocabulary_translation: [
            { cv_term: "Backend Services", jd_term: "Core Distributed Platform", replacement_guidance: "Use Stripe platform terminology." }
          ]
        }
      }
    },
    {
      id: "task_eval_102",
      task_type: "JOB_ASSESSMENT",
      job_url: "https://linear.app/careers/principal-backend",
      company_name: "Linear",
      position: "Principal Backend Engineer - Real-time Sync",
      title_hint: "Linear - Principal Backend Engineer",
      status: "COMPLETED",
      stage: "COMPLETED",
      progress: 100,
      match_score: 91,
      fit_score: 91,
      raw_text: "Linear Principal Backend job spec details...",
      error_message: null,
      created_at: new Date(Date.now() - 86400000 * 18).toISOString(),
      completed_at: new Date(Date.now() - 86400000 * 18).toISOString(),
      result_json: {
        application_id: "app_linear_002",
        company: "Linear",
        company_domain: "linear.app",
        position: "Principal Backend Engineer - Real-time Sync",
        summary: "Strong strategic match for Linear's local-first architecture. Candidate demonstrates deep knowledge of WebSocket backpressure and conflict-free state resolution.",
        match_score: 91,
        fit_score: 91,
        programmatic_match_score: 89,
        recommendation: "APPLY_STRONGLY",
        seniority_fit: "MATCHES",
        critical_risks: [],
        salary_min: 220000,
        salary_max: 270000,
        currency: "USD",
        location: "Remote (US/EU)",
        work_model: "Remote",
        matching_skills: ["Rust", "Distributed Systems", "TypeScript", "WebSocket", "System Architecture"],
        missing_skills: ["Linear GraphQL Mesh"],
        pros: [
          "Proven track record in real-time distributed state sync",
          "100% remote flexibility across US/EU timezones"
        ],
        cons: [
          "High competition for principal level engineering role"
        ],
        tailoring_strategy: {
          impact_reframing: [
            {
              bullet_point: "Built WebSocket server in Go.",
              suggested_rewrite: "Engineered high-concurrency WebSocket state sync engine handling 50k active concurrent sockets with <15ms latency.",
              reason: "Quantify concurrency metrics."
            }
          ],
          structural_adjustments: [
            "Emphasize CRDT and local-first data sync experience."
          ],
          vocabulary_translation: [
            { cv_term: "Realtime Messaging", jd_term: "Local-First Sync Engine", replacement_guidance: "Align with Linear local-first paradigms." }
          ]
        }
      }
    },
    {
      id: "task_eval_104",
      task_type: "JOB_ASSESSMENT",
      job_url: "https://datadoghq.com/careers/lead-telemetry",
      company_name: "Datadog",
      position: "Senior Lead Engineer - Telemetry Pipeline",
      title_hint: "Datadog - Senior Lead Telemetry Engineer",
      status: "COMPLETED",
      stage: "COMPLETED",
      progress: 100,
      match_score: 65,
      fit_score: 65,
      raw_text: "Datadog telemetry ingestion job description...",
      error_message: null,
      created_at: new Date(Date.now() - 86400000 * 10).toISOString(),
      completed_at: new Date(Date.now() - 86400000 * 10).toISOString(),
      result_json: {
        application_id: "app_datacamp_004",
        company: "Datadog",
        company_domain: "datadoghq.com",
        position: "Senior Lead Engineer - Telemetry Pipeline",
        summary: "Solid backend and Kafka streaming foundation, but candidate lacks required kernel-level eBPF tracing depth and low-overhead socket probing experience.",
        match_score: 65,
        fit_score: 65,
        programmatic_match_score: 55,
        recommendation: "STRETCH_ROLE",
        seniority_fit: "MATCHES",
        critical_risks: [
          "Missing hands-on production experience with eBPF Linux kernel tracing",
          "High throughput telemetry aggregation SLA expectations"
        ],
        salary_min: 210000,
        salary_max: 250000,
        currency: "USD",
        location: "New York, NY (Remote)",
        work_model: "Remote",
        matching_skills: ["Go", "Apache Kafka", "Telemetry", "Distributed Systems"],
        missing_skills: ["eBPF", "Linux Kernel Probing", "Vector Pipeline Aggregation"],
        pros: [
          "Kafka stream processing mastery",
          "Strong observability & distributed tracing background"
        ],
        cons: [
          "eBPF kernel probe development required on day 1"
        ]
      }
    },
    {
      id: "task_eval_105",
      task_type: "JOB_ASSESSMENT",
      job_url: "https://snowflake.com/careers/db-principal",
      company_name: "Snowflake",
      position: "Principal Distributed Database Engineer",
      title_hint: "Snowflake - Principal Database Engineer",
      status: "COMPLETED",
      stage: "COMPLETED",
      progress: 100,
      match_score: 45,
      fit_score: 45,
      raw_text: "Snowflake database kernel query optimization description...",
      error_message: null,
      created_at: new Date(Date.now() - 86400000 * 12).toISOString(),
      completed_at: new Date(Date.now() - 86400000 * 12).toISOString(),
      result_json: {
        application_id: "app_snowflake_005",
        company: "Snowflake",
        company_domain: "snowflake.com",
        position: "Principal Distributed Database Engineer",
        summary: "Significant experience and technical gaps for Principal Database Kernel level. Mandatory C1 German required and missing 10+ years dedicated C++ kernel execution engine experience.",
        match_score: 45,
        fit_score: 45,
        programmatic_match_score: 40,
        recommendation: "DO_NOT_APPLY",
        seniority_fit: "UNDERQUALIFIED",
        critical_risks: [
          "Missing 10+ years dedicated C++ database kernel engineering experience",
          "Language barrier: Role requires Fluent German (C1) not listed on candidate profile",
          "On-site presence required in San Mateo, CA"
        ],
        salary_min: 250000,
        salary_max: 310000,
        currency: "USD",
        location: "San Mateo, CA (On-site)",
        work_model: "On-site",
        matching_skills: ["Distributed Databases", "SQL Engine Concepts"],
        missing_skills: ["C++ Kernel Engine", "SIMD Operators", "Micro-partition Caching"],
        pros: [
          "Database query processing concepts and distributed systems background"
        ],
        cons: [
          "Requires low-level C++ database kernel internals",
          "Strict on-site presence in San Mateo, CA"
        ]
      }
    },
    {
      id: "task_eval_103",
      task_type: "JOB_ASSESSMENT",
      job_url: "https://private-career-portal.internal/job/9821",
      company_name: "Unknown Company",
      position: "Backend Developer",
      title_hint: "Unknown Company - Scrape Error",
      status: "FAILED",
      stage: "SCRAPE_FAILED",
      progress: 20,
      match_score: null,
      fit_score: null,
      raw_text: "",
      error_message: "INVALID_JOB_CONTENT: Scraped page does not appear to be a job description. Authentication required.",
      created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
      completed_at: new Date(Date.now() - 3600000 * 2).toISOString()
    }
  ],

  providers: [
    {
      id: "prov_demo_1",
      name: "Local LM Studio",
      provider_type: "openai",
      base_url: "http://192.168.1.187:1234/v1",
      api_key_masked: "Not Required / Local",
      max_concurrency: 1,
      is_active: true,
      is_fallback: false,
      input_cost_per_million: 0.00,
      output_cost_per_million: 0.00,
      created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
      updated_at: new Date(Date.now() - 86400000 * 1).toISOString(),
    },
    {
      id: "prov_demo_2",
      name: "Anthropic Claude (Backup)",
      provider_type: "anthropic",
      base_url: null,
      api_key_masked: "sk-ant-...9823",
      max_concurrency: 5,
      is_active: true,
      is_fallback: true,
      input_cost_per_million: 3.00,
      output_cost_per_million: 15.00,
      created_at: new Date(Date.now() - 86400000 * 20).toISOString(),
      updated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    }
  ],

  bindings: [
    {
      task_type: "GLOBAL_DEFAULT",
      provider_id: "prov_demo_1",
      model_name: "qwen/qwen3.5-9b",
      temperature: 0.2,
      reasoning_effort: "none",
      extra_kwargs: {}
    },
    {
      task_type: "JD_EXTRACTION",
      provider_id: "prov_demo_1",
      model_name: "qwen/qwen3.5-9b",
      temperature: 0.0,
      reasoning_effort: "none",
      extra_kwargs: { use_global_default: true }
    },
    {
      task_type: "EMAIL_EXTRACTION",
      provider_id: "prov_demo_1",
      model_name: "qwen/qwen3.5-9b",
      temperature: 0.0,
      reasoning_effort: "none",
      extra_kwargs: { use_global_default: true }
    },
    {
      task_type: "ASSESSMENT",
      provider_id: "prov_demo_1",
      model_name: "qwen/qwen3.5-9b",
      temperature: 0.1,
      reasoning_effort: "none",
      extra_kwargs: { use_global_default: true }
    },
    {
      task_type: "COVER_LETTER",
      provider_id: "prov_demo_1",
      model_name: "qwen/qwen3.5-9b",
      temperature: 0.3,
      reasoning_effort: "none",
      extra_kwargs: { use_global_default: true }
    },
    {
      task_type: "INTERVIEW_GUIDE",
      provider_id: "prov_demo_1",
      model_name: "qwen/qwen3.5-9b",
      temperature: 0.3,
      reasoning_effort: "none",
      extra_kwargs: { use_global_default: true }
    },
    {
      task_type: "AGENT_REASONING",
      provider_id: "prov_demo_1",
      model_name: "qwen/qwen3.5-9b",
      temperature: 0.3,
      reasoning_effort: "none",
      extra_kwargs: { use_global_default: true }
    },
    {
      task_type: "EMBEDDING",
      provider_id: "prov_demo_1",
      model_name: "nomic-embed-text",
      embedding_dimensions: 768,
      extra_kwargs: {}
    }
  ],

  diagnostics_traces: [
    {
      id: "tr_001",
      run_id: "run_llm_eval_881",
      category: "llm",
      name: "JOB_ASSESSMENT",
      status: "success",
      latency_ms: 1240,
      start_time: new Date(Date.now() - 3600000 * 3).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 3 + 1240).toISOString(),
      metadata: { provider: "Local LM Studio", model: "qwen/qwen3.5-9b", tokens_used: 1420 },
      payload: {
        task_type: "JOB_ASSESSMENT",
        name: "JOB_ASSESSMENT",
        prompt_tokens: 940,
        completion_tokens: 480,
        total_tokens: 1420,
        model_name: "qwen/qwen3.5-9b",
        is_local: true,
        estimated_cost: 0.0,
        estimated_savings: 0.00043,
        duration_ms: 1240,
      }
    },
    {
      id: "tr_002",
      run_id: "run_scraper_772",
      category: "scraper",
      name: "scrape_job_posting_url",
      status: "success",
      latency_ms: 680,
      start_time: new Date(Date.now() - 3600000 * 5).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 5 + 680).toISOString(),
      metadata: { url: "https://linear.app/careers/principal-backend" },
      payload: {
        name: "scrape_job_posting_url",
        duration_ms: 680,
      }
    },
    {
      id: "tr_003",
      run_id: "run_worker_663",
      category: "llm",
      name: "COVER_LETTER",
      status: "success",
      latency_ms: 1450,
      start_time: new Date(Date.now() - 3600000 * 12).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 12 + 1450).toISOString(),
      metadata: { target_application: "app_stripe_001" },
      payload: {
        task_type: "COVER_LETTER",
        name: "COVER_LETTER",
        prompt_tokens: 450,
        completion_tokens: 310,
        total_tokens: 760,
        model_name: "qwen/qwen3.5-9b",
        is_local: true,
        estimated_cost: 0.0,
        estimated_savings: 0.00025,
        duration_ms: 1450,
      }
    },
    {
      id: "tr_004",
      run_id: "run_email_554",
      category: "email_sync",
      name: "fetch_imap_unread_emails",
      status: "success",
      latency_ms: 310,
      start_time: new Date(Date.now() - 3600000 * 24).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 24 + 310).toISOString(),
      metadata: { mode: "demo", status: "simulated_sync" },
      payload: {
        name: "fetch_imap_unread_emails",
        duration_ms: 310,
      }
    },
    {
      id: "tr_005",
      run_id: "run_embed_445",
      category: "embedding",
      name: "vectorize_job_spec",
      status: "success",
      latency_ms: 420,
      start_time: new Date(Date.now() - 3600000 * 30).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 30 + 420).toISOString(),
      metadata: { dimensions: 1536 },
      payload: {
        name: "vectorize_job_spec",
        duration_ms: 420,
      }
    }
  ],

  usage_overview: {
    monthly_tokens: 142800,
    monthly_spend_usd: 0.0,
    monthly_savings_usd: 14.28,
    all_time_tokens: 485200,
    all_time_spend_usd: 0.0,
    all_time_savings_usd: 48.52,
    local_inference_percentage: 100.0,
    total_llm_calls: 38,
    avg_cost_per_assessment: 0.0000,
    task_breakdown: {
      "JOB_ASSESSMENT": { calls: 24, tokens: 98400, cost_usd: 0.0, savings_usd: 9.84 },
      "COVER_LETTER": { calls: 8, tokens: 26400, cost_usd: 0.0, savings_usd: 2.64 },
      "INTERVIEW_SIMULATION": { calls: 6, tokens: 18000, cost_usd: 0.0, savings_usd: 1.80 }
    },
    comparative_costs: [
      {
        provider_name: "Local LLM (Ollama / LM Studio)",
        model_name: "Local On-Device Models",
        provider_type: "local",
        input_cost_per_million: 0.0,
        output_cost_per_million: 0.0,
        simulated_cost_usd: 0.0,
        diff_usd: 0.0,
        diff_percentage: 0.0,
        status: "identical",
        is_local: true,
      },
      {
        provider_name: "Google Gemini",
        model_name: "Gemini 2.0 Flash",
        provider_type: "google_genai",
        input_cost_per_million: 0.10,
        output_cost_per_million: 0.40,
        simulated_cost_usd: 0.026,
        diff_usd: 0.026,
        diff_percentage: 100.0,
        status: "more_expensive",
        is_local: false,
      },
      {
        provider_name: "DeepSeek",
        model_name: "DeepSeek V3",
        provider_type: "deepseek",
        input_cost_per_million: 0.14,
        output_cost_per_million: 0.28,
        simulated_cost_usd: 0.027,
        diff_usd: 0.027,
        diff_percentage: 100.0,
        status: "more_expensive",
        is_local: false,
      },
      {
        provider_name: "OpenAI",
        model_name: "GPT-4o Mini",
        provider_type: "openai",
        input_cost_per_million: 0.15,
        output_cost_per_million: 0.60,
        simulated_cost_usd: 0.043,
        diff_usd: 0.043,
        diff_percentage: 100.0,
        status: "more_expensive",
        is_local: false,
      },
      {
        provider_name: "Anthropic",
        model_name: "Claude 3.5 Haiku",
        provider_type: "anthropic",
        input_cost_per_million: 0.80,
        output_cost_per_million: 4.00,
        simulated_cost_usd: 0.272,
        diff_usd: 0.272,
        diff_percentage: 100.0,
        status: "more_expensive",
        is_local: false,
      },
      {
        provider_name: "OpenAI",
        model_name: "GPT-4o",
        provider_type: "openai",
        input_cost_per_million: 2.50,
        output_cost_per_million: 10.00,
        simulated_cost_usd: 0.725,
        diff_usd: 0.725,
        diff_percentage: 100.0,
        status: "more_expensive",
        is_local: false,
      },
      {
        provider_name: "Anthropic",
        model_name: "Claude 3.5 Sonnet",
        provider_type: "anthropic",
        input_cost_per_million: 3.00,
        output_cost_per_million: 15.00,
        simulated_cost_usd: 1.035,
        diff_usd: 1.035,
        diff_percentage: 100.0,
        status: "more_expensive",
        is_local: false,
      }
    ]
  },

  pricing_rates: [
    {
      key: "local_baseline",
      display_name: "Local LLM Benchmark (Savings Baseline)",
      provider: "local",
      input_cost_per_million: 0.15,
      output_cost_per_million: 0.60,
      description: "Standard baseline rate (GPT-4o-mini equivalent) to estimate cloud savings for local models."
    },
    {
      key: "gpt-4o",
      display_name: "OpenAI GPT-4o",
      provider: "openai",
      input_cost_per_million: 2.50,
      output_cost_per_million: 10.00,
      description: "Flagship multimodal model for complex reasoning and tasks."
    },
    {
      key: "gpt-4o-mini",
      display_name: "OpenAI GPT-4o Mini",
      provider: "openai",
      input_cost_per_million: 0.15,
      output_cost_per_million: 0.60,
      description: "Fast, cost-efficient model for intake and structured extractions."
    },
    {
      key: "claude-3-5-sonnet",
      display_name: "Anthropic Claude 3.5 Sonnet",
      provider: "anthropic",
      input_cost_per_million: 3.00,
      output_cost_per_million: 15.00,
      description: "State-of-the-art coding, analysis, and nuances."
    },
    {
      key: "claude-3-5-haiku",
      display_name: "Anthropic Claude 3.5 Haiku",
      provider: "anthropic",
      input_cost_per_million: 0.80,
      output_cost_per_million: 4.00,
      description: "Fast and responsive lightweight model."
    },
    {
      key: "gemini-2.0-flash",
      display_name: "Google Gemini 2.0 Flash",
      provider: "gemini",
      input_cost_per_million: 0.10,
      output_cost_per_million: 0.40,
      description: "Next-gen multimodal workhorse with sub-second speeds."
    },
    {
      key: "deepseek-chat",
      display_name: "DeepSeek V3",
      provider: "deepseek",
      input_cost_per_million: 0.14,
      output_cost_per_million: 0.28,
      description: "High-performance low-cost general intelligence model."
    }
  ],

  system_settings: {
    has_completed_onboarding: true,
    enable_email_intake: true,
    enable_embeddings: false,
    enable_auto_cover_letter: true,
    cover_letter_match_threshold: 70,
    cover_letter_length: "standard"
  },

  interview_sessions: [
    {
      id: "session_demo_1",
      application_id: "app_linear_002",
      company_name: "Linear",
      position: "Principal Backend Engineer - Real-time Sync",
      persona: "TECHNICAL_BAR_RAISER",
      persona_label: "Technical Bar Raiser",
      status: "COMPLETED",
      turns_data: [
        {
          turn_number: 1,
          question: "Can you describe a time when you designed a high-throughput, real-time synchronization system under tight latency constraints?",
          user_answer: "At my previous company, I led the redesign of our WebSocket state synchronization layer using Rust and CRDTs. We reduced message broadcast latencies from 120ms to under 15ms by adopting delta-based state updates.",
          score: 94,
          star_breakdown: { situation: true, task: true, action: true, result: true },
          feedback: "Outstanding STAR structure. Directly quantified latency improvements and technical architecture choices.",
          exemplar_rewrite: "I spearheaded the real-time sync overhaul, implementing state delta replication over WebSocket connection pools in Rust."
        },
        {
          turn_number: 2,
          question: "How did you manage conflict resolution and backpressure when clients reconnected with divergent state?",
          user_answer: "We implemented an append-only log with logical vector clocks. When clients reconnected, we sent compressed delta operations rather than full snapshots, mitigating socket congestion.",
          score: 92,
          star_breakdown: { situation: true, task: true, action: true, result: true },
          feedback: "Solid technical explanation of logical clocks and delta compression under network partition recovery.",
          exemplar_rewrite: "By combining logical vector clocks with LZ4-compressed delta payloads, we guaranteed deterministic client convergence."
        }
      ],
      readiness_score: 93,
      summary_feedback: "Demonstrates exceptional technical mastery in real-time systems architecture, conflict-free data types, and structured STAR communication.",
      created_at: new Date(Date.now() - 86400000 * 2).toISOString()
    }
  ],

  agent_chats: [
    {
      id: "chat_demo_1",
      title: "Pipeline Overview & Linear Prep",
      created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
      messages: [
        {
          id: "msg_1",
          role: "user",
          content: "Can you summarize my active job applications and upcoming interview deadlines?"
        },
        {
          id: "msg_2",
          role: "assistant",
          content: "Here is your active pipeline breakdown:\n\n- **Stripe** (Offer Received): $265k Base offer package. Action item due in 3 days.\n- **Linear** (Technical Interview): System Architecture screen scheduled in 2 days.\n- **Datadog** (Online Assessment): Take-home telemetry challenge due tomorrow.\n- **Figma** (Applied): Application submitted 8 days ago."
        }
      ]
    }
  ]
}
