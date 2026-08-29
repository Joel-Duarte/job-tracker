import { getDemoDb, saveDemoDb } from './demoStorage'

function delay(ms = null) {
  const actualMs = ms !== null ? ms : Math.floor(Math.random() * 500) + 500
  return new Promise((resolve) => setTimeout(resolve, actualMs))
}

export async function handleDemoRequest(config) {
  const method = (config.method || 'get').toLowerCase()
  const rawUrl = config.url || ''
  // Strip query parameters for endpoint matching
  const urlPath = rawUrl.split('?')[0].replace(/\/$/, '')
  const params = config.params || {}
  const data = typeof config.data === 'string' ? JSON.parse(config.data || '{}') : (config.data || {})

  const db = getDemoDb()

  // Simulate artificial delay (500ms - 1000ms by default, 1500ms for job intake extraction)
  let delayMs = 500
  if (urlPath.includes('/intake/paste') || urlPath.includes('/intake/assess-job') || urlPath.includes('/intake/upload')) {
    delayMs = 1500
  }
  await delay(delayMs)

  // Response helper
  const ok = (responseData, status = 200) => ({
    data: responseData,
    status,
    statusText: 'OK',
    headers: {},
    config,
  })

  // 1. APPLICATIONS ENDPOINTS
  if (urlPath === '/applications' && method === 'get') {
    let items = [...(db.applications || [])]
    if (params.q) {
      const q = params.q.toLowerCase()
      items = items.filter(
        (a) =>
          a.company_name?.toLowerCase().includes(q) ||
          a.position?.toLowerCase().includes(q) ||
          a.location?.toLowerCase().includes(q)
      )
    }
    if (params.status) {
      items = items.filter((a) => a.status === params.status)
    }
    return ok({ items, total: items.length })
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
      if (appIndex === -1) throw new Error('Application not found')
      const app = db.applications[appIndex]
      const events = app.events || []
      const latest_event = events.length > 0 ? events[0] : null
      return ok({ ...app, events, latest_event })
    }

    if (method === 'patch') {
      if (appIndex === -1) throw new Error('Application not found')
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

    const newEvent = {
      id: `evt_${Date.now()}`,
      application_id: appId,
      event_type: eventType,
      title: eventTitle,
      description: data.notes || `Moved application from ${oldStatus} to ${newStatus}`,
      created_at: new Date().toISOString(),
      raw_payload: data,
    }

    app.events = [newEvent, ...(app.events || [])]
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
        db.action_items[itemIndex] = { ...db.action_items[itemIndex], ...data }
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
      total_tokens: totalTokens || 142800,
      total_spend_usd: totalSpend,
      total_savings_usd: totalSavings || 14.28,
      task_token_breakdown: Object.keys(taskBreakdown).length > 0 ? taskBreakdown : {
        "JOB_ASSESSMENT": { calls: 24, tokens: 98400, cost_usd: 0.0, savings_usd: 9.84 },
        "COVER_LETTER": { calls: 8, tokens: 26400, cost_usd: 0.0, savings_usd: 2.64 },
        "INTERVIEW_SIMULATION": { calls: 6, tokens: 18000, cost_usd: 0.0, savings_usd: 1.80 }
      },
      avg_latency_ms: 850,
    })
  }

  if (urlPath === '/diagnostics/traces' && method === 'get') {
    let traces = db.diagnostics_traces || []
    if (params.category && params.category !== 'all') {
      traces = traces.filter((t) => t.category === params.category)
    }
    return ok(traces)
  }

  if (urlPath === '/diagnostics/purge' && method === 'delete') {
    db.diagnostics_traces = []
    saveDemoDb(db)
    return ok({ message: 'Traces purged' })
  }

  // 7. SYSTEM & AI CONFIG
  if (urlPath === '/config/system' && method === 'get') {
    return ok(db.system_settings || {})
  }

  if (urlPath === '/config/system' && method === 'patch') {
    db.system_settings = { ...(db.system_settings || {}), ...data }
    saveDemoDb(db)
    return ok(db.system_settings)
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
    return ok(db.usage_overview || {
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
      comparative_costs: []
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
      HAS_COMPLETED_ONBOARDING: db.system_settings?.has_completed_onboarding ?? true,
      ENABLE_EMAIL_INTAKE: true,
      ENABLE_EMBEDDINGS: true,
      ENABLE_AUTO_COVER_LETTER: true,
      COVER_LETTER_MATCH_THRESHOLD: 70,
      COVER_LETTER_LENGTH: 'standard',
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
    return ok(db.agent_chats || [])
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
    const lowerMsg = lastUserMsg.toLowerCase()
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

    let replyText = `Here is advice regarding "${lastUserMsg}":\n\n1. Focus on core architectural principles.\n2. Quantify achievements with metrics.\n3. Prepare concrete STAR examples for your interview rounds.`

    if (
      lowerMsg.includes('tool') ||
      lowerMsg.includes('can you do') ||
      lowerMsg.includes('what can you') ||
      lowerMsg.includes('available tools') ||
      lowerMsg.includes('capabilities') ||
      lowerMsg.includes('engine')
    ) {
      replyText = `I have access to the following backend tools and subsystem engines to power your job search:\n\n1. Recruitment Mailbox Synchronization Engine: Automatic IMAP/OAuth email fetcher and deduplicating intake scanner.\n2. Camofox Stealth Scraper: Multi-engine web scraper for extracting job postings, role specs, and requirements.\n3. LangGraph Intake Pipeline: Stateful multi-step graph workflow for job lead qualification and candidate match scoring.\n4. pgvector/pgtrgm Search: High-performance hybrid semantic vector cosine similarity and trigram database search engine.\n5. AI Task Studio: Task-bound prompt engineering and customizable system prompt template configuration environment.\n6. Interactive Mock Interview Simulator: Real-time multi-turn behavioral & technical interview practice engine with STAR scoring and debrief scorecards.\n7. Staleness Archiver Worker: Automated inactivity tracking and stalled application follow-up detector.`
    }

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
        { stage: "Applied", count: totalApps, conversion_rate: 100, dropoff_rate: 0 },
        { stage: "Assessment", count: Math.max(3, activeCount), conversion_rate: 60, dropoff_rate: 40 },
        { stage: "Interview", count: interviewCount, conversion_rate: 40, dropoff_rate: 33.3 },
        { stage: "Offer", count: offerCount, conversion_rate: 20, dropoff_rate: 50 }
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

  // Fallback default response
  return ok({ message: 'Client Demo Mode mock response' })
}
