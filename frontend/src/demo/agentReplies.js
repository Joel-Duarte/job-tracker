const ACTIVE_STATUSES = ['APPLIED', 'ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW', 'OFFER']

export const DEMO_AGENT_CAPABILITIES = `These capabilities are simulated in demo mode using your saved sample data:

**Application & Pipeline Management**
- View applications, stages, fit scores, and pending action items.
- Inspect pipeline metrics and stalled applications.
- Try status changes and bulk transitions from the Applications board.

**Interview Tracking**
- Check upcoming interviews and applications awaiting scheduling.
- Practice with different interviewer personas and question formats in Live Mock Interview Simulator.
- Review mock interview history and scorecards.

**Company Intelligence**
- Look up company dossiers, ratings, notes, pros, and red flags.
- Try company research and notes in the Companies directory.
- Explore simulated web research without contacting external services.

**Application Documents**
- Retrieve cover letters, application questions, and interview guides.
- Try queued cover letter and application answer generation from an application.

**Candidate Profile & Career Development**
- Review your verified CV, skills, experience, and role alignment dossiers.
- Search applications and explore career roadmaps in Analytics.

**Market Benchmarks**
- Explore sample salary benchmarks and in-demand skills in Analytics.

Try “Summarize my active pipeline”, “Show my deadlines”, “Tell me about Stripe”, or “Show my cover letter for Stripe”.`

function formatPipelineApplication(app) {
  const parts = [`- **${app.company_name}** — ${app.position}: ${app.status.replaceAll('_', ' ')}`]
  if (app.status === 'TECHNICAL_INTERVIEW') {
    parts.push(app.scheduled_interview_at ? `interview ${new Date(app.scheduled_interview_at).toLocaleString()}` : 'awaiting scheduling')
  }
  if (app.nearest_due_date) parts.push(`deadline ${new Date(app.nearest_due_date).toLocaleString()}`)
  return parts.join(', ')
}

function pipelineReply(db, app) {
  const matches = (db.applications || []).filter(a => ACTIVE_STATUSES.includes(a.status) && (!app || a.id === app.id))
  return `**Active pipeline**\n\n${matches.map(formatPipelineApplication).join('\n') || 'No active applications.'}`
}

function documentReply(app, field, missing) {
  if (!app) return 'Name a company, for example “Show my cover letter for Stripe”.'
  return app[field] || `No ${missing} saved for ${app.company_name}. Open the application to generate a demo document.`
}

function questionsReply(app) {
  if (!app) return 'Name the company whose application answers you want to review.'
  return (app.application_questions || []).map(q => `**${q.question}**\n${q.answer}`).join('\n\n') || `No answers saved for ${app.company_name}. Open the application to generate demo answers.`
}

function historyReply(db) {
  return (db.interview_sessions || []).map(s => `- **${s.company_name}**: ${s.status}, score ${s.overall_score ?? s.readiness_score ?? 'pending'}. ${s.summary_feedback || ''}`).join('\n') || 'No practice sessions saved yet.'
}

function companyReply(db, app) {
  if (!app) return 'Name a tracked company, for example “Tell me about Stripe”.'
  const company = (db.companies || []).find(c => c.name === app.company_name)
  return `**${app.company_name} — Company Intelligence**\n\n${company?.company_research?.summary || 'Open Companies to explore the sample research dossier.'}\n\n${company?.notes || ''}`
}

function deadlinesReply(db) {
  const pending = (db.action_items || []).filter(t => t.status === 'PENDING')
  return `**Pending action items**\n\n${pending.map(t => `- ${t.title}: ${t.due_date ? new Date(t.due_date).toLocaleString() : 'No deadline set'}`).join('\n') || 'No pending tasks.'}`
}

const REPLY_ROUTES = [
  [/\btools?\b|what can you|can you do|capabilities/, () => DEMO_AGENT_CAPABILITIES],
  [/cover letter/, (_db, app) => documentReply(app, 'cover_letter_text', 'cover letter')],
  [/interview guide/, (_db, app) => documentReply(app, 'interview_guide_markdown', 'interview guide')],
  [/application questions|application answers|q&a/, (_db, app) => questionsReply(app)],
  [/profile|my skills|my cv|resume/, db => db.candidate_profile?.raw_text || 'No candidate profile saved.'],
  [/history|scorecard/, historyReply],
  [/company|research|tell me about/, companyReply],
  [/deadline|action item|pending task/, deadlinesReply],
  [/pipeline|applications|interview/, pipelineReply],
]

export function getDemoAgentReply(db, message) {
  const query = message.toLowerCase()
  const app = (db.applications || []).find(a => a.company_name && query.includes(a.company_name.toLowerCase()))
  const route = REPLY_ROUTES.find(([pattern]) => pattern.test(query))
  if (route) return route[1](db, app)
  return 'This is a simulated demo assistant. Try asking about your active pipeline, deadlines, candidate profile, company intelligence, cover letters, application answers, or mock interview history. Use the app controls to try generation and status changes.'
}
