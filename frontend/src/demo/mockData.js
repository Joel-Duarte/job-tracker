export const INITIAL_MOCK_DATA = {
  candidate_profile: {
    id: "cv_demo_001",
    full_name: "Alex Rivera",
    email: "alex.rivera@example.com",
    phone: "+1 (555) 234-5678",
    title: "Staff Distributed Systems Engineer",
    summary: "Experienced Staff Distributed Systems Engineer with 10+ years architecting high-throughput fault-tolerant backend microservices, event-driven streaming pipelines, and cloud-native infrastructure in Rust, Go, and Python.",
    raw_text: "Alex Rivera\nStaff Distributed Systems Engineer\nalex.rivera@example.com | (555) 234-5678\nSan Francisco, CA\n\nSummary:\nStaff Distributed Systems Engineer with 10+ years of experience building scalable backend platforms, streaming architectures (Kafka, Flink), and distributed databases (PostgreSQL, Cassandra). Proven track record leading infrastructure architecture at scale.\n\nSkills:\n- Languages: Go, Rust, Python, TypeScript, SQL\n- Infrastructure: Kubernetes, Docker, Terraform, AWS, GCP\n- Streaming & DBs: Apache Kafka, PostgreSQL, Redis, Elasticsearch\n\nExperience:\n- Principal Systems Engineer @ TechCorp (2021 - Present)\n- Senior Distributed Systems Engineer @ CloudScale (2017 - 2021)",
    extracted_skills: ["Go", "Rust", "Python", "Distributed Systems", "Apache Kafka", "Kubernetes", "PostgreSQL", "System Architecture", "Event-Driven Microservices"],
    parsed_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
  },

  applications: [
    {
      id: "app_stripe_001",
      company_id: "comp_stripe",
      company_name: "Stripe",
      position: "Staff Infrastructure Engineer - Core Platform",
      status: "OFFER",
      location: "San Francisco, CA (Hybrid)",
      work_model: "Hybrid",
      salary_min: 240000,
      salary_max: 290000,
      currency: "USD",
      url: "https://stripe.com/jobs/staff-infra-engineer",
      application_date: new Date(Date.now() - 86400000 * 25).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 1).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: new Date(Date.now() + 86400000 * 3).toISOString(),
      has_action_required: true,
      match_score: 94,
      fit_score: 94,
      programmatic_match_score: 92,
      description: "### Position Overview\nStripe is hiring a Staff Infrastructure Engineer to lead our Core Platform team. You will be responsible for building high-availability storage systems, optimizing request routing, and driving reliability across our global financial infrastructure.\n\n### Key Requirements\n- 8+ years experience in distributed backend systems.\n- Expertise in Go or Rust.\n- Deep understanding of consensus protocols (Raft/Paxos) and relational DB internals.",
      match_analysis_payload: {
        match_score: 94,
        fit_score: 94,
        key_strengths: [
          "Extensive 10+ years background in Go and Rust distributed systems",
          "Deep hands-on experience with high-throughput event streaming",
          "Strong architecture alignment for financial platform reliability"
        ],
        gaps: [
          "Minor gap in proprietary internal Stripe financial ledger tooling"
        ],
        gap_closing_tips: [
          "Highlight past experience designing idempotency frameworks and distributed transaction boundaries."
        ]
      },
      cover_letter_text: "Dear Hiring Team at Stripe,\n\nI am thrilled to express my enthusiasm for the Staff Infrastructure Engineer position. With over a decade of hands-on experience designing high-throughput distributed systems in Go and Rust, I have consistently delivered fault-tolerant platform services that scale to millions of requests per minute.\n\nAt my previous roles, I led core infrastructure initiatives that improved platform uptime to 99.999% while reducing P99 latency. Stripe's commitment to financial infrastructure excellence resonates deeply with my technical passion.\n\nSincerely,\nAlex Rivera",
      cover_letter_status: "COMPLETED",
      cover_letter_generated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      events: [
        {
          id: "evt_stripe_1",
          application_id: "app_stripe_001",
          event_type: "OFFER_RECEIVED",
          title: "Received Formal Written Offer",
          description: "Offer package received: $265,000 Base + $120,000/yr Equity RSUs + $30,000 Signing Bonus.",
          created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
          raw_payload: {
            decision_deadline: new Date(Date.now() + 86400000 * 3).toISOString()
          }
        },
        {
          id: "evt_stripe_2",
          application_id: "app_stripe_001",
          event_type: "INTERVIEW_COMPLETED",
          title: "System Design & Executive Onsite",
          description: "Completed 4-round virtual onsite interview with Bar Raiser and VP of Engineering.",
          created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
          raw_payload: {}
        }
      ]
    },
    {
      id: "app_linear_002",
      company_id: "comp_linear",
      company_name: "Linear",
      position: "Principal Backend Engineer - Real-time Sync",
      status: "TECHNICAL_INTERVIEW",
      location: "Remote (US/EU)",
      work_model: "Remote",
      salary_min: 220000,
      salary_max: 270000,
      currency: "USD",
      url: "https://linear.app/careers/principal-backend",
      application_date: new Date(Date.now() - 86400000 * 18).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      scheduled_interview_at: new Date(Date.now() + 86400000 * 2).toISOString(),
      nearest_due_date: new Date(Date.now() + 86400000 * 2).toISOString(),
      has_action_required: true,
      match_score: 91,
      fit_score: 91,
      programmatic_match_score: 89,
      description: "### About Linear\nLinear is designing the future of issue tracking and project management. We are seeking a Principal Backend Engineer to evolve our local-first real-time synchronization engine and WebSocket infrastructure.\n\n### Responsibilities\n- Scale real-time GraphQL subscriptions and CRDT synchronization.\n- Optimize client-side & server-side SQLite state persistence.",
      match_analysis_payload: {
        match_score: 91,
        fit_score: 91,
        key_strengths: [
          "Proven expertise in real-time distributed state sync",
          "Strong Rust / WebAssembly performance optimization background"
        ],
        gaps: [
          "Limited exposure to Linear's specific GraphQL schema mesh"
        ],
        gap_closing_tips: [
          "Prepare examples of conflict-free replicated data types (CRDTs) used in past projects."
        ]
      },
      events: [
        {
          id: "evt_linear_1",
          application_id: "app_linear_002",
          event_type: "INTERVIEW_SCHEDULED",
          title: "System Architecture Deep Dive",
          description: "Technical interview scheduled with Co-founder / CTO.",
          created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
          raw_payload: {
            scheduled_at: new Date(Date.now() + 86400000 * 2).toISOString()
          }
        }
      ]
    },
    {
      id: "app_figma_003",
      company_id: "comp_figma",
      company_name: "Figma",
      position: "Staff Systems Engineer - Multiplayer Engine",
      status: "APPLIED",
      location: "San Francisco, CA",
      work_model: "Hybrid",
      salary_min: 230000,
      salary_max: 280000,
      currency: "USD",
      url: "https://figma.com/careers/staff-systems-multiplayer",
      application_date: new Date(Date.now() - 86400000 * 8).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 8).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: null,
      has_action_required: false,
      match_score: 88,
      fit_score: 88,
      programmatic_match_score: 87,
      description: "### Role Overview\nFigma's Multiplayer Engine powers real-time collaboration for millions of designers simultaneously. Join us to scale C++/Rust server workers, low-latency WebSocket clusters, and memory-efficient document stores.",
      match_analysis_payload: {
        match_score: 88,
        fit_score: 88,
        key_strengths: [
          "Deep systems programming skill set",
          "Experience with micro-second latency optimizations"
        ],
        gaps: ["C++ desktop runtime memory alignment"],
        gap_closing_tips: ["Emphasize cross-compilation and native module profiling experience."]
      },
      events: [
        {
          id: "evt_figma_1",
          application_id: "app_figma_003",
          event_type: "APPLICATION_SUBMITTED",
          title: "Submitted Online Application",
          description: "Submitted application via referral link.",
          created_at: new Date(Date.now() - 86400000 * 8).toISOString(),
          raw_payload: {}
        }
      ]
    },
    {
      id: "app_datacamp_004",
      company_id: "comp_datacamp",
      company_name: "Datadog",
      position: "Senior Lead Engineer - Telemetry Pipeline",
      status: "ONLINE_ASSESSMENT",
      location: "New York, NY (Remote)",
      work_model: "Remote",
      salary_min: 210000,
      salary_max: 250000,
      currency: "USD",
      url: "https://datadoghq.com/careers/lead-telemetry",
      application_date: new Date(Date.now() - 86400000 * 12).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 3).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: new Date(Date.now() + 86400000 * 1).toISOString(),
      has_action_required: true,
      match_score: 85,
      fit_score: 85,
      programmatic_match_score: 84,
      description: "### Role Summary\nLead engineer responsible for processing petabyte-scale metric, trace, and log telemetry ingestion. You will optimize Vector/FluentBit aggregators and Kafka cluster backpressure.",
      match_analysis_payload: {
        match_score: 85,
        fit_score: 85,
        key_strengths: ["Kafka stream processing mastery", "Observability background"],
        gaps: ["eBPF kernel tracing"],
        gap_closing_tips: ["Review Linux kernel eBPF packet filter primitives."]
      },
      events: []
    },
    {
      id: "app_snowflake_005",
      company_id: "comp_snowflake",
      company_name: "Snowflake",
      position: "Principal Distributed Database Engineer",
      status: "REJECTED",
      location: "San Mateo, CA",
      work_model: "On-site",
      salary_min: 250000,
      salary_max: 310000,
      currency: "USD",
      url: "https://snowflake.com/careers/db-principal",
      application_date: new Date(Date.now() - 86400000 * 40).toISOString(),
      last_activity_at: new Date(Date.now() - 86400000 * 15).toISOString(),
      scheduled_interview_at: null,
      nearest_due_date: null,
      has_action_required: false,
      match_score: 79,
      fit_score: 79,
      programmatic_match_score: 78,
      description: "### Description\nFocus on query engine execution optimization and cloud storage caching layers.",
      match_analysis_payload: {
        match_score: 79,
        fit_score: 79,
        key_strengths: ["Database query processing concepts"],
        gaps: ["On-site location preference mismatch"],
        gap_closing_tips: ["N/A"]
      },
      events: []
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
      url: "https://stripe.com/jobs/staff-infra-engineer",
      company_name: "Stripe",
      position: "Staff Infrastructure Engineer - Core Platform",
      status: "COMPLETED",
      stage: "COMPLETED",
      progress: 100,
      match_score: 94,
      fit_score: 94,
      raw_text: "Stripe Staff Infrastructure Engineer core platform posting details...",
      error_message: null,
      created_at: new Date(Date.now() - 86400000 * 25).toISOString(),
      completed_at: new Date(Date.now() - 86400000 * 25).toISOString()
    },
    {
      id: "task_eval_102",
      url: "https://linear.app/careers/principal-backend",
      company_name: "Linear",
      position: "Principal Backend Engineer - Real-time Sync",
      status: "COMPLETED",
      stage: "COMPLETED",
      progress: 100,
      match_score: 91,
      fit_score: 91,
      raw_text: "Linear Principal Backend job spec details...",
      error_message: null,
      created_at: new Date(Date.now() - 86400000 * 18).toISOString(),
      completed_at: new Date(Date.now() - 86400000 * 18).toISOString()
    },
    {
      id: "task_eval_103",
      url: "https://private-career-portal.internal/job/9821",
      company_name: "Unknown Company",
      position: "Backend Developer",
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

  diagnostics_traces: [
    {
      id: "tr_001",
      run_id: "run_llm_eval_881",
      category: "llm",
      name: "evaluate_candidate_match",
      status: "success",
      latency_ms: 1240,
      start_time: new Date(Date.now() - 3600000 * 3).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 3 + 1240).toISOString(),
      metadata: { provider: "OpenAI", model: "gpt-4o", tokens_used: 1420 }
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
      metadata: { url: "https://linear.app/careers/principal-backend" }
    },
    {
      id: "tr_003",
      run_id: "run_worker_663",
      category: "worker",
      name: "generate_cover_letter_background",
      status: "success",
      latency_ms: 2150,
      start_time: new Date(Date.now() - 3600000 * 12).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 12 + 2150).toISOString(),
      metadata: { target_application: "app_stripe_001" }
    },
    {
      id: "tr_004",
      run_id: "run_email_554",
      category: "email_sync",
      name: "fetch_imap_unread_emails",
      status: "error",
      latency_ms: 310,
      start_time: new Date(Date.now() - 3600000 * 24).toISOString(),
      end_time: new Date(Date.now() - 3600000 * 24 + 310).toISOString(),
      error: "Client Demo Mode: IMAP Sync disabled",
      metadata: { mode: "demo" }
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
      metadata: { dimensions: 1536 }
    }
  ],

  system_settings: {
    has_completed_onboarding: true,
    enable_email_intake: false,
    enable_embeddings: true,
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
          score: 92,
          star_breakdown: { situation: true, task: true, action: true, result: true },
          feedback: "Outstanding STAR structure. Directly quantified latency improvements and technical architecture choices.",
          exemplar_rewrite: "I spearheaded the real-time sync overhaul, implementing state delta replication over WebSocket connection pools in Rust."
        }
      ],
      readiness_score: 92,
      summary_feedback: "Demonstrates exceptional technical mastery in real-time systems architecture and clear STAR communication.",
      created_at: new Date(Date.now() - 86400000 * 2).toISOString()
    }
  ],

  agent_chats: [
    {
      id: "chat_demo_1",
      title: "Preparation for Linear Technical Interview",
      created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
      messages: [
        {
          id: "msg_1",
          role: "user",
          content: "How should I structure my preparation for Linear's system design round?"
        },
        {
          id: "msg_2",
          role: "assistant",
          content: "For Linear, focus heavily on **Local-First Architecture**, **CRDT Data Structures**, and **WebSocket State Syncing**. Be prepared to detail how you handle offline optimistic updates and resolve concurrent state mutations."
        }
      ]
    }
  ]
}
