import { getDemoAgentReply } from './agentReplies.js'
import { getDemoQualityStats } from './qualityAudits.js'
import { getDemoDb, saveDemoDb } from './demoStorage.js'
import { scoreApplicationMatch, normalizeCompanyText } from '../utils/fuzzyMatch.js'
import { DEFAULT_DIAGRAM_BLOCKS, DEFAULT_DIAGRAM_CATEGORIES } from '../utils/diagramCatalog.js'

function filterDemoTraces(traces, params) {
  return traces.filter(t =>
    (!params.category || params.category === 'all' || t.category === params.category) &&
    (!params.status || params.status === 'all' || t.status === params.status) &&
    (!(params.errors_only === true || params.errors_only === 'true') || t.status === 'error')
  ).slice(0, params.limit || 100)
}

function delay(ms = null) {
  const actualMs = ms !== null ? ms : Math.floor(Math.random() * 500) + 500
  return new Promise((resolve) => setTimeout(resolve, actualMs))
}

function getDefaultDemoSystemDesignChallenges() {
  const nowIso = new Date().toISOString()
  return [
    {
      id: 1,
      slug: 'url-shortener',
      title: 'Design a URL Shortener',
      category: 'DISTRIBUTED_SYSTEMS',
      difficulty: 'EASY',
      prompt_summary:
        'Build a service that creates short, shareable aliases for long URLs and redirects users reliably with low latency.',
      initial_prompt:
        "We need to design a URL shortening service like bit.ly or TinyURL. Users should be able to generate short links for arbitrary long URLs and be redirected when visiting a short link. Let's start with requirements discovery: what clarifying questions do you have about scale, features, and constraints?",
      tags: ['hashing', 'caching', 'key-generation', 'redirects', 'read-heavy'],
      is_builtin: true,
      created_at: nowIso,
    },
    {
      id: 2,
      slug: 'spotify-100k',
      title: 'Design Spotify for 100,000 Users',
      category: 'MEDIA_STREAMING',
      difficulty: 'MEDIUM',
      prompt_summary:
        'Design an audio streaming platform sized intentionally for 100,000 registered users with playlists, search, and offline/online playback.',
      initial_prompt:
        'Design a music streaming service similar to Spotify, scoped specifically to support 100,000 total registered users. Before jumping into architecture, what questions would you like to ask to clarify the workload, catalog size, features, and constraints?',
      tags: ['right-sizing', 'audio-streaming', 'cdn', 'object-storage', 'yagni'],
      is_builtin: true,
      created_at: nowIso,
    },
    {
      id: 3,
      slug: 'realtime-notifications',
      title: 'Design a Real-Time Notification System',
      category: 'EVENT_DRIVEN',
      difficulty: 'MEDIUM',
      prompt_summary:
        'Design a multi-channel notification platform delivering push, email, SMS, and in-app alerts reliably across millions of events.',
      initial_prompt:
        'We need a scalable real-time notification system capable of delivering user alerts across in-app real-time feeds, mobile push (APNs/FCM), email, and SMS. Ask clarifying questions to lock down scale, delivery guarantees, and product scope.',
      tags: ['pub-sub', 'websockets', 'queues', 'idempotency', 'fan-out'],
      is_builtin: true,
      created_at: nowIso,
    },
    {
      id: 4,
      slug: 'ride-sharing',
      title: 'Design a Ride-Sharing Platform',
      category: 'GEOSPATIAL',
      difficulty: 'HARD',
      prompt_summary:
        'Design a real-time rider-driver matching, location tracking, and trip dispatch backend similar to Uber or Lyft.',
      initial_prompt:
        'Design the core backend of a ride-sharing platform that tracks driver locations continuously, matches nearby drivers with riders, and manages trip state transitions. What questions would you like to ask to define the scope and scale?',
      tags: ['geospatial', 'geohash', 'h3', 'matching', 'state-machine'],
      is_builtin: true,
      created_at: nowIso,
    },
    {
      id: 5,
      slug: 'distributed-job-queue',
      title: 'Design a Distributed Job Processing System',
      category: 'INFRASTRUCTURE',
      difficulty: 'MEDIUM',
      prompt_summary:
        'Design a reliable multi-tenant background task execution platform supporting delayed jobs, retries, concurrency limits, and worker heartbeats.',
      initial_prompt:
        "Design a distributed job queue and task execution platform (similar to Celery, Temporal queues, or AWS SQS + workers). Clients submit background jobs and expect reliable execution. Let's clarify requirements and failure constraints before you design.",
      tags: ['queues', 'visibility-timeout', 'dlq', 'scheduling', 'idempotency'],
      is_builtin: true,
      created_at: nowIso,
    },
    {
      id: 6,
      slug: 'video-streaming',
      title: 'Design a Video Streaming Platform',
      category: 'MEDIA_STREAMING',
      difficulty: 'HARD',
      prompt_summary:
        'Design a scalable video upload, transcoding DAG pipeline, metadata service, and adaptive bitrate playback architecture like YouTube.',
      initial_prompt:
        'Design a video sharing and streaming platform where creators upload videos and viewers stream them smoothly worldwide on varied network connections. Ask clarifying questions to narrow down scope, scale, and constraints.',
      tags: ['hls', 'dash', 'transcoding', 'cdn', 'dag-pipeline'],
      is_builtin: true,
      created_at: nowIso,
    },
    {
      id: 7,
      slug: 'chat-system',
      title: 'Design a Real-Time Chat System',
      category: 'REALTIME_MESSAGING',
      difficulty: 'MEDIUM',
      prompt_summary:
        'Design a 1:1 and group messaging application with online presence, message ordering, read receipts, and multi-device sync.',
      initial_prompt:
        'Design a real-time chat system like WhatsApp or Slack supporting 1-on-1 conversations, group chats, online/offline presence indicators, and multi-device message history sync. What clarifying questions do you have?',
      tags: ['websockets', 'ordering', 'presence', 'fan-out', 'cassandra'],
      is_builtin: true,
      created_at: nowIso,
    },
    {
      id: 8,
      slug: 'rate-limiter',
      title: 'Design a Distributed API Rate Limiter',
      category: 'INFRASTRUCTURE',
      difficulty: 'MEDIUM',
      prompt_summary:
        'Design a low-latency distributed rate limiting layer protecting public APIs from abuse, traffic spikes, and noisy tenants.',
      initial_prompt:
        'Design a distributed API rate limiter to protect an enterprise SaaS API gateway from abuse, accidental client loops, and traffic spikes while adding minimal latency. What clarifying questions should we resolve first?',
      tags: ['token-bucket', 'sliding-window', 'redis-lua', 'api-gateway', 'fail-open'],
      is_builtin: true,
      created_at: nowIso,
    },
  ]
}

function ensureDemoSystemDesignData(db) {
  if (!Array.isArray(db.system_design_challenges)) {
    db.system_design_challenges = getDefaultDemoSystemDesignChallenges()
  }
  if (!Array.isArray(db.system_design_sessions)) {
    db.system_design_sessions = []
  }
}

async function readDemoFileAsDataUrl(fileObj) {
  const fallbackSvg =
    'data:image/svg+xml;utf8,' +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320" viewBox="0 0 640 320"><rect width="640" height="320" fill="#1e293b"/><rect x="40" y="110" width="140" height="70" rx="8" fill="#334155" stroke="#60a5fa"/><text x="110" y="150" fill="#f8fafc" font-size="14" text-anchor="middle">API Gateway</text><rect x="250" y="110" width="140" height="70" rx="8" fill="#334155" stroke="#34d399"/><text x="320" y="150" fill="#f8fafc" font-size="14" text-anchor="middle">App Service</text><rect x="460" y="110" width="140" height="70" rx="8" fill="#334155" stroke="#fbbf24"/><text x="530" y="150" fill="#f8fafc" font-size="14" text-anchor="middle">Primary DB</text></svg>'
    )
  if (!fileObj || typeof FileReader === 'undefined') {
    return fallbackSvg
  }
  try {
    return await new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || fallbackSvg))
      reader.onerror = () => resolve(fallbackSvg)
      reader.readAsDataURL(fileObj)
    })
  } catch {
    return fallbackSvg
  }
}

export async function handleDemoRequest(config) {
  const method = (config.method || 'get').toLowerCase()
  const rawUrl = config.url || ''
  // Strip query parameters for endpoint matching
  const urlPath = rawUrl.split('?')[0].replace(/\/$/, '')
  const params = config.params || {}
  const data = typeof config.data === 'string' ? JSON.parse(config.data || '{}') : (config.data || {})

  // Simulate artificial delay (500ms - 1000ms by default, 1500ms for job intake extraction)
  let delayMs = 500
  if (urlPath.includes('/intake/paste') || urlPath.includes('/intake/assess-job') || urlPath.includes('/intake/upload')) {
    delayMs = 1500
  }
  await delay(delayMs)
  const db = getDemoDb()

  // Response helper
  const ok = (responseData, status = 200) => ({
    data: responseData,
    status,
    statusText: 'OK',
    headers: {},
    config,
  })

  // 1. APPLICATIONS ENDPOINTS
  if (urlPath === '/applications/stage-counts' && method === 'get') {
    let items = [...(db.applications || [])]
    if (params.q) {
      const q = params.q.toLowerCase().trim()
      items = items.filter(
        (a) =>
          a.company_name?.toLowerCase().includes(q) ||
          a.company?.name?.toLowerCase().includes(q) ||
          a.position?.toLowerCase().includes(q) ||
          a.location?.toLowerCase().includes(q)
      )
    }
    if (params.work_model) {
      const wm = params.work_model.toLowerCase().replace(/[^a-z]/g, '')
      items = items.filter((a) => {
        const cur = (a.work_model || a.job_posting?.work_model || '').toLowerCase().replace(/[^a-z]/g, '')
        return cur.includes(wm) || wm.includes(cur)
      })
    }
    if (params.action_required !== undefined) {
      const req = params.action_required === true || params.action_required === 'true'
      items = items.filter((a) => Boolean(a.has_action_required) === req)
    }
    if (params.start_date) {
      const startMs = new Date(params.start_date).getTime()
      items = items.filter((a) => {
        const d = a.last_activity_at || a.application_date || a.created_at
        return d && new Date(d).getTime() >= startMs
      })
    }
    if (params.end_date) {
      const endMs = new Date(params.end_date).getTime()
      items = items.filter((a) => {
        const d = a.last_activity_at || a.application_date || a.created_at
        return d && new Date(d).getTime() <= endMs
      })
    }
    const counts = {
      APPLIED: 0,
      TECHNICAL_INTERVIEW: 0,
      OFFER: 0,
      ARCHIVED: 0,
      HIRED: 0,
    }
    const STAGE_MAP = {
      APPLIED: ['APPLIED', 'RECRUITER_CONTACT', 'IN_PROGRESS', 'PENDING'],
      TECHNICAL_INTERVIEW: [
        'TECHNICAL_INTERVIEW',
        'PHONE_SCREEN',
        'ONLINE_ASSESSMENT',
        'BEHAVIORAL_INTERVIEW',
        'ONSITE_INTERVIEW',
        'FINAL_INTERVIEW',
        'INTERVIEW',
        'SCREENING',
      ],
      OFFER: ['OFFER'],
      ARCHIVED: ['ARCHIVED', 'WITHDRAWN', 'REJECTED'],
      HIRED: ['HIRED'],
    }
    items.forEach((a) => {
      const st = (a.status || '').toUpperCase()
      if (STAGE_MAP.APPLIED.includes(st)) counts.APPLIED++
      else if (STAGE_MAP.TECHNICAL_INTERVIEW.includes(st)) counts.TECHNICAL_INTERVIEW++
      else if (STAGE_MAP.OFFER.includes(st)) counts.OFFER++
      else if (STAGE_MAP.ARCHIVED.includes(st)) counts.ARCHIVED++
      else if (STAGE_MAP.HIRED.includes(st)) counts.HIRED++
    })
    const total_active = counts.APPLIED + counts.TECHNICAL_INTERVIEW + counts.OFFER

    const archive_counts = {
      all: counts.ARCHIVED,
      ghosted_post_applied: 0,
      ghosted_applied: 0,
      rejected: 0,
      withdrawn: 0,
    }
    const POST_APPLIED_STAGES = new Set(['ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW', 'OFFER'])
    items.forEach((a) => {
      const st = (a.status || '').toUpperCase()
      if (STAGE_MAP.ARCHIVED.includes(st)) {
        if (st === 'WITHDRAWN') {
          archive_counts.withdrawn++
        } else {
          const reason = (
            a.latest_event?.raw_payload?.archive_reason ||
            a.latest_event?.raw_payload?.rejection_reason ||
            a.rejection_reason ||
            ''
          ).toLowerCase()
          const isGhost = st === 'ARCHIVED' || reason.includes('ghost')
          if (isGhost) {
            const prior = (a.previous_status || a.latest_event?.raw_payload?.previous_status || '').toUpperCase()
            if (POST_APPLIED_STAGES.has(prior)) {
              archive_counts.ghosted_post_applied++
            } else {
              archive_counts.ghosted_applied++
            }
          } else {
            archive_counts.rejected++
          }
        }
      }
    })

    return ok({ counts, archive_counts, total_active })
  }

  if (urlPath === '/applications' && method === 'get') {
    let items = [...(db.applications || [])]
    if (params.q) {
      const q = params.q.toLowerCase().trim()
      items = items.filter(
        (a) =>
          a.company_name?.toLowerCase().includes(q) ||
          a.company?.name?.toLowerCase().includes(q) ||
          a.position?.toLowerCase().includes(q) ||
          a.location?.toLowerCase().includes(q)
      )
    }
    if (params.work_model) {
      const wm = params.work_model.toLowerCase().replace(/[^a-z]/g, '')
      items = items.filter((a) => {
        const cur = (a.work_model || a.job_posting?.work_model || '').toLowerCase().replace(/[^a-z]/g, '')
        return cur.includes(wm) || wm.includes(cur)
      })
    }
    if (params.action_required !== undefined) {
      const req = params.action_required === true || params.action_required === 'true'
      items = items.filter((a) => Boolean(a.has_action_required) === req)
    }
    if (params.start_date) {
      const startMs = new Date(params.start_date).getTime()
      items = items.filter((a) => {
        const d = a.last_activity_at || a.application_date || a.created_at
        return d && new Date(d).getTime() >= startMs
      })
    }
    if (params.end_date) {
      const endMs = new Date(params.end_date).getTime()
      items = items.filter((a) => {
        const d = a.last_activity_at || a.application_date || a.created_at
        return d && new Date(d).getTime() <= endMs
      })
    }
    const STAGE_MAP = {
      APPLIED: ['APPLIED', 'RECRUITER_CONTACT', 'IN_PROGRESS', 'PENDING'],
      TECHNICAL_INTERVIEW: [
        'TECHNICAL_INTERVIEW',
        'PHONE_SCREEN',
        'ONLINE_ASSESSMENT',
        'BEHAVIORAL_INTERVIEW',
        'ONSITE_INTERVIEW',
        'FINAL_INTERVIEW',
        'INTERVIEW',
        'SCREENING',
      ],
      OFFER: ['OFFER'],
      ARCHIVED: ['ARCHIVED', 'WITHDRAWN', 'REJECTED'],
      HIRED: ['HIRED'],
    }
    if (params.status) {
      const stUpper = params.status.toUpperCase()
      if (STAGE_MAP[stUpper]) {
        items = items.filter((a) => STAGE_MAP[stUpper].includes((a.status || '').toUpperCase()))
      } else {
        items = items.filter((a) => (a.status || '').toUpperCase() === stUpper)
      }
    }
    if (params.archive_filter && params.archive_filter !== 'all') {
      const af = params.archive_filter.toLowerCase()
      const POST_APPLIED_STAGES = new Set(['ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW', 'OFFER'])
      items = items.filter((a) => {
        const st = (a.status || '').toUpperCase()
        if (af === 'withdrawn') return st === 'WITHDRAWN'
        if (st === 'WITHDRAWN') return false

        const reason = (
          a.latest_event?.raw_payload?.archive_reason ||
          a.latest_event?.raw_payload?.rejection_reason ||
          a.rejection_reason ||
          ''
        ).toLowerCase()
        const isGhost = st === 'ARCHIVED' || reason.includes('ghost')
        if (isGhost) {
          const prior = (a.previous_status || a.latest_event?.raw_payload?.previous_status || '').toUpperCase()
          if (POST_APPLIED_STAGES.has(prior)) {
            return af === 'ghosted_post_applied'
          } else {
            return af === 'ghosted_applied'
          }
        } else {
          return af === 'rejected'
        }
      })
    }
    const total = items.length
    const limit = Number(params.limit) || 1000
    const offset = Number(params.offset) || 0
    const pagedItems = items.slice(offset, offset + limit)
    return ok({ items: pagedItems, total, limit, offset })
  }

  if (urlPath === '/applications/by-status' && method === 'get') {
    const counts = {}
    ;(db.applications || []).forEach((a) => {
      counts[a.status] = (counts[a.status] || 0) + 1
    })
    return ok(counts)
  }

  if (urlPath === '/applications/bulk-transition' && method === 'post') {
    const { target_status, from_statuses, exclude_ids } = data
    const updatedIds = []
    const excludeSet = new Set(exclude_ids || [])
    const fromSet = new Set(from_statuses || [])

    db.applications = db.applications.map((app) => {
      if (fromSet.has(app.status) && !excludeSet.has(app.id)) {
        app.previous_status = app.status
        app.status = target_status
        app.last_activity_at = new Date().toISOString()
        updatedIds.push(app.id)
      }
      return app
    })
    saveDemoDb(db)
    return ok({ updated_ids: updatedIds })
  }

  const appMatch = urlPath.match(/^\/applications\/([^/]+)$/)
  if (appMatch) {
    const appId = appMatch[1]
    const appIndex = (db.applications || []).findIndex((a) => String(a.id) === String(appId))

    if (method === 'get') {
      if (appIndex !== -1) {
        const app = db.applications[appIndex]
        const events = app.events || []
        const latest_event = events.length > 0 ? events[0] : null
        return ok({ ...app, events, latest_event })
      }
      // Fallback: check if this ID corresponds to an assessment dossier in demo mode
      const assessment = (db.assessments || []).find(
        (a) => String(a.id) === String(appId) || String(a.result_json?.application_id) === String(appId)
      )
      if (assessment) {
        const r = assessment.result_json || {}
        const syntheticApp = {
          id: r.application_id || assessment.id,
          company_id: r.company_id || null,
          company_name: r.company || assessment.title_hint || 'Target Company',
          company: {
            id: r.company_id || null,
            name: r.company || assessment.title_hint || 'Target Company',
            domain: r.company_domain || null,
          },
          position: r.position || 'Software Engineer',
          status: r.assessment_archived ? 'ARCHIVED' : 'ASSESSMENT',
          is_assessment: true,
          job_url: assessment.job_url || null,
          created_at: assessment.created_at,
          application_date: assessment.created_at,
          last_activity_at: assessment.completed_at || assessment.created_at,
          match_score: r.match_score,
          fit_score: r.fit_score,
          programmatic_match_score: r.programmatic_match_score,
          match_analysis_payload: r,
          job_posting: {
            id: `jp_assess_${assessment.id}`,
            title: r.position || 'Software Engineer',
            company_name: r.company || 'Target Company',
            description_markdown: assessment.raw_text || r.summary || '',
            salary_min: r.salary_min ?? null,
            salary_max: r.salary_max ?? null,
            currency: r.currency || 'USD',
            location: r.location || null,
            work_model: r.work_model || null,
            required_skills: [...(r.matching_skills || []), ...(r.missing_skills || [])],
          },
          events: [],
          latest_event: null,
          action_items: [],
        }
        return ok(syntheticApp)
      }
      throw new Error('Application not found')
    }

    if (method === 'patch') {
      if (appIndex === -1) {
        const assessmentIdx = (db.assessments || []).findIndex(
          (a) => String(a.id) === String(appId) || String(a.result_json?.application_id) === String(appId)
        )
        if (assessmentIdx !== -1) {
          const assessment = db.assessments[assessmentIdx]
          if (data.job_url !== undefined) assessment.job_url = data.job_url
          if (data.position !== undefined && assessment.result_json) {
            assessment.result_json.position = data.position
          }
          saveDemoDb(db)
          const r = assessment.result_json || {}
          return ok({
            id: r.application_id || assessment.id,
            company_name: r.company || 'Target Company',
            company: { id: r.company_id || null, name: r.company || 'Target Company', domain: r.company_domain || null },
            position: r.position || 'Software Engineer',
            status: r.assessment_archived ? 'ARCHIVED' : 'ASSESSMENT',
            is_assessment: true,
            job_url: assessment.job_url || null,
            match_analysis_payload: r,
          })
        }
        throw new Error('Application not found')
      }
      const targetApp = db.applications[appIndex]
      const existingJp = targetApp.job_posting || {}
      const updatedJp = {
        ...existingJp,
        ...(data.salary_min !== undefined ? { salary_min: data.salary_min } : {}),
        ...(data.salary_max !== undefined ? { salary_max: data.salary_max } : {}),
        ...(data.currency !== undefined ? { currency: data.currency } : {}),
        ...(data.location !== undefined ? { location: data.location } : {}),
        ...(data.work_model !== undefined ? { work_model: data.work_model } : {}),
      }

      const existingSpec = updatedJp.structured_spec || targetApp.structured_spec || {}
      const updatedSpec = {
        ...existingSpec,
        ...(data.location !== undefined ? { location_text: data.location } : {}),
        ...(data.work_model !== undefined ? { workplace_type: data.work_model } : {}),
      }
      updatedJp.structured_spec = updatedSpec

      db.applications[appIndex] = {
        ...targetApp,
        ...data,
        job_posting: updatedJp,
        last_activity_at: new Date().toISOString(),
      }
      saveDemoDb(db)
      return ok(db.applications[appIndex])
    }

    if (method === 'delete') {
      if (appIndex !== -1) {
        db.applications.splice(appIndex, 1)
        saveDemoDb(db)
      }
      return ok({ message: 'Deleted successfully' })
    }
  }

  const appTransitionMatch = urlPath.match(/^\/applications\/([^/]+)\/transition$/)
  if (appTransitionMatch && method === 'post') {
    const appId = appTransitionMatch[1]
    const appIndex = (db.applications || []).findIndex((a) => String(a.id) === String(appId))
    if (appIndex === -1) throw new Error('Application not found')

    const app = db.applications[appIndex]
    const oldStatus = app.status
    const newStatus = data.status || oldStatus

    app.status = newStatus
    if (data.rejection_reason) app.rejection_reason = data.rejection_reason
    if (data.rejection_date) app.rejection_date = data.rejection_date
    if (data.notes) app.notes = data.notes
    app.last_activity_at = new Date().toISOString()

    const isSameStatus = oldStatus === newStatus
    const eventType = isSameStatus ? (data.event_type || 'CUSTOM_NOTE') : `STAGE_CHANGE_${newStatus}`
    const eventTitle = isSameStatus ? (data.notes ? 'Activity / Note Logged' : 'Timeline Event Recorded') : `Transitioned to ${newStatus}`

    let preservedInterviewStage = data.interview_stage
    if (isSameStatus && !preservedInterviewStage) {
      for (const evt of app.events || []) {
        if (evt.raw_payload?.interview_stage) {
          preservedInterviewStage = evt.raw_payload.interview_stage
          break
        }
      }
    }

    const rawPayload = {
      ...data,
      ...(!isSameStatus ? { previous_status: oldStatus } : {}),
      ...(preservedInterviewStage ? { interview_stage: preservedInterviewStage } : {}),
    }

    if (!isSameStatus) {
      app.previous_status = oldStatus
    }

    const newEvent = {
      id: `evt_${Date.now()}`,
      application_id: appId,
      email_event_type: eventType,
      event_type: eventType,
      title: eventTitle,
      email_summary: data.notes ? data.notes.trim() : `Moved application from ${oldStatus} to ${newStatus}`,
      description: data.notes || `Moved application from ${oldStatus} to ${newStatus}`,
      created_at: new Date().toISOString(),
      raw_payload: rawPayload,
    }

    app.events = [newEvent, ...(app.events || [])]
    app.latest_event = newEvent
    if (preservedInterviewStage === 'Task Completed / Awaiting Response') {
      app.scheduled_interview_at = null
    } else if (data.scheduled_at) {
      app.scheduled_interview_at = data.scheduled_at
    }
    saveDemoDb(db)
    return ok(app)
  }

  const coverLetterGetMatch = urlPath.match(/^\/applications\/([^/]+)\/cover-letter$/)
  if (coverLetterGetMatch) {
    const appId = coverLetterGetMatch[1]
    const app = (db.applications || []).find((a) => String(a.id) === String(appId))
    if (method === 'get') {
      return ok({
        cover_letter_text: app?.cover_letter_text || '',
        cover_letter_status: app?.cover_letter_status || 'NOT_STARTED',
        cover_letter_generated_at: app?.cover_letter_generated_at || null,
      })
    }
    if (method === 'patch') {
      if (app) {
        app.cover_letter_text = data.cover_letter_text || data.text
        saveDemoDb(db)
      }
      return ok({
        cover_letter_text: app?.cover_letter_text || '',
        cover_letter_status: 'COMPLETED',
        cover_letter_generated_at: new Date().toISOString(),
      })
    }
  }

  const coverLetterGenMatch = urlPath.match(/^\/applications\/([^/]+)\/cover-letter\/(generate|regenerate)$/)
  if (coverLetterGenMatch && method === 'post') {
    const appId = coverLetterGenMatch[1]
    const app = (db.applications || []).find((a) => String(a.id) === String(appId))
    const company = app?.company_name || 'Hiring Company'
    const position = app?.position || 'Target Position'

    const letterText = `Dear Hiring Manager at ${company},\n\nI am writing to express my strong interest in the ${position} role. With my background as a Staff Distributed Systems Engineer and extensive hands-on experience in Go, Rust, and microservices architecture, I am confident in my ability to make an immediate positive impact on your team.\n\nThroughout my career, I have designed and deployed high-performance distributed systems, optimized real-time data streaming pipelines, and led critical infrastructure initiatives. I look forward to discussing how my skills align with ${company}'s goals.\n\nSincerely,\nJohn Souls`

    if (app) {
      app.cover_letter_text = letterText
      app.cover_letter_status = 'COMPLETED'
      app.cover_letter_generated_at = new Date().toISOString()
      saveDemoDb(db)
    }

    return ok({
      cover_letter_text: letterText,
      cover_letter_status: 'COMPLETED',
      cover_letter_generated_at: new Date().toISOString(),
    })
  }

  const appQuestionsMatch = urlPath.match(/^\/applications\/([^/]+)\/questions$/)
  if (appQuestionsMatch) {
    const appId = appQuestionsMatch[1]
    const app = (db.applications || []).find((a) => String(a.id) === String(appId))
    if (method === 'get') {
      return ok({
        application_id: Number(appId),
        questions: app?.application_questions || [],
        status: (app?.application_questions || []).some(q => q.answer) ? 'COMPLETED' : 'DRAFT',
      })
    }
    if (method === 'patch') {
      if (app) {
        app.application_questions = data.questions || []
        saveDemoDb(db)
      }
      return ok({
        application_id: Number(appId),
        questions: app?.application_questions || [],
        status: 'COMPLETED',
      })
    }
  }

  const appQuestionsGenMatch = urlPath.match(/^\/applications\/([^/]+)\/questions\/generate$/)
  if (appQuestionsGenMatch && method === 'post') {
    const appId = appQuestionsGenMatch[1]
    const app = (db.applications || []).find((a) => String(a.id) === String(appId))
    const company = app?.company?.name || app?.company_name || 'Target Company'

    const inputQuestions = data.questions || []
    const generatedQuestions = inputQuestions.map((q) => ({
      id: q.id || `q_${Math.random().toString(36).substring(2, 9)}`,
      question: q.question,
      word_limit: q.word_limit,
      answer: `Drawing from 8+ years of distributed systems engineering in Python, Go, and PostgreSQL, I have architected high-throughput infrastructure supporting 45,000 req/sec at CloudTech. For ${company}, this deep background enables immediate contribution to core reliability, sub-10ms query optimization, and resilient microservices.`,
      status: 'GENERATED',
      updated_at: new Date().toISOString(),
    }))

    if (app) {
      app.application_questions = generatedQuestions
      saveDemoDb(db)
    }

    return ok({
      application_id: Number(appId),
      questions: generatedQuestions,
      status: 'COMPLETED',
    })
  }

  const appGuideMatch = urlPath.match(/^\/applications\/([^/]+)\/interview-guide$/)
  if (appGuideMatch) {
    const appId = appGuideMatch[1]
    const app = (db.applications || []).find((a) => String(a.id) === String(appId))
    if (method === 'post') {
      const company = app?.company?.name || app?.company_name || 'Target Company'
      const position = app?.position || 'Software Engineer'
      const cr = data.company_research || app?.company?.company_research || app?.company_research
      const cultureNote = cr?.engineering_culture
        ? `<p><strong>Engineering Values:</strong> ${cr.engineering_culture}</p>`
        : ''
      const prioritiesNote = cr?.strategic_priorities
        ? `<p><strong>Strategic Focus:</strong> ${(Array.isArray(cr.strategic_priorities) ? cr.strategic_priorities : [cr.strategic_priorities]).join(', ')}</p>`
        : ''

      const sampleHtml = `
        <div class="guide-section">
          <h2>1. 🏢 Role & Company Brief</h2>
          <p>Tailored preparation for <strong>${position}</strong> at <strong>${company}</strong>.</p>
          ${cultureNote}
          ${prioritiesNote}
        </div>
        <div class="guide-section">
          <h2>2. 🎯 Strategic Fit & Elevator Pitch</h2>
          <p>60-90 second introduction tailored to ${company}'s core technical stack.</p>
        </div>
        <div class="guide-section">
          <h2>3. ⭐ Tailored STAR Stories</h2>
          <p>High-impact stories demonstrating leadership, systems architecture, and production delivery.</p>
        </div>
        <div class="guide-section">
          <h2>4. 🧠 Behavioral & Technical Question Defenses</h2>
          <p>Key architectural questions and defense talking points tailored to ${company}.</p>
        </div>
        <div class="guide-section">
          <h2>5. 💬 High-Leverage Questions to Ask Interviewer</h2>
          <p>Insightful questions demonstrating technical curiosity about ${company}'s scale and roadmaps.</p>
        </div>
        <div class="guide-section">
          <h2>6. ✅ Final Pre-Interview Checklist</h2>
          <p>Quick checklist to review 15 minutes before interviewing with ${company}.</p>
        </div>
      `.trim()

      if (app) {
        app.interview_guide_html = sampleHtml
        app.interview_guide_language = data.language || 'en'
        app.interview_guide_generated_at = new Date().toISOString()
        app.interview_guide_preferences = data
        saveDemoDb(db)
      }

      return ok(
        app || {
          id: appId,
          interview_guide_html: sampleHtml,
          interview_guide_language: data.language || 'en',
          interview_guide_generated_at: new Date().toISOString(),
          interview_guide_preferences: data,
        }
      )
    }

    if (method === 'delete') {
      if (app) {
        app.interview_guide_html = null
        app.interview_guide_generated_at = null
        saveDemoDb(db)
      }
      return ok(
        app || {
          id: appId,
          interview_guide_html: null,
          interview_guide_generated_at: null,
        }
      )
    }
  }

  const analyzeSpecMatch = urlPath.match(/^\/applications\/([^/]+)\/analyze-spec$/)
  if (analyzeSpecMatch && method === 'post') {
    const appId = analyzeSpecMatch[1]
    const app = (db.applications || []).find((a) => String(a.id) === String(appId))
    const company = app?.company?.name || app?.company_name || 'Target Company'
    const position = app?.position || 'Software Engineer'

    if (app) {
      if (data.job_url) app.job_url = data.job_url
      app.match_score = 92
      app.fit_score = 92
      app.match_analysis_payload = {
        match_score: 92,
        fit_score: 92,
        programmatic_match_score: 90,
        recommendation: 'APPLY_STRONGLY',
        seniority_fit: 'MATCHES',
        critical_risks: [],
        matching_skills: ['Distributed Systems', 'Python', 'FastAPI', 'PostgreSQL', 'Cloud Infrastructure'],
        missing_skills: ['GraphQL'],
        pros: ['Direct stack overlap', 'High performance systems track record'],
        cons: ['GraphQL not prominently mentioned in CV'],
        summary: `Strong technical match for ${position} at ${company} with core backend alignment.`,
      }
      app.job_posting = {
        id: `jp_${Date.now()}`,
        title: position,
        description_markdown: data.raw_description || 'Extracted job specification description.',
        salary_min: 170000,
        salary_max: 220000,
        currency: 'USD',
        location: 'Remote',
        work_model: 'Remote',
        required_skills: ['Distributed Systems', 'Python', 'FastAPI', 'PostgreSQL', 'Cloud Infrastructure'],
        source_url: data.job_url || app.job_url || '',
        structured_spec: {
          why_hiring: `Expanding backend platform infrastructure to support high scale microservices across ${company}.`,
          what_you_will_build: 'Architect resilient data pipelines and distributed storage abstractions.',
          responsibilities: [
            'Design and implement high throughput distributed systems.',
            'Collaborate with cross-functional product and infrastructure teams.',
            'Maintain 99.99% availability and optimize low-latency query paths.',
          ],
          requirements: [
            '5+ years building backend systems in Python, Go, or Rust.',
            'Deep understanding of relational databases and distributed consensus.',
            'Strong background in cloud architecture (AWS/GCP).',
          ],
          extracted_skills: ['Distributed Systems', 'Python', 'FastAPI', 'PostgreSQL', 'Cloud Infrastructure'],
          compensation_text: '$170,000 – $220,000',
          location_text: 'Remote',
        },
      }
      saveDemoDb(db)
    }

    const newTask = {
      id: `task_eval_${Date.now()}`,
      task_type: 'APPLICATION_ASSESSMENT',
      job_url: data.job_url || app?.job_url || '',
      title_hint: `${company} - ${position}`,
      status: 'COMPLETED',
      stage: 'COMPLETE',
      raw_text: data.raw_description || '',
      error_message: null,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      result_json: {
        target_application_id: appId,
        is_direct_application: true,
        company,
        position,
        match_score: 92,
        fit_score: 92,
      },
    }
    return ok(newTask)
  }

  // 2. INTAKE & QUEUE ENDPOINTS
  if (urlPath === '/intake/paste' && method === 'post') {
    const newApp = {
      id: `app_demo_${Date.now()}`,
      company_name: data.company_name || 'Extracted Tech Corp',
      position: data.position || 'Senior Systems Engineer',
      status: 'APPLIED',
      location: 'Remote',
      work_model: 'Remote',
      salary_min: 180000,
      salary_max: 230000,
      currency: 'USD',
      url: data.url || '',
      application_date: new Date().toISOString(),
      last_activity_at: new Date().toISOString(),
      match_score: 89,
      fit_score: 89,
      programmatic_match_score: 88,
      description: data.raw_text || 'Extracted job description text.',
      match_analysis_payload: {
        match_score: 89,
        fit_score: 89,
        programmatic_match_score: 88,
        recommendation: 'APPLY_STRONGLY',
        seniority_fit: 'MATCHES',
        critical_risks: [],
        matching_skills: ['Go', 'Rust', 'PostgreSQL', 'Distributed Systems'],
        missing_skills: [],
        pros: ['Strong backend alignment', 'Distributed systems experience'],
        cons: ['High scale throughput expectation'],
        summary: 'Strong backend systems alignment with proven distributed track record.',
      },
      events: [],
    }
    db.applications = [newApp, ...(db.applications || [])]
    saveDemoDb(db)
    return ok(newApp)
  }

  if (urlPath === '/intake/assess-job' && method === 'post') {
    const newApp = {
      id: `app_demo_${Date.now()}`,
      company_name: data.company_name || 'Assessed Tech Co',
      position: data.position || 'Software Architect',
      status: 'ASSESSMENT',
      location: 'San Francisco, CA',
      work_model: 'Hybrid',
      salary_min: 200000,
      salary_max: 260000,
      currency: 'USD',
      url: data.url || '',
      application_date: new Date().toISOString(),
      last_activity_at: new Date().toISOString(),
      match_score: 92,
      fit_score: 92,
      programmatic_match_score: 90,
      description: data.raw_text || 'Job specification for assessment.',
      match_analysis_payload: {
        match_score: 92,
        fit_score: 92,
        programmatic_match_score: 90,
        recommendation: 'APPLY_STRONGLY',
        seniority_fit: 'MATCHES',
        critical_risks: [],
        matching_skills: ['Architecture leadership', 'High availability system design'],
        missing_skills: [],
        pros: ['Architecture leadership', 'High availability system design'],
        cons: ['Proprietary toolchain'],
        summary: 'Outstanding architectural alignment with high availability systems design.',
      },
      events: [],
    }
    db.applications = [newApp, ...(db.applications || [])]
    saveDemoDb(db)
    return ok(newApp)
  }

  if (urlPath === '/intake/enqueue-assessment' && method === 'post') {
    const newTask = {
      id: `task_eval_${Date.now()}`,
      task_type: 'JOB_ASSESSMENT',
      job_url: data.url || '',
      company_name: data.company_name || 'Enqueued Corp',
      position: data.position || 'Software Engineer',
      title_hint: data.company_name || 'Enqueued Job Lead',
      status: 'COMPLETED',
      stage: 'COMPLETED',
      progress: 100,
      match_score: 87,
      fit_score: 87,
      raw_text: data.raw_text || '',
      error_message: null,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      result_json: {
        company: data.company_name || 'Enqueued Corp',
        position: data.position || 'Software Engineer',
        summary: 'Demo enqueued job lead qualification complete.',
        match_score: 87,
        fit_score: 87,
        programmatic_match_score: 85,
        recommendation: 'APPLY_STRONGLY',
        seniority_fit: 'MATCHES',
        critical_risks: [],
        salary_min: 190000,
        salary_max: 240000,
        currency: 'USD',
        location: 'Remote',
        work_model: 'Remote',
        matching_skills: ['Go', 'Distributed Systems', 'PostgreSQL'],
        missing_skills: ['Docker'],
        pros: ['Strong core tech stack alignment'],
        cons: ['High applicant volume'],
      }
    }
    db.intake_evaluations = [newTask, ...(db.intake_evaluations || [])]
    saveDemoDb(db)
    return ok(newTask)
  }

  if (urlPath === '/intake/confirm-assessment' && method === 'post') {
    const appId = data.application_id
    if (appId) {
      const idx = (db.assessments || []).findIndex(
        (a) => String(a.id) === String(appId) || String(a.result_json?.application_id) === String(appId)
      )
      if (idx !== -1) {
        if (!db.assessments[idx].result_json) db.assessments[idx].result_json = {}
        db.assessments[idx].result_json.assessment_archived = true
      }
    }

    const newApp = {
      id: `app_demo_${Date.now()}`,
      company_name: data.company || 'Confirmed Tech Corp',
      position: data.position || 'Software Engineer',
      status: data.status || 'APPLIED',
      location: data.location || 'Remote',
      work_model: data.work_model || 'Remote',
      salary_min: data.salary_min || 190000,
      salary_max: data.salary_max || 240000,
      currency: data.currency || 'USD',
      url: data.job_url || '',
      application_date: new Date().toISOString(),
      last_activity_at: new Date().toISOString(),
      match_score: data.match_analysis_payload?.match_score || 90,
      fit_score: data.match_analysis_payload?.fit_score || 90,
      programmatic_match_score: 88,
      description: data.description_markdown || 'Confirmed assessment job posting.',
      match_analysis_payload: data.match_analysis_payload || {},
      events: [
        {
          id: `evt_conf_${Date.now()}`,
          application_id: `app_demo_${Date.now()}`,
          event_type: 'APPLICATION_CREATED',
          title: 'Promoted Lead to Active Pipeline',
          description: `Confirmed assessment and created application in ${data.status || 'APPLIED'} status.`,
          created_at: new Date().toISOString(),
          raw_payload: {}
        }
      ]
    }
    db.applications = [newApp, ...(db.applications || [])]
    saveDemoDb(db)
    return ok(newApp)
  }

  // Assessments Endpoints
  if (urlPath === '/intake/assessments' && method === 'get') {
    const list = db.assessments || []
    const limit = params.limit ? parseInt(params.limit, 10) : 50
    const offset = params.offset ? parseInt(params.offset, 10) : 0
    return ok(list.slice(offset, offset + limit))
  }

  const assessRestoreMatch = urlPath.match(/^\/intake\/assessments\/([^/]+)\/restore$/)
  if (assessRestoreMatch && method === 'post') {
    const appId = assessRestoreMatch[1]
    const idx = (db.assessments || []).findIndex(
      (a) => String(a.id) === String(appId) || String(a.result_json?.application_id) === String(appId)
    )
    if (idx !== -1) {
      if (!db.assessments[idx].result_json) db.assessments[idx].result_json = {}
      db.assessments[idx].result_json.assessment_archived = false
      saveDemoDb(db)
      return ok({ status: 'success', message: `Assessment ${appId} restored.` })
    }
    return ok({ status: 'success', message: 'Assessment restored.' })
  }

  const assessPermanentDeleteMatch = urlPath.match(/^\/intake\/assessments\/([^/]+)\/permanent$/)
  if (assessPermanentDeleteMatch && method === 'delete') {
    const appId = assessPermanentDeleteMatch[1]
    db.assessments = (db.assessments || []).filter(
      (a) => String(a.id) !== String(appId) && String(a.result_json?.application_id) !== String(appId)
    )
    saveDemoDb(db)
    return ok({ status: 'success', message: `Assessment ${appId} deleted.` })
  }

  const assessDismissMatch = urlPath.match(/^\/intake\/assessments\/([^/]+)$/)
  if (assessDismissMatch && method === 'delete') {
    const appId = assessDismissMatch[1]
    const idx = (db.assessments || []).findIndex(
      (a) => String(a.id) === String(appId) || String(a.result_json?.application_id) === String(appId)
    )
    if (idx !== -1) {
      if (!db.assessments[idx].result_json) db.assessments[idx].result_json = {}
      db.assessments[idx].result_json.assessment_archived = true
      saveDemoDb(db)
      return ok({ status: 'success', message: `Assessment ${appId} dismissed.` })
    }
    return ok({ status: 'success', message: 'Assessment dismissed.' })
  }

  if (urlPath === '/intake/evaluations' && method === 'get') {
    return ok(db.intake_evaluations || [])
  }

  const evalTaskMatch = urlPath.match(/^\/intake\/evaluations\/([^/]+)$/)
  if (evalTaskMatch && method === 'delete') {
    const taskId = String(evalTaskMatch[1])
    const taskToDelete = (db.intake_evaluations || []).find((t) => String(t.id) === taskId)
    db.intake_evaluations = (db.intake_evaluations || []).filter((t) => String(t.id) !== taskId)

    // Also remove any linked staging item if one was created
    if (taskToDelete) {
      const stagedId = taskToDelete.result_json?.staging_item_id
      const jobUrl = taskToDelete.job_url
      if (stagedId || jobUrl) {
        db.staging_items = (db.staging_items || []).filter((s) => {
          if (stagedId && String(s.id) === String(stagedId)) return false
          if (jobUrl && s.extracted_data?.job_url === jobUrl) return false
          return true
        })
      }
    }

    saveDemoDb(db)
    return ok({ message: 'Evaluation deleted' })
  }

  const evalTaskActionMatch = urlPath.match(/^\/intake\/evaluations\/([^/]+)\/(cancel|retry|fix-jd)$/)
  if (evalTaskActionMatch && method === 'post') {
    const taskId = String(evalTaskActionMatch[1])
    const action = evalTaskActionMatch[2]
    const task = (db.intake_evaluations || []).find((t) => String(t.id) === taskId)
    if (task) {
      if (action === 'cancel') {
        task.status = 'FAILED'
        task.stage = 'FAILED'
        task.error_message = 'Task stopped by user'
      } else if (action === 'retry' || action === 'fix-jd') {
        task.status = 'COMPLETED'
        task.stage = 'COMPLETED'
        task.progress = 100
        task.match_score = task.match_score || 88
        task.fit_score = task.fit_score || 88
        task.error_message = null
        if (data.raw_text) task.raw_text = data.raw_text
      }
      saveDemoDb(db)
    }
    return ok(task || { id: taskId, status: 'COMPLETED' })
  }

  if (urlPath === '/intake/evaluations/bulk-retry' && method === 'post') {
    const ids = new Set((data.task_ids || []).map(String))
    db.intake_evaluations = (db.intake_evaluations || []).map((t) => {
      if (ids.has(String(t.id))) {
        t.status = 'COMPLETED'
        t.stage = 'COMPLETED'
        t.error_message = null
      }
      return t
    })
    saveDemoDb(db)
    return ok({ message: 'Tasks retried' })
  }

  if (urlPath === '/intake/evaluations/bulk-delete' && method === 'post') {
    const ids = new Set((data.task_ids || []).map(String))
    const tasksToDelete = (db.intake_evaluations || []).filter((t) => ids.has(String(t.id)))
    db.intake_evaluations = (db.intake_evaluations || []).filter((t) => !ids.has(String(t.id)))

    // Clean up corresponding staging items
    const stagedIdsToDelete = new Set(
      tasksToDelete.map((t) => t.result_json?.staging_item_id).filter(Boolean).map(String)
    )
    if (stagedIdsToDelete.size > 0) {
      db.staging_items = (db.staging_items || []).filter((s) => !stagedIdsToDelete.has(String(s.id)))
    }

    saveDemoDb(db)
    return ok({ message: 'Tasks deleted', deleted_count: tasksToDelete.length, skipped_count: 0 })
  }

  if (urlPath === '/intake/evaluations/clear-completed' && method === 'post') {
    db.intake_evaluations = (db.intake_evaluations || []).filter((t) => t.status !== 'COMPLETED')
    saveDemoDb(db)
    return ok({ message: 'Completed tasks cleared' })
  }

  if (urlPath === '/intake/extension-config' && method === 'get') {
    return ok({ ai_ready: true })
  }

  if (urlPath === '/intake/sync-account' && method === 'post') {
    return ok({ status: 'success', message: 'Simulated email sync complete! Parsed 2 unread messages.' })
  }

  // 3. CANDIDATE PROFILE ENDPOINTS
  if (urlPath === '/profile/cv' && method === 'get') {
    return ok(db.candidate_profile || null)
  }

  if (urlPath === '/profile/cv' && method === 'post') {
    db.candidate_profile = {
      ...(db.candidate_profile || {}),
      raw_text: data.raw_text,
      parsed_at: new Date().toISOString(),
    }
    saveDemoDb(db)
    return ok(db.candidate_profile)
  }

  if (urlPath === '/profile/cv/parse-file' && method === 'post') {
    return ok(db.candidate_profile || {})
  }

  const cvPatchMatch = urlPath.match(/^\/profile\/cv\/([^/]+)$/)
  if (cvPatchMatch) {
    if (method === 'patch') {
      db.candidate_profile = { ...(db.candidate_profile || {}), ...data }
      saveDemoDb(db)
      return ok(db.candidate_profile)
    }
    if (method === 'delete') {
      db.candidate_profile = null
      saveDemoDb(db)
      return ok({ message: 'Profile deleted' })
    }
  }

  // 4. ACTION ITEMS ENDPOINTS
  if (urlPath === '/action-items' && method === 'get') {
    let items = [...(db.action_items || [])]

    // Associate application object if present
    items = items.map(item => {
      const app = (db.applications || []).find(a => a.id === item.application_id)
      return {
        ...item,
        application: app ? {
          id: app.id,
          company: { name: app.company_name || app.company?.name || 'Company' },
          position: app.position
        } : null
      }
    })

    if (params.status) {
      items = items.filter((i) => i.status === params.status)
    }

    const allItems = db.action_items || []
    const total = allItems.length
    const pending_count = allItems.filter(i => i.status === 'PENDING').length
    const high_urgency_count = allItems.filter(i => i.status === 'PENDING' && i.urgency === 'HIGH').length
    const completed_count = allItems.filter(i => i.status === 'COMPLETED').length

    return ok({
      items,
      total,
      pending_count,
      high_urgency_count,
      completed_count
    })
  }

  if (urlPath === '/action-items' && method === 'post') {
    const app = (db.applications || []).find(a => a.id === data.application_id)
    const newItem = {
      id: `action_${Date.now()}`,
      application_id: data.application_id || null,
      company_name: app?.company_name || data.company_name || 'General Task',
      position: app?.position || data.position || '',
      title: data.title || 'New Action Item',
      description: data.description || '',
      due_date: data.due_date || new Date(Date.now() + 86400000 * 3).toISOString(),
      urgency: data.urgency || 'MEDIUM',
      manual_urgency: data.manual_urgency || 'MEDIUM',
      status: data.status || 'PENDING',
      created_at: new Date().toISOString(),
    }
    db.action_items = [newItem, ...(db.action_items || [])]
    saveDemoDb(db)
    return ok(newItem)
  }

  const actionItemMatch = urlPath.match(/^\/action-items\/([^/]+)$/)
  if (actionItemMatch) {
    const itemId = actionItemMatch[1]
    const itemIndex = (db.action_items || []).findIndex((i) => i.id === itemId)

    if (method === 'patch' || method === 'put') {
      if (itemIndex !== -1) {
        const oldStatus = db.action_items[itemIndex].status
        db.action_items[itemIndex] = { ...db.action_items[itemIndex], ...data }
        const item = db.action_items[itemIndex]
        if (item.application_id) {
          const parentApp = (db.applications || []).find((a) => String(a.id) === String(item.application_id))
          if (parentApp) {
            parentApp.last_activity_at = new Date().toISOString()
            const hasPending = (db.action_items || []).some(
              (a) => String(a.application_id) === String(parentApp.id) && a.status === 'PENDING'
            )
            parentApp.has_action_required = hasPending
            if (item.status === 'COMPLETED' && oldStatus !== 'COMPLETED') {
              const compEvt = {
                id: `evt_comp_${Date.now()}`,
                application_id: parentApp.id,
                email_event_type: 'ACTION_ITEM_COMPLETED',
                event_type: 'ACTION_ITEM_COMPLETED',
                title: 'Completed Action Item',
                email_summary: `Completed action item: ${item.title}. Awaiting response.`,
                description: `Completed action item: ${item.title}. Awaiting response.`,
                created_at: new Date().toISOString(),
                raw_payload: {
                  action_item_id: item.id,
                  title: item.title,
                  urgency: item.urgency,
                  completed_at: new Date().toISOString(),
                  ...(parentApp.status === 'TECHNICAL_INTERVIEW'
                    ? { interview_stage: 'Task Completed / Awaiting Response' }
                    : {}),
                },
              }
              parentApp.events = [compEvt, ...(parentApp.events || [])]
              parentApp.latest_event = compEvt
              if (parentApp.status === 'TECHNICAL_INTERVIEW') {
                parentApp.scheduled_interview_at = null
              }
            }
          }
        }
        saveDemoDb(db)
      }
      return ok(db.action_items[itemIndex] || {})
    }
    if (method === 'delete') {
      if (itemIndex !== -1) {
        db.action_items.splice(itemIndex, 1)
        saveDemoDb(db)
      }
      return ok({ message: 'Action item deleted' })
    }
  }

  const actionUrgencyMatch = urlPath.match(/^\/action-items\/([^/]+)\/urgency$/)
  if (actionUrgencyMatch && (method === 'put' || method === 'patch')) {
    const itemId = actionUrgencyMatch[1]
    const item = (db.action_items || []).find((i) => i.id === itemId)
    if (item) {
      if (data.manual_urgency) {
        item.urgency = data.manual_urgency
        item.manual_urgency = data.manual_urgency
        item.manual_urgency_override = true
      } else {
        item.manual_urgency = null
        item.manual_urgency_override = false
      }
      saveDemoDb(db)
    }
    return ok(item || {})
  }

  // 5. STAGING ENDPOINTS
  if (urlPath === '/staging' && method === 'get') {
    let items = [...(db.staging_items || [])]
    if (params.status) {
      const targetStatus = params.status === 'PROCESSED' ? 'RESOLVED' : params.status
      items = items.filter((s) => (s.status || 'PENDING') === targetStatus)
    }
    if (params.search) {
      const q = params.search.toLowerCase()
      items = items.filter(
        (s) =>
          s.company_name?.toLowerCase().includes(q) ||
          s.position?.toLowerCase().includes(q) ||
          s.subject?.toLowerCase().includes(q)
      )
    }

    const sortOrder = params.sort_order || 'desc'
    items.sort((a, b) => {
      const dateA = new Date(a.email_received_at || a.created_at || 0).getTime()
      const dateB = new Date(b.email_received_at || b.created_at || 0).getTime()
      return sortOrder === 'asc' ? dateA - dateB : dateB - dateA
    })

    const total = items.length
    const offset = parseInt(params.offset, 10) || 0
    const limit = parseInt(params.limit, 10) || 50
    const paginated = items.slice(offset, offset + limit)

    return ok({ items: paginated, total })
  }

  if (urlPath === '/staging/candidate-applications' && method === 'get') {
    const q = (params.q || '').trim()
    const stagingId = params.staging_item_id
    const stagedItem = stagingId
      ? (db.staging_items || []).find((s) => String(s.id) === String(stagingId))
      : null
    const senderEmail = stagedItem?.email_sender || ''
    const senderDomMatch = senderEmail.match(/@([a-z0-9.-]+)/i)
    const rawSenderDom = senderDomMatch ? senderDomMatch[1].toLowerCase() : null
    const senderDomain =
      rawSenderDom &&
      !['gmail.com', 'outlook.com', 'yahoo.com', 'greenhouse.io', 'ashbyhq.com', 'lever.co'].some((d) =>
        rawSenderDom.endsWith(d)
      )
        ? rawSenderDom
        : null
    const signalCompany =
      stagedItem?.extracted_data?.company ||
      stagedItem?.extracted_data?.company_name ||
      stagedItem?.suggested_company ||
      ''
    const CONCLUDED = ['REJECTED', 'ARCHIVED', 'WITHDRAWN', 'HIRED']

    const apps = (db.applications || []).filter((a) => a.status !== 'ASSESSMENT')
    const scored = apps.map((a) => {
      const compName = a.company?.name || a.company_name || ''
      const compDom = (a.company?.domain || '').toLowerCase()
      const isActive = !CONCLUDED.includes(a.status)
      let sigScore = 0
      let reason = null
      if (senderDomain && (compDom === senderDomain || normalizeCompanyText(compName) === normalizeCompanyText(senderDomain))) {
        sigScore = 0.96
        reason = `Matched domain ${senderDomain}`
      } else if (signalCompany && signalCompany.toLowerCase() !== 'unknown company') {
        const sc = scoreApplicationMatch(a, signalCompany)
        if (sc >= 0.6) {
          sigScore = Math.min(sc, 0.92)
          reason = compDom ? `Matched ${compDom}` : 'Matched company'
        }
      }
      const qScore = q && q.toLowerCase() !== 'unknown company' ? scoreApplicationMatch(a, q) : sigScore
      const effScore = Math.max(qScore, q && normalizeCompanyText(q) === normalizeCompanyText(signalCompany) ? sigScore : 0)
      if (!reason && effScore >= 0.7) {
        reason = compDom ? `Matched ${compDom}` : 'Company match'
      }
      return {
        id: a.id,
        company_id: a.company?.id || a.company_id || 1,
        company: {
          id: a.company?.id || a.company_id || 1,
          name: compName,
          domain: a.company?.domain || null,
        },
        position: a.position,
        status: a.status,
        job_url: a.job_url || a.url || null,
        application_date: a.application_date || a.created_at || null,
        last_activity_at: a.last_activity_at || a.updated_at || a.created_at || null,
        match_score: Number(effScore.toFixed(3)),
        match_reason_label: reason,
        is_active_stage: isActive,
        _sigScore: sigScore,
      }
    })

    const filtered =
      q && q.toLowerCase() !== 'unknown company'
        ? scored.filter((item) => item.match_score >= 0.25)
        : scored

    filtered.sort((a, b) => {
      const scoreDiff = (b.match_score + (b.is_active_stage ? 0.02 : 0)) - (a.match_score + (a.is_active_stage ? 0.02 : 0))
      if (Math.abs(scoreDiff) > 0.005) return scoreDiff
      return new Date(b.last_activity_at || 0) - new Date(a.last_activity_at || 0)
    })

    const sigMatches = scored.filter((item) => item._sigScore >= 0.65)
    sigMatches.sort((a, b) => b._sigScore - a._sigScore)
    const smartSuggestion = sigMatches.length ? sigMatches[0] : null

    return ok({
      items: filtered.slice(0, parseInt(params.limit, 10) || 30),
      detected_signals: {
        sender_domain: senderDomain,
        detected_domains: senderDomain ? [senderDomain] : [],
        ats_slugs: [],
        candidate_job_urls: [],
        detected_job_url: stagedItem?.extracted_data?.job_url || null,
        cleaned_company: normalizeCompanyText(signalCompany) || null,
      },
      smart_suggestion: smartSuggestion,
    })
  }

  if (urlPath === '/staging/bulk-dismiss' && method === 'post') {
    const idsToDismiss = data.item_ids || []
    if (data.dismiss_all_pending) {
      const count = (db.staging_items || []).filter((s) => (s.status || 'PENDING') === 'PENDING').length
      db.staging_items = (db.staging_items || []).filter((s) => (s.status || 'PENDING') !== 'PENDING')
      saveDemoDb(db)
      return ok({ dismissed_count: count, message: `Successfully dismissed ${count} items.` })
    }
    db.staging_items = (db.staging_items || []).filter((s) => !idsToDismiss.includes(s.id))
    saveDemoDb(db)
    return ok({ dismissed_count: idsToDismiss.length, message: `Successfully dismissed ${idsToDismiss.length} items.` })
  }

  const stagingResolveMatch = urlPath.match(/^\/staging\/([^/]+)\/resolve$/)
  if (stagingResolveMatch && method === 'post') {
    const stageId = stagingResolveMatch[1]
    const item = (db.staging_items || []).find((s) => s.id === stageId)
    if (item) {
      item.status = 'RESOLVED'

      if (data.create_new) {
        const newApp = {
          id: `app_demo_${Date.now()}`,
          company_id: `comp_${Date.now()}`,
          company_name: data.company || item.company_name || 'New Company',
          company: { id: `comp_${Date.now()}`, name: data.company || item.company_name || 'New Company', domain: `${(data.company || 'company').toLowerCase().replace(/\s+/g, '')}.com` },
          position: data.position || item.position || 'Software Engineer',
          status: data.status || 'APPLIED',
          location: 'Remote',
          work_model: 'Remote',
          salary_min: 200000,
          salary_max: 250000,
          currency: 'USD',
          url: data.job_url || '',
          job_url: data.job_url || '',
          application_date: new Date().toISOString(),
          last_activity_at: new Date().toISOString(),
          match_score: 90,
          fit_score: 90,
          programmatic_match_score: 88,
          description: data.description_markdown || 'Created from staging triage email',
          job_posting: {
            id: `jp_${Date.now()}`,
            title: data.position || item.position || 'Software Engineer',
            company_name: data.company || item.company_name || 'New Company',
            description_markdown: data.description_markdown || 'Created from staging triage email',
            salary_min: 200000,
            salary_max: 250000,
            currency: 'USD',
            location: 'Remote',
            work_model: 'Remote',
            required_skills: ['Distributed Systems'],
            structured_spec: {
              compensation_text: '$200,000 - $250,000 USD',
              location_text: 'Remote',
              workplace_type: 'Remote',
              why_hiring: 'Expanding core platform capabilities.',
              what_you_will_build: 'Distributed scalable backend microservices.',
              responsibilities: ['Build backend platform microservices'],
              requirements: ['Experience with distributed backend architecture'],
              extracted_skills: ['Distributed Systems']
            }
          },
          events: [
            {
              id: `evt_${Date.now()}`,
              application_id: `app_demo_${Date.now()}`,
              email_event_type: data.event_type || 'APPLICATION_CONFIRMATION',
              event_type: data.event_type || 'APPLICATION_CONFIRMATION',
              title: data.summary || 'Email Intake Event',
              description: data.summary || 'Created application from staging email triage',
              email_summary: data.summary || 'Created application from staging email triage',
              email_sender: item.email_sender || 'recruiter@company.com',
              created_at: new Date().toISOString(),
              raw_payload: {}
            }
          ]
        }
        db.applications = [newApp, ...(db.applications || [])]
      } else if (data.application_id) {
        const targetApp = (db.applications || []).find(a => a.id === data.application_id)
        if (targetApp) {
          const newEvt = {
            id: `evt_${Date.now()}`,
            application_id: targetApp.id,
            email_event_type: data.event_type || 'EMAIL_RECEIVED',
            event_type: data.event_type || 'EMAIL_RECEIVED',
            title: data.summary || 'Email Event Linked',
            description: data.summary || 'Linked email event from staging triage',
            email_summary: data.summary || 'Linked email event from staging triage',
            email_sender: item.email_sender || 'recruiter@company.com',
            created_at: new Date().toISOString(),
            raw_payload: {}
          }
          targetApp.events = [newEvt, ...(targetApp.events || [])]
          targetApp.latest_event = newEvt
          targetApp.last_activity_at = new Date().toISOString()
          if (data.status) targetApp.status = data.status
        }
      }

      saveDemoDb(db)
    }
    return ok({ message: 'Staging item resolved' })
  }

  const stagingItemMatch = urlPath.match(/^\/staging\/([^/]+)$/)
  if (stagingItemMatch && method === 'delete') {
    const stageId = stagingItemMatch[1]
    db.staging_items = (db.staging_items || []).filter((s) => String(s.id) !== String(stageId))
    saveDemoDb(db)
    return ok({ message: 'Staging item deleted' })
  }

  const stagingReopenMatch = urlPath.match(/^\/staging\/([^/]+)\/reopen$/)
  if (stagingReopenMatch && method === 'post') {
    const stageId = stagingReopenMatch[1]
    const item = (db.staging_items || []).find((s) => String(s.id) === String(stageId))
    if (!item) throw new Error('Staging item not found')
    item.status = 'PENDING'
    item.match_reason = 'REOPENED_FOR_TRIAGE'
    saveDemoDb(db)
    return ok(item)
  }

  if (urlPath === '/staging/resolved' && method === 'delete') {
    db.staging_items = (db.staging_items || []).filter((s) => s.status !== 'PROCESSED' && s.status !== 'RESOLVED')
    saveDemoDb(db)
    return ok({ message: 'Resolved staging items cleared' })
  }

  // Events endpoints
  const eventMoveToStagingMatch = urlPath.match(/^\/events\/([^/]+)\/move-to-staging$/)
  if (eventMoveToStagingMatch && method === 'post') {
    const eventId = eventMoveToStagingMatch[1]
    let foundEvent = null
    let parentApp = null

    for (const app of db.applications || []) {
      const evIdx = (app.events || []).findIndex((e) => String(e.id) === String(eventId))
      if (evIdx !== -1) {
        foundEvent = app.events[evIdx]
        parentApp = app
        app.events.splice(evIdx, 1)
        break
      }
    }

    if (!foundEvent) {
      throw new Error('Event not found')
    }

    // Remove associated action items
    db.action_items = (db.action_items || []).filter((a) => String(a.event_id) !== String(eventId))

    // Create or restore staging item
    if (!db.staging_items) db.staging_items = []
    let staged = db.staging_items.find((s) => s.email_message_id && s.email_message_id === foundEvent.email_message_id)
    if (staged) {
      staged.status = 'PENDING'
      staged.match_reason = 'UNLINKED_MANUALLY'
    } else {
      staged = {
        id: `stg_${Date.now()}`,
        email_message_id: foundEvent.email_message_id || `msg_${Date.now()}`,
        email_sender: foundEvent.email_sender || 'recruiter@company.com',
        email_sender_name: foundEvent.email_sender_name || parentApp?.company?.name || 'Recruiter',
        email_subject: foundEvent.email_subject || foundEvent.title || 'Recruitment Communication',
        email_received_at: foundEvent.email_received_at || foundEvent.created_at || new Date().toISOString(),
        email_raw_body: foundEvent.email_raw_body || foundEvent.description || '',
        extracted_data: foundEvent.raw_payload || {
          company: parentApp?.company?.name || '',
          position: parentApp?.position || '',
          summary: foundEvent.email_summary || foundEvent.description || '',
        },
        match_reason: 'UNLINKED_MANUALLY',
        status: 'PENDING',
        created_at: new Date().toISOString(),
      }
      db.staging_items.unshift(staged)
    }

    saveDemoDb(db)
    return ok({
      status: 'success',
      message: 'Event unlinked and moved to Staging Queue.',
      staging_item_id: staged.id,
      application_id: parentApp?.id,
    })
  }

  const eventItemMatch = urlPath.match(/^\/events\/([^/]+)$/)
  if (eventItemMatch && method === 'patch') {
    const eventId = eventItemMatch[1]
    let updatedEvt = null
    for (const app of db.applications || []) {
      const evt = (app.events || []).find((e) => String(e.id) === String(eventId))
      if (evt) {
        if (!evt.raw_payload) evt.raw_payload = {}
        if (data.notes !== undefined) {
          evt.raw_payload.notes = data.notes.trim()
          if (evt.email_event_type === 'CUSTOM_NOTE' || evt.event_type === 'CUSTOM_NOTE') {
            evt.email_summary = data.notes.trim()
            evt.description = data.notes.trim()
          }
        }
        if (data.email_summary !== undefined) {
          evt.email_summary = data.email_summary.trim()
        }
        if (app.latest_event && String(app.latest_event.id) === String(eventId)) {
          app.latest_event = { ...evt }
        }
        app.last_activity_at = new Date().toISOString()
        updatedEvt = evt
        break
      }
    }
    saveDemoDb(db)
    return ok(updatedEvt || { id: eventId })
  }

  const eventDeleteMatch = urlPath.match(/^\/events\/([^/]+)$/)
  if (eventDeleteMatch && method === 'delete') {
    const eventId = eventDeleteMatch[1]
    for (const app of db.applications || []) {
      app.events = (app.events || []).filter((e) => String(e.id) !== String(eventId))
    }
    db.action_items = (db.action_items || []).filter((a) => String(a.event_id) !== String(eventId))
    saveDemoDb(db)
    return ok({ status: 'success', event_id: eventId })
  }

  // 6. DIAGNOSTICS & TELEMETRY
  if (urlPath === '/diagnostics/quality' && method === 'get') {
    return ok(getDemoQualityStats(db.quality_audits || []))
  }

  if (urlPath === '/diagnostics/stats' && method === 'get') {
    const traces = db.diagnostics_traces || []
    let totalTokens = 0
    let totalSpend = 0
    let totalSavings = 0
    const taskBreakdown = {}

    traces.forEach((t) => {
      const p = t.payload || {}
      const tokens = p.total_tokens || 0
      const cost = p.estimated_cost || 0
      const savings = p.estimated_savings || 0
      const taskName = p.task_type || p.name || t.name || 'General'

      totalTokens += tokens
      totalSpend += cost
      totalSavings += savings

      if (!taskBreakdown[taskName]) {
        taskBreakdown[taskName] = { calls: 0, tokens: 0, cost_usd: 0, savings_usd: 0 }
      }
      taskBreakdown[taskName].calls += 1
      taskBreakdown[taskName].tokens += tokens
      taskBreakdown[taskName].cost_usd += cost
      taskBreakdown[taskName].savings_usd += savings
    })

    return ok({
      total_runs: traces.length,
      total_traces: traces.length,
      success_count: traces.filter((t) => t.status === 'success').length,
      error_count: traces.filter((t) => t.status === 'error').length,
      success_rate: traces.length > 0 ? Math.round((traces.filter((t) => t.status === 'success').length / traces.length) * 100) : 100,
      total_tokens: totalTokens,
      total_spend_usd: totalSpend,
      total_savings_usd: totalSavings,
      task_token_breakdown: taskBreakdown,
      avg_latency_ms: 850,
    })
  }

  if (urlPath === '/diagnostics/traces' && method === 'get') {
    return ok(filterDemoTraces(db.diagnostics_traces || [], params))
  }

  if (urlPath === '/diagnostics/purge' && method === 'delete') {
    db.diagnostics_traces = []
    db.quality_audits = []
    saveDemoDb(db)
    return ok({ message: 'Traces purged' })
  }

  // 7. SYSTEM & AI CONFIG
  if (urlPath === '/system/badges' && method === 'get') {
    const stagingCount = (db.staging_items || []).filter((s) => s.status === 'PENDING').length
    const pendingTasksCount = (db.action_items || []).filter((a) => a.status === 'PENDING').length
    const activeQueueTasksCount = (db.intake_evaluations || []).filter((t) =>
      ['QUEUED', 'PROCESSING', 'FETCHING', 'EXTRACTING', 'MATCHING', 'ASSESSING', 'SAVING'].includes(t.status)
    ).length

    const totalAppsCount = (db.applications || []).length
    const readyAssessmentsCount = (db.applications || []).filter(
      (a) => (a.is_assessment || a.status === 'ASSESSMENT') && a.status === 'ASSESSMENT'
    ).length
    const latestActivity = (db.applications || []).reduce((max, app) => {
      const act = app.last_activity_at || app.created_at
      return act && (!max || act > max) ? act : max
    }, null)

    return ok({
      staging_count: stagingCount,
      pending_action_items_count: pendingTasksCount,
      active_queue_tasks_count: activeQueueTasksCount,
      ready_assessments_count: readyAssessmentsCount,
      total_applications_count: totalAppsCount,
      latest_activity_at: latestActivity,
    })
  }

  if (urlPath === '/config/system' && method === 'get') {
    return ok(db.system_settings || {})
  }

  if (urlPath === '/config/system' && method === 'patch') {
    db.system_settings = { ...(db.system_settings || {}), ...data }
    saveDemoDb(db)
    return ok(db.system_settings)
  }

  if (urlPath === '/config/system/test-search-provider' && method === 'post') {
    return ok({
      success: true,
      latency_ms: 110,
      message: 'Connected to SearXNG search engine successfully (demo mode).',
    })
  }

  if (urlPath === '/config/ai/health' && method === 'get') {
    return ok({
      status: 'healthy',
      latency_ms: 14,
      provider_name: 'Client Local Engine',
      model_name: 'demo-local-llm',
      error_message: null,
    })
  }

  if (urlPath === '/ai/usage-overview' && method === 'get') {
    const monthlyTokens = db.usage_overview?.monthly_tokens || 142800
    const estInTokens = Math.round(monthlyTokens * 0.7)
    const estOutTokens = Math.round(monthlyTokens * 0.3)

    // Find active provider
    const activeProvider = (db.providers || []).find((p) => p.is_active) || {
      input_cost_per_million: 0.0,
      output_cost_per_million: 0.0,
    }
    const inRate = activeProvider.input_cost_per_million || 0.0
    const outRate = activeProvider.output_cost_per_million || 0.0
    const isLocal = inRate === 0 && outRate === 0

    let monthlySpend = 0.0
    let monthlySavings = 0.0
    let localInferencePct = 100.0

    if (isLocal) {
      monthlySpend = 0.0
      monthlySavings = (estInTokens / 1e6) * 0.15 + (estOutTokens / 1e6) * 0.60
      localInferencePct = 100.0
    } else {
      monthlySpend = (estInTokens / 1e6) * inRate + (estOutTokens / 1e6) * outRate
      monthlySavings = 0.0
      localInferencePct = 0.0
    }

    const rates = db.pricing_rates || [
      { key: 'local_baseline', display_name: 'Local LLM (Ollama / LM Studio)', provider: 'local', input_cost_per_million: 0.0, output_cost_per_million: 0.0, is_local: true },
      { key: 'gemini-2.0-flash', display_name: 'Google Gemini 2.0 Flash', provider: 'google_genai', input_cost_per_million: 0.10, output_cost_per_million: 0.40 },
      { key: 'deepseek-chat', display_name: 'DeepSeek V3', provider: 'deepseek', input_cost_per_million: 0.14, output_cost_per_million: 0.28 },
      { key: 'gpt-4o-mini', display_name: 'OpenAI GPT-4o Mini', provider: 'openai', input_cost_per_million: 0.15, output_cost_per_million: 0.60 },
      { key: 'claude-3-5-haiku', display_name: 'Anthropic Claude 3.5 Haiku', provider: 'anthropic', input_cost_per_million: 0.80, output_cost_per_million: 4.00 },
      { key: 'gpt-4o', display_name: 'OpenAI GPT-4o', provider: 'openai', input_cost_per_million: 2.50, output_cost_per_million: 10.00 },
      { key: 'claude-3-5-sonnet', display_name: 'Anthropic Claude 3.5 Sonnet', provider: 'anthropic', input_cost_per_million: 3.00, output_cost_per_million: 15.00 },
    ]

    const comparativeCosts = rates.map((r) => {
      const isRLocal = r.key === 'local_baseline' || r.provider === 'local' || (r.input_cost_per_million === 0 && r.output_cost_per_million === 0)
      const simulatedCost = isRLocal ? 0.0 : (estInTokens / 1e6) * r.input_cost_per_million + (estOutTokens / 1e6) * r.output_cost_per_million
      const diffUsd = simulatedCost - monthlySpend
      let diffPct = 0.0
      if (monthlySpend > 0) {
        diffPct = Math.round(((simulatedCost - monthlySpend) / monthlySpend) * 1000) / 10
      } else {
        diffPct = simulatedCost > 0 ? 100.0 : 0.0
      }
      const status = diffUsd < -0.0001 ? 'cheaper' : diffUsd > 0.0001 ? 'more_expensive' : 'identical'

      return {
        provider_name: r.provider === 'openai' ? 'OpenAI' : r.provider === 'anthropic' ? 'Anthropic' : r.provider === 'gemini' ? 'Google Gemini' : r.provider === 'deepseek' ? 'DeepSeek' : 'Local LLM (Ollama / LM Studio)',
        model_name: r.display_name || r.key,
        provider_type: r.provider,
        input_cost_per_million: r.input_cost_per_million,
        output_cost_per_million: r.output_cost_per_million,
        simulated_cost_usd: Math.round(simulatedCost * 1000) / 1000,
        diff_usd: Math.round(diffUsd * 1000) / 1000,
        diff_percentage: diffPct,
        status,
        is_local: isRLocal,
      }
    })

    return ok({
      monthly_tokens: monthlyTokens,
      monthly_spend_usd: Math.round(monthlySpend * 100) / 100,
      monthly_savings_usd: Math.round(monthlySavings * 100) / 100,
      all_time_tokens: db.usage_overview?.all_time_tokens || 485200,
      all_time_spend_usd: isLocal ? 0.0 : Math.round(monthlySpend * 3.4 * 100) / 100,
      all_time_savings_usd: isLocal ? 48.52 : 0.0,
      local_inference_percentage: localInferencePct,
      total_llm_calls: db.usage_overview?.total_llm_calls || 38,
      avg_cost_per_assessment: isLocal ? 0.0 : Math.round((monthlySpend / 24) * 10000) / 10000,
      task_breakdown: db.usage_overview?.task_breakdown || {
        "JOB_ASSESSMENT": { calls: 24, tokens: 98400, cost_usd: 0.0, savings_usd: 9.84 },
        "COVER_LETTER": { calls: 8, tokens: 26400, cost_usd: 0.0, savings_usd: 2.64 },
        "INTERVIEW_SIMULATION": { calls: 6, tokens: 18000, cost_usd: 0.0, savings_usd: 1.80 }
      },
      comparative_costs: comparativeCosts
    })
  }

  if (urlPath === '/ai/providers' && method === 'get') {
    return ok(db.providers || [])
  }

  if (urlPath === '/ai/providers' && method === 'post') {
    const newProvider = {
      id: `prov_demo_${Date.now()}`,
      name: data.name,
      provider_type: data.provider_type || 'openai',
      base_url: data.base_url || null,
      api_key_masked: data.api_key ? 'sk-...masked' : 'Not Required / Local',
      max_concurrency: data.max_concurrency || 1,
      is_active: data.is_active !== undefined ? data.is_active : true,
      is_fallback: data.is_fallback || false,
      input_cost_per_million: parseFloat(data.input_cost_per_million) || 0.0,
      output_cost_per_million: parseFloat(data.output_cost_per_million) || 0.0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    db.providers = [...(db.providers || []), newProvider]
    saveDemoDb(db)
    return ok(newProvider, 201)
  }

  const provMatch = urlPath.match(/^\/ai\/providers\/([^/]+)$/)
  if (provMatch) {
    const pId = provMatch[1]
    const pIdx = (db.providers || []).findIndex((p) => String(p.id) === String(pId))

    if (method === 'patch' || method === 'put') {
      if (pIdx === -1) throw new Error('Provider not found')
      db.providers[pIdx] = {
        ...db.providers[pIdx],
        ...data,
        updated_at: new Date().toISOString(),
      }
      saveDemoDb(db)
      return ok(db.providers[pIdx])
    }

    if (method === 'delete') {
      if (pIdx !== -1) {
        db.providers.splice(pIdx, 1)
        saveDemoDb(db)
      }
      return ok({ message: 'Provider deleted' })
    }
  }

  const provTestMatch = urlPath.match(/^\/ai\/providers\/([^/]+)\/test$/)
  if (provTestMatch && method === 'post') {
    return ok({ status: 'success', message: 'Provider endpoint healthy and reachable (18ms)' })
  }

  if (urlPath === '/ai/bindings' && method === 'get') {
    return ok(db.bindings || [])
  }

  const bindingTaskMatch = urlPath.match(/^\/ai\/bindings\/([^/]+)$/)
  if (bindingTaskMatch && (method === 'put' || method === 'post')) {
    const taskType = bindingTaskMatch[1]
    const idx = (db.bindings || []).findIndex((b) => b.task_type === taskType)
    const newBinding = { task_type: taskType, ...data }
    if (idx !== -1) {
      db.bindings[idx] = newBinding
    } else {
      db.bindings = [...(db.bindings || []), newBinding]
    }
    saveDemoDb(db)
    return ok(newBinding)
  }

  if (urlPath === '/ai/pricing-rates' && method === 'get') {
    return ok(db.pricing_rates || [
      { key: 'local_baseline', display_name: 'Local LLM Benchmark (Savings Baseline)', provider: 'local', input_cost_per_million: 0.15, output_cost_per_million: 0.60 },
      { key: 'gpt-4o', display_name: 'OpenAI GPT-4o', provider: 'openai', input_cost_per_million: 2.50, output_cost_per_million: 10.00 },
      { key: 'gpt-4o-mini', display_name: 'OpenAI GPT-4o Mini', provider: 'openai', input_cost_per_million: 0.15, output_cost_per_million: 0.60 },
      { key: 'claude-3-5-sonnet', display_name: 'Anthropic Claude 3.5 Sonnet', provider: 'anthropic', input_cost_per_million: 3.00, output_cost_per_million: 15.00 },
      { key: 'claude-3-5-haiku', display_name: 'Anthropic Claude 3.5 Haiku', provider: 'anthropic', input_cost_per_million: 0.80, output_cost_per_million: 4.00 },
      { key: 'gemini-2.0-flash', display_name: 'Google Gemini 2.0 Flash', provider: 'gemini', input_cost_per_million: 0.10, output_cost_per_million: 0.40 },
      { key: 'deepseek-chat', display_name: 'DeepSeek V3', provider: 'deepseek', input_cost_per_million: 0.14, output_cost_per_million: 0.28 },
    ])
  }

  if (urlPath === '/ai/pricing-rates' && (method === 'put' || method === 'post')) {
    const updatedRates = data.rates || data
    db.pricing_rates = updatedRates
    saveDemoDb(db)
    return ok(db.pricing_rates)
  }

  if (urlPath === '/ai/pricing-rates/reset' && method === 'post') {
    db.pricing_rates = [
      { key: 'local_baseline', display_name: 'Local LLM Benchmark (Savings Baseline)', provider: 'local', input_cost_per_million: 0.15, output_cost_per_million: 0.60 },
      { key: 'gpt-4o', display_name: 'OpenAI GPT-4o', provider: 'openai', input_cost_per_million: 2.50, output_cost_per_million: 10.00 },
      { key: 'gpt-4o-mini', display_name: 'OpenAI GPT-4o Mini', provider: 'openai', input_cost_per_million: 0.15, output_cost_per_million: 0.60 },
      { key: 'claude-3-5-sonnet', display_name: 'Anthropic Claude 3.5 Sonnet', provider: 'anthropic', input_cost_per_million: 3.00, output_cost_per_million: 15.00 },
      { key: 'claude-3-5-haiku', display_name: 'Anthropic Claude 3.5 Haiku', provider: 'anthropic', input_cost_per_million: 0.80, output_cost_per_million: 4.00 },
      { key: 'gemini-2.0-flash', display_name: 'Google Gemini 2.0 Flash', provider: 'gemini', input_cost_per_million: 0.10, output_cost_per_million: 0.40 },
      { key: 'deepseek-chat', display_name: 'DeepSeek V3', provider: 'deepseek', input_cost_per_million: 0.14, output_cost_per_million: 0.28 },
    ]
    saveDemoDb(db)
    return ok(db.pricing_rates)
  }

  if (urlPath === '/ai/global-settings' && method === 'get') {
    return ok({
      DISPLAY_TIMEZONE: db.system_settings?.DISPLAY_TIMEZONE || null,
      TIMEZONE_SOURCE: db.system_settings?.TIMEZONE_SOURCE || 'auto',
      HAS_COMPLETED_ONBOARDING: db.system_settings?.has_completed_onboarding ?? true,
      ENABLE_EMAIL_INTAKE: db.system_settings?.enable_email_intake ?? true,
      ENABLE_EMBEDDINGS: db.system_settings?.enable_embeddings ?? true,
      ENABLE_AUTO_COVER_LETTER: db.system_settings?.enable_auto_cover_letter ?? true,
      COVER_LETTER_MATCH_THRESHOLD: db.system_settings?.cover_letter_match_threshold ?? 70,
      COVER_LETTER_LENGTH: db.system_settings?.cover_letter_length ?? 'standard',
      COVER_LETTER_TONE: db.system_settings?.cover_letter_tone ?? 'professional',
    })
  }

  if (urlPath === '/ai/global-settings' && method === 'patch') {
    db.system_settings = getDemoDb().system_settings
    if (data.TIMEZONE_SOURCE === 'auto' && db.system_settings?.TIMEZONE_SOURCE === 'manual' && !data.RESET_TIMEZONE_OVERRIDE) {
      data.DISPLAY_TIMEZONE = db.system_settings.DISPLAY_TIMEZONE
      data.TIMEZONE_SOURCE = 'manual'
    }
    db.system_settings = {
      ...(db.system_settings || {}),
      ...(data.COVER_LETTER_TONE ? { cover_letter_tone: data.COVER_LETTER_TONE } : {}),
      ...(data.cover_letter_tone ? { cover_letter_tone: data.cover_letter_tone } : {}),
      ...data,
    }
    saveDemoDb(db)
    return ok({
      DISPLAY_TIMEZONE: db.system_settings?.DISPLAY_TIMEZONE || null,
      TIMEZONE_SOURCE: db.system_settings?.TIMEZONE_SOURCE || 'auto',
      HAS_COMPLETED_ONBOARDING: db.system_settings?.has_completed_onboarding ?? true,
      ENABLE_EMAIL_INTAKE: db.system_settings?.enable_email_intake ?? true,
      ENABLE_EMBEDDINGS: db.system_settings?.enable_embeddings ?? true,
      ENABLE_AUTO_COVER_LETTER: db.system_settings?.enable_auto_cover_letter ?? true,
      COVER_LETTER_MATCH_THRESHOLD: db.system_settings?.cover_letter_match_threshold ?? 70,
      COVER_LETTER_LENGTH: db.system_settings?.cover_letter_length ?? 'standard',
      COVER_LETTER_TONE: db.system_settings?.cover_letter_tone ?? 'professional',
    })
  }

  if (urlPath === '/email_accounts' && method === 'get') {
    return ok([
      {
        id: "email_demo_001",
        email: "alex.rivera@example.com",
        provider: "IMAP",
        is_active: true,
        last_synced_at: new Date().toISOString()
      }
    ])
  }

  // 8. INTERVIEW SIMULATOR ENDPOINTS
  if (urlPath === '/interviews/sessions/start' && method === 'post') {
    const newSession = {
      id: `session_demo_${Date.now()}`,
      application_id: data.application_id,
      company_name: data.company_name || 'Target Company',
      position: data.position || 'Target Position',
      persona: data.persona || 'TECHNICAL_BAR_RAISER',
      persona_label: data.persona_label || 'Technical Bar Raiser',
      status: 'IN_PROGRESS',
      turns_data: [
        {
          turn_number: 1,
          question: "Let's dive right in. Can you describe a challenging architectural trade-off you made in your recent work?",
          user_answer: null,
          score: null,
        },
      ],
      readiness_score: 85,
      summary_feedback: null,
      created_at: new Date().toISOString(),
    }
    db.interview_sessions = [newSession, ...(db.interview_sessions || [])]
    saveDemoDb(db)
    return ok(newSession)
  }

  const evalAnswerMatch = urlPath.match(/^\/interviews\/sessions\/([^/]+)\/evaluate-answer$/)
  if (evalAnswerMatch && method === 'post') {
    const sessionId = evalAnswerMatch[1]
    const session = (db.interview_sessions || []).find((s) => s.id === sessionId)
    if (session) {
      const turnNumber = session.turns_data.length
      const lastTurn = session.turns_data[turnNumber - 1]
      lastTurn.user_answer = data.user_answer || data.answer
      lastTurn.score = 90
      lastTurn.star_breakdown = { situation: true, task: true, action: true, result: true }
      lastTurn.feedback = 'Strong elaboration of technical design and operational metrics.'
      lastTurn.exemplar_rewrite = 'I structured the message broker architecture using distributed log partitions to prevent consumer lag.'
      session.readiness_score = Math.min(95, session.readiness_score + 2)
      saveDemoDb(db)
    }
    return ok({
      score: 90,
      star_breakdown: { situation: true, task: true, action: true, result: true },
      feedback: 'Strong elaboration of technical design and operational metrics.',
      exemplar_rewrite: 'I structured the message broker architecture using distributed log partitions to prevent consumer lag.',
      readiness_score: session?.readiness_score || 90,
    })
  }

  const nextQuestionMatch = urlPath.match(/^\/interviews\/sessions\/([^/]+)\/next-question$/)
  if (nextQuestionMatch && method === 'post') {
    const sessionId = nextQuestionMatch[1]
    const session = (db.interview_sessions || []).find((s) => s.id === sessionId)
    let nextQ = 'How do you handle production incidents and perform post-mortem root cause analyses?'
    if (session) {
      const turnNum = session.turns_data.length + 1
      if (turnNum === 2) {
        nextQ = 'How do you handle production incidents and perform post-mortem root cause analyses?'
      } else if (turnNum >= 3) {
        nextQ = 'Tell me about a time you had a technical disagreement with a peer or stakeholder and how you resolved it.'
      }
      session.turns_data.push({
        turn_number: turnNum,
        question: nextQ,
        user_answer: null,
        score: null,
      })
      saveDemoDb(db)
    }
    return ok({ question: nextQ })
  }

  const finalizeSessionMatch = urlPath.match(/^\/interviews\/sessions\/([^/]+)\/finalize$/)
  if (finalizeSessionMatch && method === 'post') {
    const sessionId = finalizeSessionMatch[1]
    const session = (db.interview_sessions || []).find((s) => s.id === sessionId)
    if (session) {
      session.status = 'COMPLETED'
      session.summary_feedback = 'Excellent overall performance demonstrating deep technical engineering principles and structured STAR responses.'
      saveDemoDb(db)
    }
    return ok(session || {})
  }

  const sessionDetailMatch = urlPath.match(/^\/interviews\/sessions\/([^/]+)$/)
  if (sessionDetailMatch && method === 'get') {
    const sessionId = sessionDetailMatch[1]
    const session = (db.interview_sessions || []).find((s) => s.id === sessionId)
    return ok(session || {})
  }

  if (urlPath === '/interviews/sessions' && method === 'get') {
    return ok(db.interview_sessions || [])
  }

  // 9. AGENT CHAT ENDPOINTS
  if (urlPath === '/agent/chats' && method === 'get') {
    const list = db.agent_chats || []
    return ok(
      list.map((c) => ({
        id: c.id,
        title: c.title,
        created_at: c.created_at,
        updated_at: c.updated_at,
      }))
    )
  }

  const agentChatDetailMatch = urlPath.match(/^\/agent\/chats\/([^/]+)$/)
  if (agentChatDetailMatch) {
    const chatId = agentChatDetailMatch[1]
    const chatIndex = (db.agent_chats || []).findIndex((c) => c.id === chatId)
    if (method === 'get') {
      if (chatIndex === -1) throw new Error('Chat not found')
      return ok(db.agent_chats[chatIndex])
    }
    if (method === 'delete') {
      if (chatIndex !== -1) {
        db.agent_chats.splice(chatIndex, 1)
        saveDemoDb(db)
      }
      return ok({ message: 'Chat deleted' })
    }
  }

  if (urlPath === '/agent/chat' && method === 'post') {
    const messages = data.messages || []
    const lastUserMsg = messages[messages.length - 1]?.content || 'Hello'
    let chatId = data.chat_id
    let chat = (db.agent_chats || []).find((c) => c.id === chatId)

    if (!chat) {
      chatId = `chat_${Date.now()}`
      chat = {
        id: chatId,
        title: lastUserMsg.slice(0, 30) + '...',
        created_at: new Date().toISOString(),
        messages: [],
      }
      db.agent_chats = [chat, ...(db.agent_chats || [])]
    }

    const replyText = getDemoAgentReply(db, lastUserMsg)

    const assistantMsg = {
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: replyText,
    }

    chat.messages.push({ id: `msg_${Date.now() - 1}`, role: 'user', content: lastUserMsg })
    chat.messages.push(assistantMsg)
    saveDemoDb(db)

    return ok({
      reply: assistantMsg.content,
      chat_id: chatId,
      actions_performed: [],
    })
  }

  // 10. SEARCH & ANALYTICS ENDPOINTS
  if (urlPath === '/analytics/recalculate' && method === 'post') {
    return ok({ status: 'ok', message: 'Analytics cache cleared and recalculated' })
  }

  if (urlPath === '/search/semantic' && method === 'get') {
    const query = (params.query || '').toLowerCase()
    const matches = (db.applications || []).filter(
      (a) =>
        a.company_name?.toLowerCase().includes(query) ||
        a.position?.toLowerCase().includes(query) ||
        a.description?.toLowerCase().includes(query)
    )
    return ok({ results: matches })
  }

  if (urlPath === '/search/companies' && method === 'get') {
    const q = (params.q || '').toLowerCase().trim()
    const matches = (db.companies || [])
      .filter((c) => !q || c.name?.toLowerCase().includes(q) || c.domain?.toLowerCase().includes(q))
      .map((c) => ({
        id: c.id,
        name: c.name,
        domain: c.domain,
        rating: c.rating,
      }))
    return ok(matches)
  }

  if (urlPath === '/analytics/overview' && method === 'get') {
    const apps = db.applications || []
    const totalApps = apps.length
    const activeCount = apps.filter((a) => ['APPLIED', 'TECHNICAL_INTERVIEW', 'OFFER'].includes(a.status)).length
    const offerCount = apps.filter((a) => a.status === 'OFFER' || a.status === 'HIRED').length
    const interviewCount = apps.filter((a) => a.status === 'TECHNICAL_INTERVIEW' || a.status === 'OFFER' || a.status === 'HIRED').length

    const remoteCount = apps.filter(a => (a.work_model || '').toLowerCase() === 'remote').length
    const hybridCount = apps.filter(a => (a.work_model || '').toLowerCase() === 'hybrid').length
    const onsiteCount = apps.filter(a => (a.work_model || '').toLowerCase() === 'on-site' || (a.work_model || '').toLowerCase() === 'onsite').length
    const unknownCount = totalApps - remoteCount - hybridCount - onsiteCount

    return ok({
      total_applications: totalApps,
      active_pipeline_count: activeCount,
      interview_rate: totalApps > 0 ? (interviewCount / totalApps) * 100 : 0,
      offer_rate: totalApps > 0 ? (offerCount / totalApps) * 100 : 0,
      average_fit_score: 90.0,
      top_in_demand_skills: [
        { skill: "Go", count: 4, is_in_candidate_cv: true, avg_salary_min: 240000, avg_salary_max: 290000 },
        { skill: "Rust", count: 3, is_in_candidate_cv: true, avg_salary_min: 230000, avg_salary_max: 280000 },
        { skill: "Distributed Systems", count: 5, is_in_candidate_cv: true, avg_salary_min: 220000, avg_salary_max: 290000 },
        { skill: "PostgreSQL", count: 2, is_in_candidate_cv: true, avg_salary_min: 210000, avg_salary_max: 260000 },
        { skill: "eBPF Kernel Tracing", count: 1, is_in_candidate_cv: false, avg_salary_min: 220000, avg_salary_max: 270000 }
      ],
      priority_skill_gaps: [
        { skill: "eBPF Kernel Tracing", priority_score: 8.5, missing_frequency: 2, sample_companies: ["Datadog"] },
        { skill: "GraphQL Schema Mesh", priority_score: 6.2, missing_frequency: 1, sample_companies: ["Linear"] }
      ],
      pipeline_funnel: [
        {
          stage: "Applied",
          count: totalApps,
          conversion_rate: 100,
          dropoff_rate: 10,
          dropped_count: 1,
          active_count: 2,
          rejected_count: 1,
          archived_count: 0,
          withdrawn_count: 0,
        },
        {
          stage: "Interview",
          count: interviewCount,
          conversion_rate: 40,
          dropoff_rate: 20,
          dropped_count: 1,
          active_count: 1,
          rejected_count: 0,
          archived_count: 1,
          withdrawn_count: 0,
        },
        {
          stage: "Offer",
          count: offerCount,
          conversion_rate: 20,
          dropoff_rate: 0,
          dropped_count: 0,
          active_count: 1,
          rejected_count: 0,
          archived_count: 0,
          withdrawn_count: 0,
        }
      ],
      work_model_distribution: {
        remote_count: remoteCount,
        hybrid_count: hybridCount,
        onsite_count: onsiteCount,
        unknown_count: unknownCount
      },
      salary_insights: [
        { skill: "Go", avg_min: 240000, avg_max: 290000 },
        { skill: "Rust", avg_min: 220000, avg_max: 280000 },
        { skill: "C++", avg_min: 230000, avg_max: 310000 }
      ]
    })
  }

  if (urlPath === '/analytics/role-alignment' && method === 'get') {
    const selectedTrack = params.role_track || 'all'
    const totalJobs = (db.applications || []).length || 25
    return ok({
      detected_tracks: [
        { key: "all", label: "All Tracks", job_count: totalJobs },
        { key: "backend", label: "Backend Engineering", job_count: 18 },
        { key: "fullstack", label: "Full-Stack Engineering", job_count: 12 },
        { key: "data_ai", label: "AI & Data Engineering", job_count: 6 },
        { key: "devops", label: "DevOps & Cloud SRE", job_count: 4 },
      ],
      selected_track: selectedTrack,
      total_analyzed_jobs: selectedTrack === 'backend' ? 18 : totalJobs,
      vocabulary_shifts: [
        {
          cv_term: "SQL database",
          jd_term: "PostgreSQL",
          frequency_count: 14,
          frequency_pct: 77.8,
          rationale: "Aligns candidate relational database experience with employer ATS standard."
        },
        {
          cv_term: "Message Queue",
          jd_term: "Apache Kafka",
          frequency_count: 11,
          frequency_pct: 61.1,
          rationale: "Explicitly highlights event-driven streaming architecture competencies."
        },
        {
          cv_term: "Python scripts",
          jd_term: "FastAPI Async Services",
          frequency_count: 9,
          frequency_pct: 50.0,
          rationale: "Emphasizes production microservice API frameworks."
        },
        {
          cv_term: "In-memory Cache",
          jd_term: "Redis Cluster / Valkey",
          frequency_count: 8,
          frequency_pct: 44.4,
          rationale: "Demonstrates distributed caching and session state scaling."
        },
        {
          cv_term: "Container Deployment",
          jd_term: "Docker / Kubernetes (k8s)",
          frequency_count: 7,
          frequency_pct: 38.9,
          rationale: "Matches enterprise cloud container orchestration standards."
        },
        {
          cv_term: "CI/CD Pipeline",
          jd_term: "GitHub Actions / ArgoCD",
          frequency_count: 6,
          frequency_pct: 33.3,
          rationale: "Reflects automated deployment and GitOps practices."
        },
        {
          cv_term: "System Metrics",
          jd_term: "Prometheus & Grafana",
          frequency_count: 5,
          frequency_pct: 27.8,
          rationale: "Quantifies production telemetry and observability."
        },
        {
          cv_term: "REST API",
          jd_term: "gRPC & OpenAPI 3.0",
          frequency_count: 4,
          frequency_pct: 22.2,
          rationale: "Highlights high-performance binary protocol experience."
        },
        {
          cv_term: "NoSQL storage",
          jd_term: "DynamoDB / Cassandra",
          frequency_count: 4,
          frequency_pct: 22.2,
          rationale: "Demonstrates wide-column distributed key-value store expertise."
        },
        {
          cv_term: "Tracing",
          jd_term: "OpenTelemetry / Jaeger",
          frequency_count: 3,
          frequency_pct: 16.7,
          rationale: "Presents distributed request tracing capabilities."
        }
      ],
      bullet_reframes: [
        {
          original_bullet: "Engineered scalable services for CloudTech.",
          suggested_rewrite: "Architected high-throughput microservices for CloudTech handling 20,000 req/sec with 99.99% reliability.",
          reason: "Quantifies throughput metrics and aligns with senior backend requirements.",
          frequency_count: 12
        },
        {
          original_bullet: "Managed database queries and performance.",
          suggested_rewrite: "Optimized PostgreSQL query execution plans and index partitioning, reducing p99 latency by 45%.",
          reason: "Highlights concrete performance optimization and database tuning outcome.",
          frequency_count: 8
        },
        {
          original_bullet: "Built API endpoints for client applications.",
          suggested_rewrite: "Designed asynchronous FastAPI and gRPC services handling over 5M daily API calls.",
          reason: "Emphasizes async execution and modern protocol adoption.",
          frequency_count: 7
        },
        {
          original_bullet: "Set up CI/CD automation for releases.",
          suggested_rewrite: "Streamlined deployment pipelines with GitHub Actions & ArgoCD, reducing release lead time from 3 days to 15 mins.",
          reason: "Showcases measurable DevOps efficiency and GitOps automation.",
          frequency_count: 6
        },
        {
          original_bullet: "Handled system bugs and outages.",
          suggested_rewrite: "Established Prometheus alert rules and OpenTelemetry tracing, reducing MTTR by 60% during critical incidents.",
          reason: "Demonstrates proactive observability and incident management.",
          frequency_count: 5
        }
      ]
    })
  }

  if (urlPath === '/analytics/funnel' && method === 'get') {
    const period = params.period || 'weekly'
    return ok({
      period_type: period,
      summary_kpis: {
        intakes: { label: "Total Intake Leads", value: 14, trend_percentage: 12.0, is_positive: true },
        applications: { label: "Submitted Applications", value: 10, trend_percentage: 8.5, is_positive: true },
        interviews: { label: "Interview Conversions", value: 4, trend_percentage: 25.0, is_positive: true },
        offers: { label: "Offers Received", value: 2, trend_percentage: 50.0, is_positive: true }
      },
      chart_data: [
        { period_key: "P1", period_label: "W01", start_date: "2025-01-01", end_date: "2025-01-07", intakes: 10, applications: 7, interviews: 2, offers: 1, conversion_rate: 28.5 },
        { period_key: "P2", period_label: "W02", start_date: "2025-01-08", end_date: "2025-01-14", intakes: 14, applications: 10, interviews: 4, offers: 2, conversion_rate: 40.0 }
      ],
      table_data: [
        { period_key: "P2", period_label: "W02", start_date: "2025-01-08", end_date: "2025-01-14", intakes: 14, applications: 10, interviews: 4, offers: 2, conversion_rate: 40.0 },
        { period_key: "P1", period_label: "W01", start_date: "2025-01-01", end_date: "2025-01-07", intakes: 10, applications: 7, interviews: 2, offers: 1, conversion_rate: 28.5 }
      ]
    })
  }

  if (urlPath === '/analytics/role-alignment/dossier' && method === 'get') {
    const track = params.role_track || 'all'
    return ok({
      id: 1,
      cv_id: 1,
      role_track: track,
      model_name: "gpt-4o",
      input_tokens: 1250,
      output_tokens: 680,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      dossier: {
        executive_fit: {
          market_competitiveness_rating: "STRONG",
          positioning_summary: "High-caliber Distributed Systems & Backend profile with deep expertise in asynchronous messaging, Python/Go, and cloud-native scaling. Highly aligned with Tier-1 Tech backend requirements.",
          competitive_advantages: [
            "Demonstrated mastery in high-throughput gRPC and Kafka event stream architectures",
            "Strong track record in Postgres query profiling and database scaling",
            "Robust end-to-end CI/CD and observability implementation across microservices"
          ],
          primary_vulnerabilities: [
            "Limited explicit mention of Kubernetes operator development or deep eBPF observability",
            "Opportunity to showcase more multi-region cross-cloud active-active failover design"
          ]
        },
        bullet_rewrites: [
          {
            original_bullet: "Built backend APIs and microservices for core product platform.",
            rewritten_bullet: "Architected distributed asynchronous microservices in FastAPI & gRPC, scaling throughput by 3.5x to handle 10M+ daily events with 99.99% availability.",
            target_competency: "High-Throughput Distributed Architecture",
            impact_quantification: "3.5x throughput scale, 10M+ daily events, 99.99% SLA"
          },
          {
            original_bullet: "Improved database performance and fixed query bottlenecks.",
            rewritten_bullet: "Optimized complex PostgreSQL queries and connection pooling via pgvector/pgBouncer, cutting p99 query latency from 850ms to 42ms.",
            target_competency: "Database Performance & Query Tuning",
            impact_quantification: "95% p99 latency reduction (850ms to 42ms)"
          },
          {
            original_bullet: "Implemented observability and monitoring dashboards.",
            rewritten_bullet: "Instrumented OpenTelemetry distributed tracing and Prometheus metrics across 24 microservices, reducing Mean Time to Resolution (MTTR) by 60%.",
            target_competency: "Production Observability & SRE",
            impact_quantification: "60% MTTR reduction across 24 microservices"
          }
        ],
        talking_points: [
          {
            topic_area: "Distributed Consensus & Idempotency",
            technical_story_hook: "Resolving duplicate event processing across a multi-partition Kafka pipeline using Redis-backed distributed locks and transactional outbox patterns.",
            key_takeaway: "Deep understanding of at-least-once delivery trade-offs and zero-data-loss consistency guarantees.",
            sample_questions: [
              "How do you design an idempotent webhook consumer that survives worker node crashes?",
              "What strategies do you use to prevent duplicate writes during network partitions?"
            ]
          },
          {
            topic_area: "High-Concurrency Async Architecture",
            technical_story_hook: "Refactoring synchronous I/O blocking routes to native Python AsyncIO/uvloop with worker connection pooling.",
            key_takeaway: "Proactive resource optimization reducing server compute costs while doubling concurrency limits.",
            sample_questions: [
              "How do you diagnose event loop blocking in async Python runtimes?",
              "When would you choose gRPC over HTTP/2 REST for inter-service communication?"
            ]
          }
        ],
        skill_bridge_roadmap: [
          {
            skill_or_tool: "Kubernetes & Helm",
            category: "Cloud & Orchestration",
            rationale: "Required in 85% of Senior/Staff Backend job postings in this track.",
            learning_priority: "HIGH",
            recommended_actions: [
              "Deploy a multi-tier FastAPI + PostgreSQL application to a local KinD/k3s cluster using custom Helm charts.",
              "Configure Horizontal Pod Autoscaling (HPA) based on custom Prometheus request metrics."
            ]
          },
          {
            skill_or_tool: "eBPF / Advanced Tracing",
            category: "Observability",
            rationale: "Differentiates Staff-level candidates in latency-critical infrastructure roles.",
            learning_priority: "MEDIUM",
            recommended_actions: [
              "Experiment with Cilium or Pixie for zero-code network profiling in test environments."
            ]
          }
        ]
      }
    })
  }

  if (urlPath === '/analytics/role-alignment/enhance' && method === 'post') {
    const track = params.role_track || 'all'
    return ok({
      id: 1,
      cv_id: 1,
      role_track: track,
      model_name: "gpt-4o",
      input_tokens: 1420,
      output_tokens: 720,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      dossier: {
        executive_fit: {
          market_competitiveness_rating: "EXCEPTIONAL",
          positioning_summary: "Generated AI Dossier: Exceptional alignment with modern distributed backend engineering standards.",
          competitive_advantages: [
            "Strong command of asynchronous concurrency and distributed systems",
            "High database tuning competency with PostgreSQL and pgvector",
            "Proven ability to reduce latency and system MTTR"
          ],
          primary_vulnerabilities: [
            "Add more explicit Kubernetes operator and multi-region deployment evidence"
          ]
        },
        bullet_rewrites: [
          {
            original_bullet: "Built backend APIs and microservices for core product platform.",
            rewritten_bullet: "Architected distributed asynchronous microservices in FastAPI & gRPC, scaling throughput by 3.5x to handle 10M+ daily events with 99.99% availability.",
            target_competency: "High-Throughput Distributed Architecture",
            impact_quantification: "3.5x throughput scale, 10M+ daily events, 99.99% SLA"
          }
        ],
        talking_points: [
          {
            topic_area: "Distributed Consensus & Idempotency",
            technical_story_hook: "Resolving duplicate event processing across Kafka partitions.",
            key_takeaway: "Deep understanding of zero-data-loss consistency guarantees.",
            sample_questions: ["How do you design an idempotent webhook consumer?"]
          }
        ],
        skill_bridge_roadmap: [
          {
            skill_or_tool: "Kubernetes & Helm",
            category: "Cloud & Orchestration",
            rationale: "Required in 85% of Senior Backend job postings.",
            learning_priority: "HIGH",
            recommended_actions: ["Deploy a multi-tier app on KinD with custom Helm charts."]
          }
        ]
      }
    })
  }

  if (urlPath === '/prompts' && method === 'get') {
    return ok([])
  }

  // 11. COMPANIES ENDPOINTS
  if (urlPath === '/companies' && method === 'post') {
    const name = data.name?.trim()
    if (!name) {
      return { status: 400, data: { detail: 'Company name is required' } }
    }
    const company = {
      id: `comp_demo_${Date.now()}`,
      name,
      name_normalized: name.toLowerCase(),
      domain: data.domain?.trim() || null,
      about_url: data.about_url?.trim() || null,
      rating: null,
      notes: '',
      pros: [],
      red_flags: [],
      company_research: null,
      researched_at: null,
      research_status: data.queue_research ? 'QUEUED' : 'NONE',
      application_count: 0,
      active_applications_count: 0,
    }
    db.companies = [...(db.companies || []), company]
    saveDemoDb(db)
    return ok(company)
  }

  if (urlPath === '/companies' && method === 'get') {
    let allItems = [...(db.companies || [])]

    // Calculate application_count & applications dynamically from db.applications
    allItems = allItems.map((c) => {
      const apps = (db.applications || []).filter(
        (a) =>
          String(a.company_id) === String(c.id) ||
          a.company_name?.toLowerCase() === c.name?.toLowerCase()
      )
      const activeCount = apps.filter((a) =>
        ['APPLIED', 'ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW', 'OFFER'].includes(a.status)
      ).length
      return {
        ...c,
        applications_count: apps.length,
        active_applications_count: activeCount,
        application_count: apps.length,
      }
    })

    // Compute global directory stats before filtering
    const totalCompanies = allItems.length
    const withActive = allItems.filter((c) => (c.active_applications_count || 0) > 0).length
    const researchedCount = allItems.filter(
      (c) => c.company_research && c.company_research.summary
    ).length
    const totalApps = (db.applications || []).length
    const stats = {
      total: totalCompanies,
      with_active: withActive,
      researched_count: researchedCount,
      total_applications: totalApps,
      unresearched_count: Math.max(0, totalCompanies - researchedCount),
    }

    let items = allItems

    // 1. Text Search Filter (name, domain, notes, research summary)
    if (params.q) {
      const q = params.q.toLowerCase().trim()
      items = items.filter(
        (c) =>
          c.name?.toLowerCase().includes(q) ||
          c.domain?.toLowerCase().includes(q) ||
          c.notes?.toLowerCase().includes(q) ||
          c.company_research?.summary?.toLowerCase().includes(q)
      )
    }

    // 2. Filter missing research
    if (params.without_research === 'true' || params.without_research === true) {
      items = items.filter(
        (c) => !c.company_research || !c.company_research.summary
      )
    }

    // 3. Duplicate IDs filter
    if (params.duplicate_ids) {
      const ids = String(params.duplicate_ids)
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      if (ids.length) {
        items = items.filter((c) => ids.includes(String(c.id)))
      }
    }

    // 4. Sorting
    const sortBy = params.sort_by || 'applications'
    const sortOrder = (params.sort_order || 'desc').toLowerCase()
    const isAsc = sortOrder === 'asc'

    items.sort((a, b) => {
      if (sortBy === 'name') {
        const res = (a.name || '').localeCompare(b.name || '')
        return isAsc ? res : -res
      }
      if (sortBy === 'recent') {
        const dateA = a.last_applied_at ? new Date(a.last_applied_at).getTime() : 0
        const dateB = b.last_applied_at ? new Date(b.last_applied_at).getTime() : 0
        return isAsc ? dateA - dateB : dateB - dateA
      }
      // Default: 'applications'
      const countA = a.applications_count || 0
      const countB = b.applications_count || 0
      return isAsc ? countA - countB : countB - countA
    })

    const total = items.length
    const limit = Number(params.limit) || 50
    const offset = Number(params.offset) || 0
    const pagedItems = items.slice(offset, offset + limit)

    return ok({
      items: pagedItems,
      total,
      limit,
      offset,
      stats,
    })
  }

  if (urlPath === '/companies/duplicates' && method === 'get') {
    const list = db.companies || []
    const domainMap = {}
    list.forEach((c) => {
      if (c.domain) {
        const dom = c.domain.toLowerCase().trim()
        domainMap[dom] = domainMap[dom] || []
        domainMap[dom].push(c)
      }
    })
    const clusters = []
    const duplicateIds = new Set()
    Object.entries(domainMap).forEach(([dom, comps]) => {
      if (comps.length > 1) {
        comps.forEach((c) => duplicateIds.add(c.id))
        clusters.push({
          canonical_name: comps[0].name,
          cluster_size: comps.length,
          companies: comps.map((c) => ({
            id: c.id,
            name: c.name,
            domain: c.domain,
            application_count: (db.applications || []).filter(
              (a) => String(a.company_id) === String(c.id) || a.company_name?.toLowerCase() === c.name?.toLowerCase()
            ).length,
          })),
        })
      }
    })
    return ok({
      total_clusters: clusters.length,
      total_duplicate_companies: duplicateIds.size,
      duplicate_company_ids: Array.from(duplicateIds),
      clusters,
    })
  }

  if (urlPath === '/companies/merge' && method === 'post') {
    const primaryId = data.primary_company_id
    const duplicateId = data.duplicate_company_id
    const primaryIdx = (db.companies || []).findIndex((c) => String(c.id) === String(primaryId))
    const duplicate = (db.companies || []).find((c) => String(c.id) === String(duplicateId))
    if (primaryIdx !== -1 && duplicate) {
      // Reassign applications
      (db.applications || []).forEach((a) => {
        if (String(a.company_id) === String(duplicateId) || a.company_name?.toLowerCase() === duplicate.name?.toLowerCase()) {
          a.company_id = db.companies[primaryIdx].id
          a.company_name = db.companies[primaryIdx].name
          if (a.company) {
            a.company.id = db.companies[primaryIdx].id
            a.company.name = db.companies[primaryIdx].name
            a.company.domain = db.companies[primaryIdx].domain
          }
        }
      })
      // Delete duplicate company
      db.companies = db.companies.filter((c) => String(c.id) !== String(duplicateId))
      saveDemoDb(db)
      return ok({
        status: 'success',
        message: 'Companies merged successfully',
        primary_company_id: primaryId,
      })
    }
    return { status: 400, data: { detail: 'Failed to merge companies' } }
  }

  if (urlPath === '/companies/bulk-research' && method === 'post') {
    const count = (db.companies || []).length
    return ok({ enqueued_count: count, skipped_count: 0 })
  }

  const refreshResearchMatch = urlPath.match(/^\/companies\/([^/]+)\/refresh-research$/)
  if (refreshResearchMatch && method === 'post') {
    const cid = refreshResearchMatch[1]
    const idx = (db.companies || []).findIndex((c) => String(c.id) === String(cid))
    if (idx !== -1) {
      db.companies[idx].research_status = 'COMPLETED'
      db.companies[idx].researched_at = new Date().toISOString()
      if (!db.companies[idx].company_research) {
        db.companies[idx].company_research = {
          summary: `${db.companies[idx].name} is a leading enterprise technology company building cloud software.`,
          engineering_culture: "Modern engineering practices with continuous delivery and high technical excellence.",
          recent_initiatives: "Product line expansion, platform infrastructure optimization, and AI automation.",
          products_and_technical_domain: ["Core Platform", "Cloud Infrastructure"],
          strategic_priorities: ["Customer satisfaction", "Platform reliability", "High availability"],
          language_to_mirror: ["Quality-driven", "High reliability", "First-principles engineering"],
          candidate_alignment_angles: ["Highlight distributed systems scalability and observability"],
          verified_facts: [
            { fact: "Enterprise operations across multiple global regions", confidence: "high", source_url: `https://${db.companies[idx].domain || 'example.com'}` }
          ],
          employee_signals: [
            { signal: "Values cross-functional collaboration and clear documentation" }
          ],
          public_rating_snippet: "4.2 / 5.0",
          sources: [`https://${db.companies[idx].domain || 'example.com'}`],
        }
      }
      saveDemoDb(db)
      return ok(db.companies[idx])
    }
    return { status: 404, data: { detail: 'Company not found' } }
  }

  const companyIdMatch = urlPath.match(/^\/companies\/([^/]+)$/)
  if (companyIdMatch && method === 'get') {
    const cid = companyIdMatch[1]
    const company = (db.companies || []).find(
      (c) => String(c.id) === String(cid) || c.name?.toLowerCase() === cid.toLowerCase()
    )
    if (!company) {
      return { status: 404, data: { detail: 'Company not found' } }
    }
    const apps = (db.applications || []).filter(
      (a) =>
        String(a.company_id) === String(company.id) ||
        a.company_name?.toLowerCase() === company.name?.toLowerCase()
    )
    return ok({ ...company, applications: apps, application_count: apps.length })
  }

  if (companyIdMatch && method === 'patch') {
    const cid = companyIdMatch[1]
    const idx = (db.companies || []).findIndex(
      (c) => String(c.id) === String(cid) || c.name?.toLowerCase() === cid.toLowerCase()
    )
    if (idx !== -1) {
      db.companies[idx] = { ...db.companies[idx], ...data }
      saveDemoDb(db)
      return ok(db.companies[idx])
    }
    return { status: 404, data: { detail: 'Company not found' } }
  }

  if (companyIdMatch && method === 'delete') {
    const cid = companyIdMatch[1]
    const company = (db.companies || []).find(
      (c) => String(c.id) === String(cid) || c.name?.toLowerCase() === cid.toLowerCase()
    )
    db.companies = (db.companies || []).filter(
      (c) => String(c.id) !== String(cid) && c.name?.toLowerCase() !== cid.toLowerCase()
    )
    if (params.delete_applications === true || params.delete_applications === 'true') {
      db.applications = (db.applications || []).filter(
        (a) => String(a.company_id) !== String(cid) && a.company_name?.toLowerCase() !== company?.name?.toLowerCase()
      )
    }
    saveDemoDb(db)
    return ok({ status: 'success', message: 'Company deleted' })
  }

  // 12. SYSTEM DESIGN LAB ENDPOINTS
  if (urlPath.startsWith('/system-design')) {
    ensureDemoSystemDesignData(db)

    if (urlPath === '/system-design/catalog' && method === 'get') {
      return ok({
        categories: DEFAULT_DIAGRAM_CATEGORIES,
        blocks: DEFAULT_DIAGRAM_BLOCKS,
      })
    }

    const demoMatchBlock = (name) => {
      const lower = String(name || '').trim().toLowerCase()
      const found = DEFAULT_DIAGRAM_BLOCKS.find(
        (b) =>
          b.label.toLowerCase() === lower ||
          b.type_id === lower ||
          lower.includes(b.type_id.replace('_', ' ')) ||
          b.label.toLowerCase().includes(lower)
      )
      if (found) {
        return {
          name: String(name || found.label),
          type_id: found.type_id,
          label: found.label,
          category: found.category,
          icon: found.icon,
          hint_role: found.default_role,
          is_custom: false,
        }
      }
      return {
        name: String(name || 'Custom Block'),
        type_id: 'custom',
        label: String(name || 'Custom Block'),
        category: 'compute_services',
        icon: 'box',
        hint_role: `Place a block representing "${name}" and wire it into your data flow.`,
        is_custom: true,
      }
    }

    const demoComputePenalty = (hintsCount, revealedAll) => {
      const single = Math.max(0, Number(hintsCount || 0)) * 3
      const raw = revealedAll ? Math.max(18, single) : single
      return Math.round(Math.min(25, raw) * 10) / 10
    }

    const demoDeriveRating = (score) =>
      score >= 88
        ? 'STRONG_HIRE'
        : score >= 70
          ? 'INTERVIEW_READY'
          : score >= 50
            ? 'DEVELOPING'
            : 'NEEDS_PRACTICE'

    const defaultDemoVariants = [
      { variant_id: 'standard-scale', title: 'Standard Scale Profile', focus_summary: 'Balanced throughput, SLA, and cost constraints' },
      { variant_id: 'enterprise-compliance', title: 'Enterprise Compliance Profile', focus_summary: 'Strict privacy, audit trail, and YAGNI data governance' },
      { variant_id: 'burst-global', title: 'Global Spike & Edge Profile', focus_summary: 'Extreme burst traffic, multi-region locality, and failover' },
    ]
    const serializeChallenge = (c) => ({
      ...c,
      is_archived: Boolean(c.is_archived),
      expected_components: c.is_builtin ? [] : Array.isArray(c.expected_components) ? c.expected_components : [],
      scale_notes: c.is_builtin ? '' : String(c.scale_notes || ''),
      available_variants: Array.isArray(c.available_variants) && c.available_variants.length
        ? c.available_variants
        : c.is_builtin
          ? defaultDemoVariants
          : [],
    })

    if (urlPath === '/system-design/challenges' && method === 'get') {
      let items = (db.system_design_challenges || []).filter((c) => !c.is_archived)
      if (params.category) {
        items = items.filter((c) => c.category === params.category)
      }
      if (params.difficulty) {
        items = items.filter((c) => c.difficulty === params.difficulty)
      }
      return ok(items.map(serializeChallenge))
    }

    if (urlPath === '/system-design/challenges' && method === 'post') {
      const title = String(data.title || 'Custom Architecture Challenge').trim()
      const slugBase = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'custom-challenge'
      const nextId = db.system_design_challenges.reduce((m, c) => Math.max(m, Number(c.id) || 0), 0) + 1
      const created = {
        id: nextId,
        slug: `${slugBase}-${nextId}`,
        title,
        category: data.category || 'DISTRIBUTED_SYSTEMS',
        difficulty: data.difficulty || 'MEDIUM',
        prompt_summary: data.prompt_summary || 'Custom system design scenario.',
        initial_prompt: data.initial_prompt || `Design ${title}. Clarify scale and core constraints first.`,
        tags: Array.isArray(data.tags) && data.tags.length ? data.tags : ['custom'],
        expected_components: Array.isArray(data.expected_components) ? data.expected_components : [],
        scale_notes: String(data.scale_notes || '').trim(),
        is_builtin: false,
        is_archived: false,
        created_at: new Date().toISOString(),
      }
      db.system_design_challenges.push(created)
      saveDemoDb(db)
      return ok(serializeChallenge(created), 201)
    }

    const findDemoChallengeDuplicate = (candidateTitle, challengesList) => {
      const stripStop = (t) =>
        String(t || '')
          .toLowerCase()
          .replace(/[^a-z0-9\s]/g, ' ')
          .split(/\s+/)
          .filter(
            (w) =>
              w &&
              ![
                'design',
                'build',
                'create',
                'architect',
                'implement',
                'a',
                'an',
                'the',
                'system',
                'service',
                'platform',
                'architecture',
                'engine',
                'pipeline',
                'for',
                'of',
                'and',
                'with',
                'to',
                'in',
                'on',
              ].includes(w)
          )
      const candWords = stripStop(candidateTitle)
      if (!candWords.length) return null
      const candSet = new Set(candWords)
      const candNorm = candWords.join(' ')
      for (const ch of challengesList || []) {
        if (ch.is_archived) continue
        const exWords = stripStop(ch.title)
        if (!exWords.length) continue
        const exNorm = exWords.join(' ')
        if (candNorm === exNorm) return ch
        const exSet = new Set(exWords)
        let inter = 0
        for (const w of candSet) {
          if (exSet.has(w)) inter++
        }
        const union = candSet.size + exSet.size - inter
        const jaccard = union > 0 ? inter / union : 0
        if (jaccard >= 0.72 && inter >= 2) return ch
        const candSubset = [...candSet].every((w) => exSet.has(w))
        const exSubset = [...exSet].every((w) => candSet.has(w))
        if ((candSubset || exSubset) && inter >= 2) return ch
      }
      return null
    }

    if (urlPath === '/system-design/challenges/frontier-prompt' && method === 'post') {
      const appObj = data.application_id
        ? (db.applications || []).find((a) => Number(a.id) === Number(data.application_id))
        : null
      const topic = String(data.topic || '').trim()
      const extraContext = String(data.extra_context || '').trim()
      if (!topic && !appObj && !extraContext) {
        return {
          status: 400,
          data: {
            detail:
              'Provide either a Topic / Scenario Focus or link a tracked job application (application_id).',
          },
        }
      }
      const companyObj = appObj?.company_id
        ? (db.companies || []).find((c) => Number(c.id) === Number(appObj.company_id))
        : null
      const companyName = appObj?.company?.name || appObj?.company_name || companyObj?.name || 'Target Company'
      const roleTitle = appObj?.position || 'Software Engineer'
      const signals = []
      const contextSections = []
      if (topic) {
        contextSections.push(`## Requested Topic\n${topic}`)
      }
      if (appObj) {
        contextSections.push(`## Target Role\n${roleTitle} at ${companyName} (status: ${appObj.status || 'APPLIED'})`)
        if (appObj.notes && String(appObj.notes).trim()) {
          signals.push('Application Notes')
          contextSections.push(`## Application Notes (Clues Only)\n${String(appObj.notes).trim()}`)
        }
        const desc = appObj.job_posting?.description_markdown || appObj.job_description || ''
        const skills = appObj.job_posting?.required_skills || appObj.required_skills || []
        if (desc || (Array.isArray(skills) && skills.length)) {
          signals.push('Job Posting & Skills')
          contextSections.push(
            `## Job Posting & Skills\n${skills.length ? `Skills: ${skills.join(', ')}\n` : ''}${String(desc).slice(0, 1200)}`
          )
        }
        const compPros = Array.isArray(companyObj?.pros)
          ? companyObj.pros.join(', ')
          : companyObj?.pros || ''
        const compNotes = companyObj?.notes || compPros || appObj.company_research || ''
        if (compNotes) {
          signals.push('Company Research')
          contextSections.push(`## Company Research\n${typeof compNotes === 'string' ? compNotes : JSON.stringify(compNotes)}`)
        }
        if (appObj.match_analysis_payload) {
          signals.push('Match Gap Analysis')
        }
      }
      if (extraContext) {
        signals.push('Extra Focus Clues')
        contextSections.push(`## Candidate Extra Focus Clues\n${extraContext}`)
      }
      if (data.use_web_search) {
        signals.push('Web Grounding')
      }
      const activeChallenges = (db.system_design_challenges || []).filter((c) => !c.is_archived)
      const dedupLines = activeChallenges.map((c) => `- ${c.title} — ${c.prompt_summary || ''}`.trim())
      const markdownPrompt = [
        '# Tailored System Design Challenge Generator Prompt',
        `Target Difficulty: ${data.difficulty || 'MEDIUM'}`,
        'Return ONLY a valid JSON object matching the 3-variant System Design challenge schema.',
        ...contextSections,
        '## EXISTING CHALLENGES — DO NOT DUPLICATE',
        ...dedupLines,
      ].join('\n\n')
      const slugBase = (topic || `${companyName}-${roleTitle}` || 'challenge')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
      return ok({
        filename: `${slugBase || 'challenge'}-frontier-challenge-prompt.md`,
        markdown_prompt: markdownPrompt,
        context_signals: signals,
        existing_challenge_titles: activeChallenges.map((c) => c.title),
      })
    }

    if (urlPath === '/system-design/challenges/import' && method === 'post') {
      const raw = String(data.raw_response || '').trim()
      let parsed = null
      const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i)
      const candidates = [fenced ? fenced[1].trim() : null, raw].filter(Boolean)
      const firstBrace = raw.indexOf('{')
      const lastBrace = raw.lastIndexOf('}')
      if (firstBrace !== -1 && lastBrace > firstBrace) {
        candidates.push(raw.slice(firstBrace, lastBrace + 1))
      }
      for (const candidate of candidates) {
        try {
          const obj = JSON.parse(candidate)
          if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
            parsed = obj
            break
          }
        } catch {
          // continue
        }
      }
      if (!parsed || !parsed.title || !parsed.prompt_summary || !parsed.initial_prompt || !parsed.interviewer_brief) {
        return {
          status: 400,
          data: { detail: 'Challenge JSON must include title, prompt_summary, initial_prompt, and interviewer_brief.' },
        }
      }
      if (!data.allow_duplicate) {
        const dup = findDemoChallengeDuplicate(parsed.title, db.system_design_challenges)
        if (dup) {
          return {
            status: 409,
            data: {
              detail: `Challenge '${parsed.title}' closely overlaps existing challenge '${dup.title}'. Pass allow_duplicate=True or adjust your topic to create anyway.`,
            },
          }
        }
      }
      const nextId = db.system_design_challenges.reduce((m, c) => Math.max(m, Number(c.id) || 0), 0) + 1
      const slug =
        String(parsed.title)
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-|-$/g, '') || `frontier-custom-${nextId}`
      const created = {
        id: nextId,
        slug: `${slug}-${nextId}`,
        title: String(parsed.title).trim(),
        category: String(parsed.category || 'DISTRIBUTED_SYSTEMS').trim().toUpperCase(),
        difficulty: String(parsed.difficulty || data.difficulty || 'MEDIUM').trim().toUpperCase(),
        prompt_summary: String(parsed.prompt_summary).trim(),
        initial_prompt: String(parsed.initial_prompt).trim(),
        tags: Array.isArray(parsed.tags) && parsed.tags.length ? parsed.tags : ['frontier-imported'],
        expected_components: [],
        scale_notes: '',
        interviewer_brief: parsed.interviewer_brief,
        is_builtin: false,
        is_archived: false,
        created_at: new Date().toISOString(),
      }
      db.system_design_challenges.push(created)
      saveDemoDb(db)
      return ok(serializeChallenge(created), 201)
    }

    if (urlPath === '/system-design/challenges/generate' && method === 'post') {
      const appObj = data.application_id
        ? (db.applications || []).find((a) => Number(a.id) === Number(data.application_id))
        : null
      const topic = String(data.topic || '').trim()
      const roleCtx = appObj ? `${appObj.company_name || appObj.company?.name || 'Target'} ${appObj.position || 'Engineer'}` : ''
      const titleBase = topic || (roleCtx ? `${roleCtx} Core Platform` : 'Distributed Event Pipeline')
      const candidateTitle = titleBase.startsWith('Design') ? titleBase : `Design ${titleBase}`
      if (!data.allow_duplicate) {
        const dup = findDemoChallengeDuplicate(candidateTitle, db.system_design_challenges)
        if (dup) {
          return {
            status: 409,
            data: {
              detail: `Challenge '${candidateTitle}' closely overlaps existing challenge '${dup.title}'. Pass allow_duplicate=True or adjust your topic to create anyway.`,
            },
          }
        }
      }
      const nextId = db.system_design_challenges.reduce((m, c) => Math.max(m, Number(c.id) || 0), 0) + 1
      const created = {
        id: nextId,
        slug: `ai-custom-${nextId}`,
        title: candidateTitle,
        category: 'DISTRIBUTED_SYSTEMS',
        difficulty: data.difficulty || 'MEDIUM',
        prompt_summary: data.use_web_search
          ? `Web-grounded scenario tailored for ${titleBase}.`
          : `AI-tailored scenario focusing on ${titleBase}.`,
        initial_prompt: `Design ${titleBase}. Start by clarifying expected traffic, durability guarantees, and key latency SLAs.`,
        tags: ['ai-generated', ...(data.use_web_search ? ['web-grounded'] : []), ...(appObj ? [appObj.company_name || appObj.company?.name] : [])].filter(Boolean),
        expected_components: [],
        scale_notes: '',
        is_builtin: false,
        is_archived: false,
        created_at: new Date().toISOString(),
      }
      db.system_design_challenges.push(created)
      saveDemoDb(db)
      return ok(serializeChallenge(created), 201)
    }

    if (urlPath === '/system-design/challenges/reset-defaults' && method === 'post') {
      const defaults = getDefaultDemoSystemDesignChallenges().map((d) => ({ ...d, is_archived: false }))
      const customChallenges = (db.system_design_challenges || []).filter((c) => !c.is_builtin)
      db.system_design_challenges = [...defaults, ...customChallenges]
      saveDemoDb(db)
      return ok(db.system_design_challenges.filter((c) => !c.is_archived).map(serializeChallenge))
    }

    const sdChallengeMatch = urlPath.match(/^\/system-design\/challenges\/([^/]+)$/)
    if (sdChallengeMatch) {
      const key = sdChallengeMatch[1]
      const idx = db.system_design_challenges.findIndex(
        (c) => String(c.id) === String(key) || c.slug === key
      )
      if (idx === -1) {
        return { status: 404, data: { detail: 'System design challenge not found' } }
      }
      if (method === 'get') {
        return ok(serializeChallenge(db.system_design_challenges[idx]))
      }
      if (method === 'put') {
        const ch = db.system_design_challenges[idx]
        const updated = {
          ...ch,
          title: String(data.title || ch.title).trim(),
          category: String(data.category || ch.category).trim().toUpperCase(),
          difficulty: String(data.difficulty || ch.difficulty).trim().toUpperCase(),
          prompt_summary: String(data.prompt_summary || ch.prompt_summary).trim(),
          initial_prompt: String(data.initial_prompt || ch.initial_prompt).trim(),
          tags: Array.isArray(data.tags) ? data.tags : ch.tags,
          ...(!ch.is_builtin
            ? {
                expected_components: Array.isArray(data.expected_components)
                  ? data.expected_components
                  : ch.expected_components || [],
                scale_notes:
                  data.scale_notes !== undefined ? String(data.scale_notes || '').trim() : ch.scale_notes || '',
              }
            : {}),
        }
        db.system_design_challenges[idx] = updated
        db.system_design_sessions = (db.system_design_sessions || []).map((s) =>
          Number(s.challenge_id) === Number(ch.id) ? { ...s, challenge: serializeChallenge(updated) } : s
        )
        saveDemoDb(db)
        return ok(serializeChallenge(updated))
      }
      if (method === 'delete') {
        const ch = db.system_design_challenges[idx]
        const hasSessions = (db.system_design_sessions || []).some(
          (s) => Number(s.challenge_id) === Number(ch.id)
        )
        if (ch.is_builtin || hasSessions) {
          db.system_design_challenges[idx] = { ...ch, is_archived: true }
        } else {
          db.system_design_challenges.splice(idx, 1)
        }
        saveDemoDb(db)
        return ok(null, 204)
      }
    }

    if (urlPath === '/system-design/sessions' && method === 'get') {
      return ok([...db.system_design_sessions])
    }

    if (urlPath === '/system-design/sessions' && method === 'post') {
      const challenge = serializeChallenge(
        db.system_design_challenges.find((c) => Number(c.id) === Number(data.challenge_id)) ||
          db.system_design_challenges[0]
      )
      const nextId =
        db.system_design_sessions.reduce((maxId, s) => Math.max(maxId, Number(s.id) || 0), 0) + 1
      const nowIso = new Date().toISOString()
      const variants = challenge.available_variants || []
      const reqSeed = String(data.brief_seed || '').trim().toLowerCase()
      const reqVariant = String(data.variant_id || '').trim()
      const resolvedSeed = reqSeed || Math.random().toString(16).slice(2, 10).padEnd(8, '0')
      let chosen = null
      let selectionMode = 'random'
      if (reqVariant && variants.length) {
        chosen = variants.find((v) => v.variant_id === reqVariant) || variants[0]
        selectionMode = 'explicit'
      } else if (variants.length) {
        let hash = 0
        const key = `${challenge.slug}:${resolvedSeed}`
        for (let i = 0; i < key.length; i += 1) {
          hash = (hash * 31 + key.charCodeAt(i)) >>> 0
        }
        chosen = variants[hash % variants.length]
      }
      const newSession = {
        id: nextId,
        challenge_id: challenge.id,
        application_id: data.application_id || null,
        mode: data.mode || 'ADAPTIVE',
        brief_seed: resolvedSeed,
        variant_id: selectionMode === 'explicit' ? chosen?.variant_id || 'default' : null,
        variant_title: selectionMode === 'explicit' ? chosen?.title || null : null,
        variant_focus: selectionMode === 'explicit' ? chosen?.focus_summary || null : null,
        variant_selection_mode: selectionMode,
        stage: 'REQUIREMENTS',
        status: 'IN_PROGRESS',
        requirements_transcript: [
          {
            turn_index: 1,
            role: 'interviewer',
            content: challenge.initial_prompt,
            stage: 'REQUIREMENTS',
            timestamp: nowIso,
          },
        ],
        requirements_ledger: {
          functional_requirements: [],
          non_functional_requirements: [],
          scale_estimates: {},
          out_of_scope: [],
          notes: '',
          is_locked: false,
        },
        diagrams_metadata: [],
        diagram_guidance: {},
        architecture_reviews: [],
        defence_transcript: [],
        final_evaluation: null,
        overall_score: null,
        readiness_rating: null,
        created_at: nowIso,
        updated_at: nowIso,
        completed_at: null,
        challenge,
      }
      db.system_design_sessions = [newSession, ...db.system_design_sessions]
      saveDemoDb(db)
      return ok(newSession, 201)
    }

    const sdSessionIdMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)$/)
    if (sdSessionIdMatch) {
      const sid = Number(sdSessionIdMatch[1])
      const idx = db.system_design_sessions.findIndex((s) => Number(s.id) === sid)
      if (idx === -1) {
        return { status: 404, data: { detail: 'System design session not found' } }
      }
      if (method === 'get') {
        return ok(db.system_design_sessions[idx])
      }
      if (method === 'delete') {
        db.system_design_sessions.splice(idx, 1)
        saveDemoDb(db)
        return ok(null, 204)
      }
    }

    const sdModeMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/mode$/)
    if (sdModeMatch && method === 'patch') {
      const sid = Number(sdModeMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      session.mode = data.mode || session.mode
      session.updated_at = new Date().toISOString()
      saveDemoDb(db)
      return ok(session)
    }

    const sdReqMsgMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/requirements\/message$/)
    if (sdReqMsgMatch && method === 'post') {
      const sid = Number(sdReqMsgMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const transcript = session.requirements_transcript || []
      const nowIso = new Date().toISOString()
      const msgText = data.message || ''
      const assisted = Boolean(data.request_hint || /\b(hint|help|coach|nudge|stuck)\b/i.test(msgText))
      transcript.push({
        turn_index: transcript.length + 1,
        role: 'candidate',
        content: msgText,
        stage: session.stage,
        assisted,
        timestamp: nowIso,
      })
      const replyContent = assisted
        ? 'Coaching Hint: Focus on bounding peak read vs. write QPS (~10:1 ratio, ~50M MAU), p99 latency SLAs (<50ms), and whether custom aliases or analytics are out of scope.'
        : 'Assume roughly 10:1 read-to-write traffic (~50M monthly active readers), 99.95% availability, and under 50ms p99 redirect latency. What write QPS or durability constraints are you designing around?'
      transcript.push({
        turn_index: transcript.length + 1,
        role: 'interviewer',
        content: replyContent,
        stage: session.stage,
        assisted,
        timestamp: nowIso,
      })
      session.requirements_transcript = transcript
      session.updated_at = nowIso
      saveDemoDb(db)
      return ok(session)
    }

    const sdReqExtractMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/requirements\/extract$/)
    if (sdReqExtractMatch && method === 'post') {
      const sid = Number(sdReqExtractMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      session.requirements_ledger = {
        functional_requirements: [
          'Core API endpoint to create/ingest primary entities',
          'Low-latency read/lookup path for active items',
        ],
        non_functional_requirements: [
          '99.95% availability target',
          'p99 read latency under 50ms',
        ],
        scale_estimates: {
          traffic_pattern: '10:1 read-to-write ratio',
          monthly_active_users: '~50M MAU (demo baseline)',
        },
        out_of_scope: ['Billing and multi-region active-active conflict resolution'],
        notes: `Extracted from ${session.requirements_transcript.length} conversation turns.`,
        is_locked: Boolean(session.requirements_ledger?.is_locked),
      }
      session.updated_at = new Date().toISOString()
      saveDemoDb(db)
      return ok(session)
    }

    const sdLedgerMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/requirements\/ledger$/)
    if (sdLedgerMatch && method === 'put') {
      const sid = Number(sdLedgerMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      session.requirements_ledger = {
        functional_requirements: data.functional_requirements || [],
        non_functional_requirements: data.non_functional_requirements || [],
        scale_estimates: data.scale_estimates || {},
        out_of_scope: data.out_of_scope || [],
        notes: data.notes || '',
        is_locked: Boolean(data.is_locked),
      }
      if (data.is_locked && session.stage === 'REQUIREMENTS') {
        session.stage = 'DESIGN'
      } else if (!data.is_locked && session.stage === 'DESIGN' && !(session.diagrams_metadata || []).length) {
        session.stage = 'REQUIREMENTS'
      }
      session.updated_at = new Date().toISOString()
      saveDemoDb(db)
      return ok(session)
    }

    const sdUploadMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/diagrams$/)
    if (sdUploadMatch && method === 'post') {
      const sid = Number(sdUploadMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const isFormData = typeof FormData !== 'undefined' && config.data instanceof FormData
      const fileObj = isFormData ? config.data.get('file') : null
      const notes = isFormData ? String(config.data.get('notes') || '') : String(data.notes || '')
      const diagrams = session.diagrams_metadata || []
      const version = diagrams.reduce((m, d) => Math.max(m, Number(d.version) || 0), 0) + 1
      const dataUrl = await readDemoFileAsDataUrl(fileObj)
      const mimeType = fileObj?.type || 'image/png'
      const ext = mimeType.includes('jpeg') ? 'jpg' : mimeType.includes('webp') ? 'webp' : 'png'
      diagrams.push({
        version,
        filename: `v${version}.${ext}`,
        mime_type: mimeType,
        size_bytes: fileObj?.size || 2048,
        notes,
        uploaded_at: new Date().toISOString(),
        diagram_kind: 'image',
        data_url: dataUrl,
      })
      session.diagrams_metadata = diagrams
      if (session.stage === 'REQUIREMENTS') {
        session.stage = 'DESIGN'
      }
      session.updated_at = new Date().toISOString()
      saveDemoDb(db)
      return ok(session, 201)
    }

    const sdCanvasMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/diagrams\/canvas$/)
    if (sdCanvasMatch && method === 'post') {
      const sid = Number(sdCanvasMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const nodes = Array.isArray(data.nodes) ? data.nodes : []
      if (!nodes.length) {
        return {
          status: 400,
          data: { detail: 'Canvas diagram must include at least one architecture component before saving.' },
        }
      }
      const edges = Array.isArray(data.edges) ? data.edges : []
      const diagrams = session.diagrams_metadata || []
      const version = diagrams.reduce((m, d) => Math.max(m, Number(d.version) || 0), 0) + 1
      const flowPayload = {
        schema_version: 1,
        nodes,
        edges,
        notes: String(data.notes || '').trim(),
        flow_summary: {
          node_count: nodes.length,
          edge_count: edges.length,
          components: nodes.map((n) => (n.tech_stack ? `${n.label} (${n.tech_stack})` : n.label)),
          directed_flows: edges.map((e) => {
            const src = nodes.find((n) => n.id === e.source)?.label || e.source
            const dst = nodes.find((n) => n.id === e.target)?.label || e.target
            return `${src} -> ${dst} [${e.protocol || 'HTTPS'}, ${e.delivery_mode || 'sync'}]`
          }),
        },
      }
      diagrams.push({
        version,
        filename: `v${version}.flow.json`,
        mime_type: 'application/json',
        size_bytes: JSON.stringify(flowPayload).length,
        notes: flowPayload.notes,
        uploaded_at: new Date().toISOString(),
        diagram_kind: 'canvas',
        node_count: nodes.length,
        edge_count: edges.length,
        components_preview: nodes.slice(0, 8).map((n) => n.label),
        flow_payload: flowPayload,
      })
      session.diagrams_metadata = diagrams
      if (session.stage === 'REQUIREMENTS') {
        session.stage = 'DESIGN'
      }
      session.updated_at = new Date().toISOString()
      saveDemoDb(db)
      return ok(session, 201)
    }

    const sdFlowMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/diagrams\/(\d+)\/flow$/)
    if (sdFlowMatch && method === 'get') {
      const sid = Number(sdFlowMatch[1])
      const ver = Number(sdFlowMatch[2])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const entry = (session.diagrams_metadata || []).find((d) => Number(d.version) === ver)
      if (!entry || entry.diagram_kind !== 'canvas' || !entry.flow_payload) {
        return { status: 404, data: { detail: `Canvas flow v${ver} not found.` } }
      }
      return ok(entry.flow_payload)
    }

    const sdHintMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/diagrams\/hint$/)
    if (sdHintMatch && method === 'post') {
      const sid = Number(sdHintMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const hintMode = data.hint_mode || 'next_component'
      if (hintMode === 'reveal_all' && String(session.mode || '').toUpperCase() === 'INTERVIEW') {
        return {
          status: 400,
          data: {
            detail:
              'Revealing the full required component bank is disabled in strict INTERVIEW mode. Switch to ADAPTIVE or PRACTICE mode.',
          },
        }
      }
      const rawChallenge =
        db.system_design_challenges.find((c) => Number(c.id) === Number(session.challenge_id)) || {}
      const expectedList =
        Array.isArray(rawChallenge.expected_components) && rawChallenge.expected_components.length
          ? rawChallenge.expected_components
          : [
              'API Gateway',
              'Stateless App Service',
              'Distributed Cache (Redis)',
              'Primary Relational DB',
              'Task Queue',
              'Background Worker Pool',
            ]
      const currentNodes = Array.isArray(data.current_nodes) ? data.current_nodes : []
      const guidance = { ...(session.diagram_guidance || {}) }
      let hintsCount = Number(guidance.hints_used_count || 0)
      let revealedAll = Boolean(guidance.revealed_all_bank || false)
      const alreadyRevealed = Array.isArray(guidance.revealed_components)
        ? [...guidance.revealed_components]
        : []
      const revealedSet = new Set(alreadyRevealed.map((r) => String(r.name || '').toLowerCase()))

      const nodeMatches = (exp) => {
        const expLow = exp.toLowerCase()
        const matchedBlock = demoMatchBlock(exp)
        return currentNodes.some(
          (n) =>
            (matchedBlock.type_id !== 'custom' && n.type_id === matchedBlock.type_id) ||
            `${n.label || ''} ${n.tech_stack || ''}`.toLowerCase().includes(expLow)
        )
      }

      const unrevealed = expectedList.filter(
        (exp) => !nodeMatches(exp) && !revealedSet.has(exp.toLowerCase())
      )
      const newlyRevealed = []
      let message = ''
      if (hintMode === 'next_component') {
        if (unrevealed.length) {
          const item = demoMatchBlock(unrevealed[0])
          alreadyRevealed.push(item)
          newlyRevealed.push(item)
          hintsCount += 1
          message = `Unlocked expected block: ${item.label} (-3 pts).`
        } else {
          message = 'All expected components are already revealed or placed.'
        }
      } else {
        revealedAll = true
        for (const exp of unrevealed) {
          const item = demoMatchBlock(exp)
          alreadyRevealed.push(item)
          newlyRevealed.push(item)
        }
        message = newlyRevealed.length
          ? `Unlocked ${newlyRevealed.length} expected component(s) into your guided bank.`
          : 'Required component bank is already unlocked.'
      }

      const penaltyPoints = demoComputePenalty(hintsCount, revealedAll)
      session.diagram_guidance = {
        hints_used_count: hintsCount,
        revealed_all_bank: revealedAll,
        revealed_components: alreadyRevealed,
        penalty_points: penaltyPoints,
      }
      session.updated_at = new Date().toISOString()
      saveDemoDb(db)
      return ok({
        newly_revealed: newlyRevealed,
        revealed_components: alreadyRevealed,
        hints_used_count: hintsCount,
        revealed_all_bank: revealedAll,
        penalty_points: penaltyPoints,
        remaining_expected_count: Math.max(0, unrevealed.length - newlyRevealed.length),
        message,
        session,
      })
    }

    const sdReviewMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/review$/)
    if (sdReviewMatch && method === 'post') {
      const sid = Number(sdReviewMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const diagrams = session.diagrams_metadata || []
      if (!diagrams.length) {
        return { status: 400, data: { detail: 'No diagram uploaded yet.' } }
      }
      const targetVersion = Number(data.diagram_version || diagrams[diagrams.length - 1].version)
      const targetRev = diagrams.find((d) => Number(d.version) === targetVersion) || diagrams[diagrams.length - 1]
      const webGrounded = Boolean(data.use_web_search)
      const isCanvas = targetRev?.diagram_kind === 'canvas' && targetRev?.flow_payload
      const flowNodes = isCanvas ? targetRev.flow_payload.nodes || [] : []
      const flowEdges = isCanvas ? targetRev.flow_payload.edges || [] : []
      const review = {
        diagram_version: targetVersion,
        interpreted_components: isCanvas
          ? flowNodes.map((n) => (n.tech_stack ? `${n.label} (${n.tech_stack})` : n.label))
          : ['API Gateway', 'Application Service', 'Redis Read Cache', 'Primary SQL Database'],
        interpreted_data_flows: isCanvas && flowEdges.length
          ? flowEdges.map((e) => {
              const s = flowNodes.find((n) => n.id === e.source)?.label || e.source
              const t = flowNodes.find((n) => n.id === e.target)?.label || e.target
              return `${s} -> ${t} [${e.protocol || 'HTTPS'}, ${e.delivery_mode || 'sync'}]`
            })
          : [
              'Client -> API Gateway -> App Service',
              'App Service -> Redis Cache (miss -> Primary DB)',
            ],
        visual_clarifications_needed: isCanvas
          ? []
          : [
              'Clarify whether DB read replicas handle analytics queries or share primary connections.',
            ],
        strengths: [
          isCanvas
            ? `Explicit structured Flow JSON topology (${flowNodes.length} component(s), ${flowEdges.length} directed flow(s)) makes request paths unambiguous.`
            : 'Clear separation between stateless compute tier and read-through cache.',
          'Right-sized service boundaries align with discovered scale requirements.',
          ...(webGrounded
            ? ['[Web Grounded] Matches production edge-caching & stateless app-tier benchmarks.']
            : []),
        ],
        missing_components: ['Dead-letter / async worker path for non-blocking click/audit telemetry'],
        bottlenecks_and_spofs: ['Single primary database instance without automated failover standby'],
        unnecessary_complexity: [],
        requirement_gaps: ['Explicit cache eviction / TTL invalidation flow is not annotated'],
        overall_impression: `${webGrounded ? '[Web-Grounded] ' : ''}Solid v${targetVersion} baseline architecture; tighten DB failover and async telemetry paths during defence.`,
        suggested_defence_topics: [
          'How does your service behave if Redis evicts hot keys or temporarily goes unreachable during peak traffic?',
        ],
      }
      const filteredReviews = (session.architecture_reviews || []).filter(
        (r) => Number(r.diagram_version) !== targetVersion
      )
      filteredReviews.push(review)
      filteredReviews.sort((a, b) => Number(a.diagram_version) - Number(b.diagram_version))
      session.architecture_reviews = filteredReviews
      session.stage = 'REVIEW'
      if (!(session.defence_transcript || []).length) {
        session.defence_transcript = [
          {
            turn_index: 1,
            role: 'interviewer',
            content: review.suggested_defence_topics[0],
            stage: 'DEFENCE',
            timestamp: new Date().toISOString(),
          },
        ]
      }
      session.updated_at = new Date().toISOString()
      saveDemoDb(db)
      return ok(session)
    }

    const sdDefenceMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/defence\/message$/)
    if (sdDefenceMatch && method === 'post') {
      const sid = Number(sdDefenceMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const defence = session.defence_transcript || []
      const nowIso = new Date().toISOString()
      const msgText = data.message || ''
      const assisted = Boolean(data.request_hint || /\b(hint|help|coach|nudge|stuck)\b/i.test(msgText))
      const webGrounded = Boolean(data.use_web_search)
      defence.push({
        turn_index: defence.length + 1,
        role: 'candidate',
        content: msgText,
        stage: 'DEFENCE',
        assisted,
        timestamp: nowIso,
      })
      const baseReply = assisted
        ? 'Coaching Hint: Explain your circuit-breaker threshold, stale-while-revalidate fallback, and how you shed non-critical write telemetry under primary DB saturation.'
        : 'Understood. Suppose your primary DB hits connection saturation during a failover window—what backpressure or circuit-breaker mechanism prevents cascading 5xx failures?'
      defence.push({
        turn_index: defence.length + 1,
        role: 'interviewer',
        content: webGrounded ? `[Web-Grounded Context] ${baseReply}` : baseReply,
        stage: 'DEFENCE',
        assisted,
        timestamp: nowIso,
      })
      session.defence_transcript = defence
      session.stage = 'DEFENCE'
      session.updated_at = nowIso
      saveDemoDb(db)
      return ok(session)
    }

    const sdEvalMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/evaluate$/)
    if (sdEvalMatch && method === 'post') {
      const sid = Number(sdEvalMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const lockedLabel = session.requirements_ledger?.is_locked ? 'locked' : 'unlocked'
      const diagramsCount = (session.diagrams_metadata || []).length
      const defTurns = (session.defence_transcript || []).filter((t) => t.role === 'candidate').length
      const dims = [
        ['Requirements Clarity', 4, `Candidate ran ${(session.requirements_transcript || []).length} discovery turns and curated a ${lockedLabel} requirements ledger.`, 'Strong clarifying focus on read/write ratio and SLA bounds.'],
        ['Scope & Prioritization', 4, 'Explicitly separated MVP endpoints from out-of-scope multi-region replication.', 'Pragmatic phasing aligns with interview time constraints.'],
        ['Back-of-the-Envelope Estimation', 4, 'Captured MAU baseline and 10:1 read/write assumption inside scale_estimates.', 'Add explicit storage growth calculations over 5 years next time.'],
        ['API & Interface Design', 4, 'Defined primary write ingestion and low-latency read paths in ledger notes.', 'Mention idempotency keys on mutating POST requests.'],
        ['Data Model & Storage Choice', 4, 'Diagram v' + Math.max(1, diagramsCount) + ' anchors durable state in a primary relational DB.', 'Sound indexing and schema discipline.'],
        ['High-Level Architecture', 5, `Submitted ${diagramsCount || 1} diagram revision(s) with clear gateway, service, and storage separation.`, 'Clean component boundaries easy to follow.'],
        ['Scalability & Partitioning', 4, 'Addressed read scaling through cache offloading before DB lookup.', 'Clarify sharding key choice once write QPS exceeds single primary.'],
        ['Reliability & Fault Tolerance', 4, 'Identified standby failover risk and discussed cache unavailability fallback.', 'Document active health-check thresholds and retry jitter.'],
        ['Caching & Latency Optimization', 5, 'Placed Redis read cache directly ahead of storage to meet <50ms p99 SLA.', 'Effective hot-key mitigation mindset.'],
        ['Right-Sizing & Simplicity (YAGNI)', 5, 'Avoided unnecessary Kafka/microservice sprawl for the initial scale target.', 'Zero speculative complexity.'],
        ['Trade-off Justification', 4, `Completed ${defTurns} defence response(s) explaining cache vs. DB consistency tradeoffs.`, 'Articulated trade-offs clearly under probing.'],
        ['Defence Communication Under Pressure', 4, 'Directly answered bottlenecks highlighted in the architecture review.', 'Concise and structured explanations.'],
      ]
      const rawScore = 86
      const penalty = Number(session.diagram_guidance?.penalty_points || 0)
      const netScore = Math.round(Math.max(0, rawScore - penalty) * 10) / 10
      const rating = demoDeriveRating(netScore)
      const finalEvaluation = {
        overall_score: netScore,
        raw_score: rawScore,
        guidance_penalty: penalty,
        readiness_rating: rating,
        executive_summary:
          `Demonstrated strong end-to-end systems thinking across ${diagramsCount || 1} diagram revision(s) and ${defTurns} defence turn(s), keeping the core read/write path clean and appropriately scaled.`,
        rubric_scores: dims.map(([dimension, score, evidence, critique]) => ({
          dimension,
          score,
          evidence,
          critique,
        })),
        key_strengths: [
          'Established measurable read/write ratio and p99 latency targets before drawing',
          'Avoided premature distributed complexity while isolating the hot read path in cache',
        ],
        critical_gaps: [
          'Primary database single-point-of-failure failover automation needs explicit diagram notation',
        ],
        recommended_next_steps: [
          'Revise the architecture diagram showing standby replication and async dead-letter worker queues',
        ],
      }
      const nowIso = new Date().toISOString()
      session.final_evaluation = finalEvaluation
      session.overall_score = netScore
      session.readiness_rating = rating
      session.stage = 'COMPLETED'
      session.status = 'COMPLETED'
      session.completed_at = nowIso
      session.updated_at = nowIso
      saveDemoDb(db)
      return ok(session)
    }

    const sdFrontierPacketMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/frontier-packet$/)
    if (sdFrontierPacketMatch && method === 'get') {
      const sid = Number(sdFrontierPacketMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const challenge = session.challenge || {}
      const reqTurns = session.requirements_transcript || []
      const defTurns = session.defence_transcript || []
      const candidateTurns = [...reqTurns, ...defTurns].filter((t) => t.role === 'candidate')
      const assistedCount = candidateTurns.filter((t) => t.assisted).length
      const independentCount = candidateTurns.length - assistedCount
      const diagrams = session.diagrams_metadata || []
      const latestVersion = diagrams.length ? Number(diagrams[diagrams.length - 1].version) : null
      const fmtTurns = (turns) =>
        turns.length
          ? turns
              .map(
                (t) =>
                  `- **Turn ${t.turn_index} (${t.role}${t.assisted ? ' [ASSISTED / HINT REQUESTED]' : ''})**: ${t.content}`
              )
              .join('\n')
          : '_No turns recorded._'
      const rubricDims = [
        'Requirements Clarity',
        'Scope & Prioritization',
        'Back-of-the-Envelope Estimation',
        'API & Interface Design',
        'Data Model & Storage Choice',
        'High-Level Architecture',
        'Scalability & Partitioning',
        'Reliability & Fault Tolerance',
        'Caching & Latency Optimization',
        'Right-Sizing & Simplicity (YAGNI)',
        'Trade-off Justification',
        'Defence Communication Under Pressure',
      ]
      const jsonTemplate = JSON.stringify(
        {
          overall_score: 0,
          readiness_rating: 'NEEDS_PRACTICE | DEVELOPING | INTERVIEW_READY | STRONG_HIRE',
          executive_summary: '<2-4 sentence assessment>',
          rubric_scores: rubricDims.map((dimension) => ({
            dimension,
            score: 3,
            evidence: '<concrete observation>',
            critique: '<specific strength or gap>',
          })),
          key_strengths: ['<strength>'],
          critical_gaps: ['<gap>'],
          recommended_next_steps: ['<next step>'],
        },
        null,
        2
      )
      const markdownPacket = [
        `# System Design Interview Evaluation Dossier: ${challenge.title || 'Challenge'}`,
        '',
        `> Attach your latest uploaded diagram image (if any) alongside this prompt in Claude, ChatGPT, or Gemini.`,
        `> Coaching telemetry: **${independentCount} independent** candidate turn(s) vs **${assistedCount} assisted/hint-requested** turn(s).`,
        '',
        '## 1. Challenge Brief',
        `- **Title**: ${challenge.title || ''}`,
        `- **Initial Prompt**: ${challenge.initial_prompt || ''}`,
        '',
        '## 2. Requirements Discovery Transcript',
        fmtTurns(reqTurns),
        '',
        '## 3. Requirements Ledger',
        '```json',
        JSON.stringify(session.requirements_ledger || {}, null, 2),
        '```',
        '',
        '## 4. Diagram Revisions & Local AI Review Notes',
        '```json',
        JSON.stringify(
          {
            diagrams_metadata: diagrams.map(({ data_url: _omit, ...rest }) => rest),
            architecture_reviews: session.architecture_reviews || [],
          },
          null,
          2
        ),
        '```',
        '',
        '## 5. Architecture Defence Transcript',
        fmtTurns(defTurns),
        '',
        '## 6. Return Valid JSON Scorecard Matching This Schema',
        '```json',
        jsonTemplate,
        '```',
      ].join('\n')
      return ok({
        session_id: sid,
        challenge_title: challenge.title || 'System Design Challenge',
        filename: `${challenge.slug || 'system-design'}-session-${sid}-frontier-packet.md`,
        diagram_version: latestVersion,
        markdown_packet: markdownPacket,
      })
    }

    const sdImportEvalMatch = urlPath.match(/^\/system-design\/sessions\/([^/]+)\/import-evaluation$/)
    if (sdImportEvalMatch && method === 'post') {
      const sid = Number(sdImportEvalMatch[1])
      const session = db.system_design_sessions.find((s) => Number(s.id) === sid)
      if (!session) return { status: 404, data: { detail: 'Session not found' } }
      const raw = String(data.raw_response || '').trim()
      let parsed = null
      const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i)
      const candidates = [fenced ? fenced[1].trim() : null, raw].filter(Boolean)
      const firstBrace = raw.indexOf('{')
      const lastBrace = raw.lastIndexOf('}')
      if (firstBrace !== -1 && lastBrace > firstBrace) {
        candidates.push(raw.slice(firstBrace, lastBrace + 1))
      }
      for (const candidate of candidates) {
        try {
          const obj = JSON.parse(candidate)
          if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
            parsed = obj
            break
          }
        } catch {
          // try next extraction candidate
        }
      }
      if (!parsed) {
        return { status: 400, data: { detail: 'Could not extract a valid JSON scorecard object.' } }
      }
      const rubricScores = Array.isArray(parsed.rubric_scores)
        ? parsed.rubric_scores.map((r, idx) => ({
            dimension: String(r.dimension || `Dimension ${idx + 1}`),
            score: Math.max(1, Math.min(5, Number(r.score || 3))),
            evidence:
              String(r.evidence || '').trim().length >= 5
                ? String(r.evidence).trim()
                : `Session ${sid} external frontier review evidence.`,
            critique: String(r.critique || 'Evaluated by external frontier model.').trim(),
          }))
        : []
      const rawScore = Number(parsed.overall_score ?? 85)
      const penalty = Number(session.diagram_guidance?.penalty_points || 0)
      const overallScore = Math.round(Math.max(0, rawScore - penalty) * 10) / 10
      const rating = demoDeriveRating(overallScore)
      const normalized = {
        overall_score: overallScore,
        raw_score: rawScore,
        guidance_penalty: penalty,
        readiness_rating: rating,
        executive_summary: String(
          parsed.executive_summary || 'External frontier evaluation imported.'
        ),
        rubric_scores: rubricScores,
        key_strengths: Array.isArray(parsed.key_strengths) ? parsed.key_strengths : [],
        critical_gaps: Array.isArray(parsed.critical_gaps) ? parsed.critical_gaps : [],
        recommended_next_steps: Array.isArray(parsed.recommended_next_steps)
          ? parsed.recommended_next_steps
          : [],
      }
      const nowIso = new Date().toISOString()
      session.final_evaluation = normalized
      session.overall_score = overallScore
      session.readiness_rating = rating
      session.stage = 'COMPLETED'
      session.status = 'COMPLETED'
      session.completed_at = nowIso
      session.updated_at = nowIso
      saveDemoDb(db)
      return ok(session)
    }
  }

  return ok({ message: 'Client Demo Mode mock response' })
}
