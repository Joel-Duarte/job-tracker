import Dexie from 'dexie'

export const db = new Dexie('JobTrackerLocalDB')

db.version(1).stores({
  applications: '++id, company_name, title, status, work_model, fit_score, created_at, updated_at',
  companies: '++id, &name',
  action_items: '++id, application_id, status, due_date, urgency, priority',
  candidate_profile: '++id, full_name',
  staging: '++id, company_name, status, created_at',
  diagnostics: '++id, category, status, created_at',
  interview_sessions: '++id, application_id, persona, status, created_at',
  email_accounts: '++id, email_address, provider',
  system_settings: '&key',
  ai_providers: '++id, provider_type, name, is_active',
  evaluations: '++id, status, stage, company_name, job_title, created_at'
})

export const MOCK_SEED_DATA = {
  candidate_profile: [
    {
      id: 1,
      full_name: 'Alex Mercer',
      email: 'alex.mercer@example.com',
      phone: '+1 (555) 234-5678',
      raw_text: `Alex Mercer - Staff Distributed Systems Engineer
Email: alex.mercer@example.com | Phone: +1 (555) 234-5678 | San Francisco, CA

SUMMARY
Staff Systems Engineer with 9+ years experience architecting high-throughput microservices, event-driven streaming platforms, and distributed storage engines using Go, Rust, Python, and Vue/TypeScript. Led multi-region infrastructure modernizations handling 50B+ daily requests with 99.999% uptime.

CORE COMPETENCIES
- Distributed Systems: Kafka, gRPC, Raft consensus, Redis, Postgres, Cassandra
- Cloud & Infrastructure: AWS, Kubernetes, Terraform, Docker, CI/CD pipelines
- Frontend & Full-Stack: Vue 3, TypeScript, Pinia, REST APIs, GraphQL
- Leadership: Technical Architecture, Mentorship, Cross-functional alignment

EXPERIENCE
Staff Engineer @ CloudScale Technologies (2021 - Present)
- Designed and built a multi-tenant event streaming platform in Go and Rust, reducing system latency by 45%.
- Authored internal RPC protocols and zero-downtime database migration tooling.

Senior Backend Engineer @ DataStream IO (2018 - 2021)
- Built streaming analytics pipeline processing 2M events/sec using Python, Kafka, and ClickHouse.
- Spearheaded migration from monolithic REST architecture to event-driven microservices.`,
      parsed_skills: ['Go', 'Rust', 'Python', 'Vue 3', 'TypeScript', 'Distributed Systems', 'Kafka', 'Kubernetes', 'PostgreSQL', 'gRPC'],
      target_roles: ['Staff Distributed Systems Engineer', 'Principal Infrastructure Engineer', 'Lead Systems Architect'],
      updated_at: new Date().toISOString()
    }
  ],
  applications: [
    {
      id: 1,
      company_name: 'Stripe',
      title: 'Staff Distributed Systems Engineer',
      location: 'San Francisco, CA (Hybrid)',
      work_model: 'Hybrid',
      salary_range: '$240,000 - $310,000',
      status: 'TECHNICAL_INTERVIEW',
      fit_score: 94,
      programmatic_match_score: 92,
      applied_date: new Date(Date.now() - 14 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 15 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
      url: 'https://stripe.com/jobs/staff-systems-engineer',
      description: 'Architect next-generation payment routing infrastructure with high throughput and low latency guarantees.',
      timeline_events: [
        { id: 101, event_type: 'INTAKE', title: 'Application Submitted', description: 'Applied via online portal', created_at: new Date(Date.now() - 14 * 86400000).toISOString() },
        { id: 102, event_type: 'RECRUITER_SCREEN', title: 'Recruiter Screen Completed', description: 'Positive feedback; scheduled technical deep-dive', created_at: new Date(Date.now() - 7 * 86400000).toISOString() },
        { id: 103, event_type: 'TECHNICAL_INTERVIEW', title: 'System Design Interview Scheduled', description: 'Scheduled for upcoming Thursday', created_at: new Date(Date.now() - 2 * 86400000).toISOString() }
      ],
      match_analysis_payload: {
        strengths: ['9+ years distributed systems experience matching criteria', 'Strong gRPC and streaming platform alignment', 'Proven track record of high-throughput design'],
        gaps: ['Requires minor ramp up on internal proprietary ledger protocol'],
        recommendations: ['Review distributed consensus (Raft/Paxos) trade-offs before technical round']
      },
      cover_letter_text: `Dear Hiring Team at Stripe,\n\nI am thrilled to apply for the Staff Distributed Systems Engineer position. With nearly a decade of experience designing fault-tolerant, high-throughput microservices and event streaming architectures, I am eager to contribute to Stripe's core payment infrastructure.\n\nBest regards,\nAlex Mercer`
    },
    {
      id: 2,
      company_name: 'Linear',
      title: 'Senior Full Stack Systems Engineer',
      location: 'Remote',
      work_model: 'Remote',
      salary_range: '$210,000 - $270,000',
      status: 'OFFER',
      fit_score: 96,
      programmatic_match_score: 95,
      applied_date: new Date(Date.now() - 25 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 26 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
      url: 'https://linear.app/careers/senior-fullstack-engineer',
      description: 'Build fast, offline-first collaborative product management software using Vue, TypeScript, and local sync engines.',
      timeline_events: [
        { id: 201, event_type: 'INTAKE', title: 'Application Submitted', description: 'Submitted custom tailored resume', created_at: new Date(Date.now() - 25 * 86400000).toISOString() },
        { id: 202, event_type: 'TECHNICAL_INTERVIEW', title: 'Pair Programming & Architecture Clear', description: 'Passed all technical rounds with high ratings', created_at: new Date(Date.now() - 5 * 86400000).toISOString() },
        { id: 203, event_type: 'OFFER', title: 'Written Offer Received', description: 'Received formal offer package', created_at: new Date(Date.now() - 1 * 86400000).toISOString() }
      ],
      match_analysis_payload: {
        strengths: ['Deep expertise in local-first sync engines and Vue 3', 'Exemplary code craft and performance optimization skills'],
        gaps: [],
        recommendations: ['Review stock options exercise terms and target compensation structure']
      }
    },
    {
      id: 3,
      company_name: 'Figma',
      title: 'Principal Performance Engineer',
      location: 'San Francisco, CA',
      work_model: 'On-site',
      salary_range: '$260,000 - $340,000',
      status: 'ONLINE_ASSESSMENT',
      fit_score: 88,
      programmatic_match_score: 85,
      applied_date: new Date(Date.now() - 6 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 7 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
      url: 'https://figma.com/careers/principal-performance',
      description: 'Optimize WebAssembly runtime execution and memory consumption for multi-player canvas rendering engine.',
      timeline_events: [
        { id: 301, event_type: 'INTAKE', title: 'Application Submitted', description: 'Applied via Figma careers site', created_at: new Date(Date.now() - 6 * 86400000).toISOString() },
        { id: 302, event_type: 'ONLINE_ASSESSMENT', title: 'OA Received', description: 'Algorithms and Memory Management OA due in 3 days', created_at: new Date(Date.now() - 3 * 86400000).toISOString() }
      ],
      match_analysis_payload: {
        strengths: ['C++/Rust and WebAssembly memory architecture experience', 'Strong low-level profiling skills'],
        gaps: ['Wasm rendering engine internals focus'],
        recommendations: ['Complete practice memory profiler assessment']
      }
    },
    {
      id: 4,
      company_name: 'Datadog',
      title: 'Staff Infrastructure Platform Engineer',
      location: 'New York, NY (Hybrid)',
      work_model: 'Hybrid',
      salary_range: '$230,000 - $295,000',
      status: 'APPLIED',
      fit_score: 91,
      programmatic_match_score: 89,
      applied_date: new Date(Date.now() - 4 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 4 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 4 * 86400000).toISOString(),
      url: 'https://datadoghq.com/careers/staff-infra',
      description: 'Scale telemetry data collection pipelines handling millions of telemetry points per second.',
      timeline_events: [
        { id: 401, event_type: 'INTAKE', title: 'Application Submitted', description: 'Application submitted', created_at: new Date(Date.now() - 4 * 86400000).toISOString() }
      ],
      match_analysis_payload: {
        strengths: ['Proven experience with high throughput telemetry processing', 'Deep Kubernetes and Golang background'],
        gaps: [],
        recommendations: []
      }
    },
    {
      id: 5,
      company_name: 'Vercel',
      title: 'Lead Edge Compute Architect',
      location: 'Remote',
      work_model: 'Remote',
      salary_range: '$220,000 - $280,000',
      status: 'HIRED',
      fit_score: 98,
      programmatic_match_score: 97,
      applied_date: new Date(Date.now() - 60 * 86400000).toISOString(),
      created_at: new Date(Date.now() - 60 * 86400000).toISOString(),
      updated_at: new Date(Date.now() - 30 * 86400000).toISOString(),
      url: 'https://vercel.com/careers/edge-architect',
      description: 'Lead architecture of global edge middleware routing and serverless function execution infrastructure.',
      timeline_events: [
        { id: 501, event_type: 'INTAKE', title: 'Application Submitted', description: 'Applied online', created_at: new Date(Date.now() - 60 * 86400000).toISOString() },
        { id: 502, event_type: 'OFFER', title: 'Offer Accepted', description: 'Accepted offer for Lead Edge Compute Architect', created_at: new Date(Date.now() - 30 * 86400000).toISOString() }
      ],
      match_analysis_payload: {
        strengths: ['World-class edge networking and runtime execution experience'],
        gaps: [],
        recommendations: []
      }
    }
  ],
  action_items: [
    {
      id: 1,
      application_id: 1,
      company_name: 'Stripe',
      title: 'Prepare Distributed Consensus & System Design prep notes',
      status: 'PENDING',
      due_date: new Date(Date.now() + 2 * 86400000).toISOString(),
      urgency: 'HIGH',
      priority: 'HIGH',
      notes: 'Review Raft leader election, consensus edge cases, and idempotency guarantees.'
    },
    {
      id: 2,
      application_id: 3,
      company_name: 'Figma',
      title: 'Complete Online Assessment on Memory Management',
      status: 'PENDING',
      due_date: new Date(Date.now() + 1 * 86400000).toISOString(),
      urgency: 'HIGH',
      priority: 'URGENT',
      notes: 'Focus on C++/Rust memory profiling and Wasm bindings.'
    },
    {
      id: 3,
      application_id: 2,
      company_name: 'Linear',
      title: 'Review offer compensation package and negotiate equity terms',
      status: 'COMPLETED',
      due_date: new Date(Date.now() - 1 * 86400000).toISOString(),
      urgency: 'MEDIUM',
      priority: 'MEDIUM',
      notes: 'Confirmed equity vesting schedule and signing bonus.'
    }
  ],
  staging: [
    {
      id: 1,
      source: 'EMAIL',
      company_name: 'Datadog',
      sender: 'recruiting@datadoghq.com',
      subject: 'Application Received: Staff Infrastructure Platform Engineer',
      raw_text: 'Thank you for submitting your application to Datadog. Our engineering team is reviewing your profile.',
      status: 'UNRESOLVED',
      created_at: new Date(Date.now() - 3 * 86400000).toISOString()
    }
  ],
  diagnostics: [
    {
      id: 1,
      category: 'LOCAL_MODE',
      status: 'SUCCESS',
      message: 'Local IndexedDB storage adapter initialized successfully with demo seeds.',
      created_at: new Date().toISOString()
    },
    {
      id: 2,
      category: 'BYOK_AI',
      status: 'INFO',
      message: 'Client-first BYOK AI client registered. Ready for browser direct inference.',
      created_at: new Date().toISOString()
    }
  ],
  system_settings: [
    { key: 'STORAGE_MODE', value: 'demo' },
    { key: 'ENABLE_AUTO_COVER_LETTER', value: true },
    { key: 'COVER_LETTER_MATCH_THRESHOLD', value: 70 },
    { key: 'COVER_LETTER_LENGTH', value: 'standard' },
    { key: 'ENABLE_EMAIL_INTAKE', value: false }
  ],
  ai_providers: [
    {
      id: 1,
      name: 'Ollama (Local)',
      provider_type: 'ollama',
      base_url: 'http://localhost:11434',
      api_key: '',
      is_active: true,
      is_fallback: false
    },
    {
      id: 2,
      name: 'LM Studio (Local)',
      provider_type: 'lm_studio',
      base_url: 'http://localhost:1234/v1',
      api_key: '',
      is_active: false,
      is_fallback: true
    }
  ]
}

export async function initAndSeedDatabase(forceReset = false) {
  if (forceReset) {
    await db.transaction('rw', db.tables, async () => {
      for (const table of db.tables) {
        await table.clear()
      }
    })
  }

  const appCount = await db.applications.count()
  if (appCount === 0 || forceReset) {
    await db.transaction('rw', db.tables, async () => {
      for (const [tableName, records] of Object.entries(MOCK_SEED_DATA)) {
        if (db[tableName]) {
          await db[tableName].bulkAdd(records)
        }
      }
    })
    console.log('[IndexedDB] Local database seeded with mock dataset successfully.')
  }
}

export async function exportLocalDatabaseJSON() {
  const exportData = {}
  for (const table of db.tables) {
    exportData[table.name] = await table.toArray()
  }
  return JSON.stringify(exportData, null, 2)
}

export async function importLocalDatabaseJSON(jsonString) {
  const data = JSON.parse(jsonString)
  await db.transaction('rw', db.tables, async () => {
    for (const table of db.tables) {
      if (data[table.name]) {
        await table.clear()
        await table.bulkAdd(data[table.name])
      }
    }
  })
}
