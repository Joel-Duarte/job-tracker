# AI Agent Tools Specification

This document provides a comprehensive blueprint and specification of the AI agent tools designed for the Job Tracker system. Based on the backend architecture, database schemas, and service capabilities, these tools allow LLM-driven agents to inspect recruitment funnels, identify stalled applications, evaluate skill alignment, manage background queue operations, query market benchmarks, and track action items.

---

## Overview of Recommended AI Agent Tools

| Tool Name | Core Purpose | Primary Domain |
|---|---|---|
| `analyze_pipeline_metrics` | Cohort funnel conversion, dropoff rates, and KPI trend analysis | Analytics & Funnel |
| `detect_stalled_applications` | Stale application identification and follow-up tracking | Pipeline Management |
| `query_market_benchmarks` | Skill demand, compensation ranges, and market distribution | Market Intelligence |
| `evaluate_ai_fit_score` | Detailed match analysis, skill gaps, and AI match scoring | Job & Candidate Match |
| `manage_intake_queue` | Background task queue monitoring, retry, and cancellation | Queue & Background Operations |
| `manage_action_items` | High-urgency action item tracking and task resolution | Tasks & Deadlines |
| `semantic_vector_search` | Vector cosine similarity search across applications and email logs | Semantic Search |
| `update_application_pipeline` | Pipeline status transition and timeline event creation | Application Lifecycle |

---

### analyze_pipeline_metrics

#### Description
Evaluates recruitment conversion funnel performance across defined cohort periods (weekly or monthly). Computes stage counts (Intake Leads $\rightarrow$ Applications $\rightarrow$ Interviews $\rightarrow$ Offers), conversion and dropoff percentages, and period-over-period KPI trend deltas.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AnalyzePipelineMetricsInput",
  "type": "object",
  "properties": {
    "period": {
      "type": "string",
      "enum": ["weekly", "monthly"],
      "default": "weekly",
      "description": "Aggregation period granularity for cohort calculation."
    },
    "num_periods": {
      "type": "integer",
      "minimum": 1,
      "maximum": 24,
      "default": 8,
      "description": "Number of historical periods to include in cohort trend analysis."
    }
  },
  "required": []
}
```

#### Output Structure
```json
{
  "period_type": "weekly",
  "summary_kpis": {
    "intakes": {
      "label": "Total Intake Leads",
      "value": 14,
      "trend_percentage": 16.7,
      "is_positive": true
    },
    "applications": {
      "label": "Submitted Applications",
      "value": 10,
      "trend_percentage": 25.0,
      "is_positive": true
    },
    "interviews": {
      "label": "Interview Conversions",
      "value": 3,
      "trend_percentage": -10.0,
      "is_positive": false
    },
    "offers": {
      "label": "Offers Received",
      "value": 1,
      "trend_percentage": 0.0,
      "is_positive": true
    }
  },
  "cohort_data": [
    {
      "period_key": "2025-W08",
      "period_label": "W08 (Feb 17)",
      "start_date": "2025-02-17",
      "end_date": "2025-02-23",
      "intakes": 14,
      "applications": 10,
      "interviews": 3,
      "offers": 1,
      "conversion_rate": 30.0,
      "stages": [
        { "stage": "Intake", "count": 14 },
        { "stage": "Applications", "count": 10 },
        { "stage": "Interviews", "count": 3 },
        { "stage": "Offers", "count": 1 }
      ]
    }
  ]
}
```

#### Use Case
Executed when the candidate asks "How is my application funnel performing this month?" or "What is my interview conversion rate compared to last week?"

---

### detect_stalled_applications

#### Description
Scans active job applications that have remained in a specific pipeline status without recent activity, email events, or status updates for more than a specified threshold of days. Identifies stalled applications requiring follow-ups or status archiving.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "DetectStalledApplicationsInput",
  "type": "object",
  "properties": {
    "stale_days_threshold": {
      "type": "integer",
      "minimum": 1,
      "default": 14,
      "description": "Minimum number of inactive days before an application is flagged as stalled."
    },
    "status_filter": {
      "type": "string",
      "enum": ["APPLIED", "TECHNICAL_INTERVIEW", "ASSESSMENT", "ALL"],
      "default": "ALL",
      "description": "Optional filter for target application status."
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "default": 20,
      "description": "Maximum number of stalled applications to return."
    }
  },
  "required": []
}
```

#### Output Structure
```json
{
  "total_stalled": 2,
  "threshold_days": 14,
  "stalled_applications": [
    {
      "application_id": 42,
      "company": "Acme Corp",
      "position": "Senior Backend Engineer",
      "status": "APPLIED",
      "days_inactive": 18,
      "last_activity_at": "2025-02-05T10:15:00Z",
      "last_event_summary": "Application submitted via company portal.",
      "recommended_action": "Send follow-up email to recruiter or archive if ghosted."
    }
  ]
}
```

#### Use Case
Used when the user asks "Which applications haven't responded in over two weeks?" or during automated weekly maintenance audits to flag potential ghosting.

---

### query_market_benchmarks

#### Description
Queries market intelligence aggregated across stored job descriptions and candidate CV profiles. Analyzes overall top in-demand skills, priority skill gaps specific to the candidate, work model distribution (remote, hybrid, onsite), and average compensation bounds.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "QueryMarketBenchmarksInput",
  "type": "object",
  "properties": {
    "days_limit": {
      "type": "integer",
      "minimum": 1,
      "description": "Restrict market analysis to job postings created in the last N days."
    },
    "work_model": {
      "type": "string",
      "enum": ["all", "remote", "hybrid", "onsite"],
      "default": "all",
      "description": "Filter benchmark analysis by workplace model."
    },
    "top_n_skills": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "default": 10,
      "description": "Number of top skills and skill gaps to extract."
    }
  },
  "required": []
}
```

#### Output Structure
```json
{
  "total_jobs_analyzed": 45,
  "top_in_demand_skills": [
    {
      "skill": "Python",
      "count": 38,
      "percentage": 84.4,
      "avg_salary_min": 130000.0,
      "avg_salary_max": 175000.0,
      "is_in_candidate_cv": true
    },
    {
      "skill": "Kubernetes",
      "count": 22,
      "percentage": 48.9,
      "avg_salary_min": 140000.0,
      "avg_salary_max": 190000.0,
      "is_in_candidate_cv": false
    }
  ],
  "priority_skill_gaps": [
    {
      "skill": "Kubernetes",
      "missing_frequency": 22,
      "target_job_count": 22,
      "priority_score": 52.8,
      "sample_companies": ["CloudTech", "DataData", "StreamInc"]
    }
  ],
  "work_model_distribution": {
    "remote_count": 28,
    "hybrid_count": 12,
    "onsite_count": 5,
    "unknown_count": 0
  }
}
```

#### Use Case
Triggered when the candidate asks "What technical skills are most in-demand for remote roles?" or "Which missing skills should I learn to increase my salary potential?"

---

### evaluate_ai_fit_score

#### Description
Retrieves and evaluates the qualitative AI fit score (`fit_score`), programmatic match score (`programmatic_match_score`), matching skills list, missing skill gaps, and match breakdown for a specific application or newly evaluated job posting.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EvaluateAIFitScoreInput",
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Numeric Application ID to fetch fit evaluation for."
    },
    "company_name": {
      "type": "string",
      "description": "Company name to search and evaluate if ID is unknown."
    }
  },
  "required": []
}
```

#### Output Structure
```json
{
  "application_id": 12,
  "company": "Stripe",
  "position": "Backend Staff Engineer",
  "qualitative_fit_score": 88.5,
  "programmatic_match_score": 85.0,
  "fit_tier": "ELITE",
  "matching_skills": ["Python", "FastAPI", "PostgreSQL", "System Design"],
  "missing_skills": ["Go", "Distributed Consensus"],
  "match_analysis": {
    "seniority_fit": "Strong match (7+ years required)",
    "key_strengths": "Deep API design experience, microservices architecture",
    "potential_concerns": "Role prefers Go experience; candidate background is primary Python"
  }
}
```

#### Use Case
Used when the user asks "How well do I fit the Stripe Staff Engineer role?" or "Why did I get an 88% fit score for this application?"

---

### manage_intake_queue

#### Description
Monitors, manages, and executes operational actions on the background AI evaluation queue (`IntakeEvaluationTaskModel`). Supports listing task status, retrying failed intake/cover letter tasks, canceling active jobs, or triggering JD fixes for failed scrapes.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ManageIntakeQueueInput",
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["list", "retry", "cancel", "fix_jd"],
      "description": "Operational action to perform on the background queue."
    },
    "task_id": {
      "type": "integer",
      "description": "Specific Task ID required for retry, cancel, or fix_jd actions."
    },
    "status_filter": {
      "type": "string",
      "enum": ["PENDING", "PROCESSING", "COMPLETED", "FAILED", "ALL"],
      "default": "ALL",
      "description": "Optional filter when listing tasks."
    },
    "raw_text_override": {
      "type": "string",
      "description": "Manual job description raw text supplied when action is 'fix_jd'."
    }
  },
  "required": ["action"]
}
```

#### Output Structure
```json
{
  "action": "retry",
  "success": true,
  "task": {
    "id": 104,
    "task_type": "EVALUATION",
    "status": "PENDING",
    "stage": "FETCHING",
    "url": "https://example.com/careers/job/123",
    "error_message": null,
    "created_at": "2025-02-23T14:20:00Z"
  },
  "message": "Task #104 successfully re-queued for processing."
}
```

#### Use Case
Called when the user asks "Why did my job intake fail?" or requests "Retry processing the cover letter generation task for job #104."

---

### manage_action_items

#### Description
Retrieves, creates, or updates candidate action items (`ActionItemModel`), upcoming deadlines, interview preparations, and draft responses. Filters by urgency level or application context.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ManageActionItemsInput",
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["list", "complete", "dismiss"],
      "default": "list",
      "description": "Action to perform on action items."
    },
    "action_item_id": {
      "type": "integer",
      "description": "Specific action item ID to update (required for complete/dismiss)."
    },
    "urgency": {
      "type": "string",
      "enum": ["HIGH", "MEDIUM", "LOW"],
      "description": "Optional filter for task urgency level."
    }
  },
  "required": []
}
```

#### Output Structure
```json
{
  "action": "list",
  "pending_count": 2,
  "action_items": [
    {
      "id": 15,
      "company": "Datadog",
      "title": "Schedule Technical Interview Stage 2",
      "due_date": "2025-02-25T17:00:00Z",
      "urgency": "HIGH",
      "status": "PENDING",
      "action_url": "https://calendly.com/datadog-recruiter/30min"
    }
  ]
}
```

#### Use Case
Executed when the candidate asks "What urgent tasks do I need to complete today?" or "Mark my Datadog scheduling action item as completed."

---

### semantic_vector_search

#### Description
Executes high-performance vector cosine similarity search using pgvector (768-dimensional embeddings) across stored recruiter emails, company interactions, and job specifications. Automatically falls back to keyword matching if vector embeddings are disabled.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SemanticVectorSearchInput",
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Natural language search query describing recruiter communications, job specs, or status details."
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 5,
      "description": "Maximum number of matching embedding documents to return."
    }
  },
  "required": ["query"]
}
```

#### Output Structure
```json
[
  {
    "application_id": 7,
    "company": "Linear",
    "position": "Frontend Engineer",
    "status": "TECHNICAL_INTERVIEW",
    "similarity_score": "92.4%",
    "document_content": "Recruiter email from Sarah: We would love to invite you to the system design round on Tuesday.",
    "metadata": {
      "source_type": "email_event",
      "event_id": 102
    }
  }
]
```

#### Use Case
Used when the user asks "Did Linear say anything about compensation in their last email?" or "Search my communications for mentions of system design interview prep."

---

### update_application_pipeline

#### Description
Transitions an application's pipeline status (APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, ASSESSMENT), creates a structured timeline event (`ApplicationEventModel`), and automatically enqueues vector embedding regeneration.

#### Parameters
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "UpdateApplicationPipelineInput",
  "type": "object",
  "properties": {
    "company_name": {
      "type": "string",
      "description": "Target company name whose application status is being updated."
    },
    "new_status": {
      "type": "string",
      "enum": ["APPLIED", "TECHNICAL_INTERVIEW", "OFFER", "REJECTED", "ASSESSMENT"],
      "description": "Canonical new status to set."
    },
    "notes": {
      "type": "string",
      "description": "Optional status change summary or explanation note."
    }
  },
  "required": ["company_name", "new_status"]
}
```

#### Output Structure
```json
{
  "success": true,
  "application_id": 12,
  "company": "Stripe",
  "old_status": "APPLIED",
  "new_status": "TECHNICAL_INTERVIEW",
  "message": "Successfully transitioned Stripe application from APPLIED to TECHNICAL_INTERVIEW.",
  "embedding_updated": true
}
```

#### Use Case
Executed when the candidate says "Move my Stripe application to Technical Interview" or "Update Figma status to Rejected after receiving their email."
