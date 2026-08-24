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
    const appIndex = (db.applications || []).findIndex((a) => a.id === appId)

    if (method === 'get') {
      if (appIndex === -1) throw new Error('Application not found')
      const app = db.applications[appIndex]
      const events = app.events || []
      const latest_event = events.length > 0 ? events[0] : null
      return ok({ ...app, events, latest_event })
    }

    if (method === 'patch') {
      if (appIndex === -1) throw new Error('Application not found')
      db.applications[appIndex] = {
        ...db.applications[appIndex],
        ...data,
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
    const appIndex = (db.applications || []).findIndex((a) => a.id === appId)
    if (appIndex === -1) throw new Error('Application not found')

    const app = db.applications[appIndex]
    const oldStatus = app.status
    const newStatus = data.status || oldStatus

    app.status = newStatus
    if (data.rejection_reason) app.rejection_reason = data.rejection_reason
    if (data.rejection_date) app.rejection_date = data.rejection_date
    if (data.notes) app.notes = data.notes
    app.last_activity_at = new Date().toISOString()

    const newEvent = {
      id: `evt_${Date.now()}`,
      application_id: appId,
      event_type: `STAGE_CHANGE_${newStatus}`,
      title: `Transitioned to ${newStatus}`,
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
    const app = (db.applications || []).find((a) => a.id === appId)
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
    const app = (db.applications || []).find((a) => a.id === appId)
    const company = app?.company_name || 'Hiring Company'
    const position = app?.position || 'Target Position'

    const letterText = `Dear Hiring Manager at ${company},\n\nI am writing to express my strong interest in the ${position} role. With my background as a Staff Distributed Systems Engineer and extensive hands-on experience in Go, Rust, and microservices architecture, I am confident in my ability to make an immediate positive impact on your team.\n\nThroughout my career, I have designed and deployed high-performance distributed systems, optimized real-time data streaming pipelines, and led critical infrastructure initiatives. I look forward to discussing how my skills align with ${company}'s goals.\n\nSincerely,\nAlex Rivera`

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
        key_strengths: ['Strong backend alignment', 'Distributed systems experience'],
        gaps: ['None identified'],
        gap_closing_tips: ['Highlight past infrastructure work.'],
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
        key_strengths: ['Architecture leadership', 'High availability system design'],
        gaps: ['Proprietary toolchain'],
        gap_closing_tips: ['Focus on system design fundamentals.'],
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
    const taskId = evalTaskMatch[1]
    db.intake_evaluations = (db.intake_evaluations || []).filter((t) => t.id !== taskId)
    saveDemoDb(db)
    return ok({ message: 'Evaluation deleted' })
  }

  const evalTaskActionMatch = urlPath.match(/^\/intake\/evaluations\/([^/]+)\/(cancel|retry|fix-jd)$/)
  if (evalTaskActionMatch && method === 'post') {
    const taskId = evalTaskActionMatch[1]
    const action = evalTaskActionMatch[2]
    const task = (db.intake_evaluations || []).find((t) => t.id === taskId)
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
    const ids = new Set(data.task_ids || [])
    db.intake_evaluations = (db.intake_evaluations || []).map((t) => {
      if (ids.has(t.id)) {
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
    const ids = new Set(data.task_ids || [])
    db.intake_evaluations = (db.intake_evaluations || []).filter((t) => !ids.has(t.id))
    saveDemoDb(db)
    return ok({ message: 'Tasks deleted' })
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
    return ok({ items, total: items.length })
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
    db.staging_items = (db.staging_items || []).filter((s) => s.id !== stageId)
    saveDemoDb(db)
    return ok({ message: 'Staging item deleted' })
  }

  if (urlPath === '/staging/resolved' && method === 'delete') {
    db.staging_items = (db.staging_items || []).filter((s) => s.status !== 'RESOLVED')
    saveDemoDb(db)
    return ok({ message: 'Resolved staging items cleared' })
  }

  // 6. DIAGNOSTICS & TELEMETRY
  if (urlPath === '/diagnostics/stats' && method === 'get') {
    const traces = db.diagnostics_traces || []
    return ok({
      total_traces: traces.length,
      success_count: traces.filter((t) => t.status === 'success').length,
      error_count: traces.filter((t) => t.status === 'error').length,
      avg_latency_ms: 850,
    })
  }

  if (urlPath === '/diagnostics/traces' && method === 'get') {
    let traces = db.diagnostics_traces || []
    if (params.category) traces = traces.filter((t) => t.category === params.category)
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

    const assistantMsg = {
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: `Here is advice regarding "${lastUserMsg}":\n\n1. Focus on core architectural principles.\n2. Quantify achievements with metrics.\n3. Prepare concrete STAR examples for your interview rounds.`,
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
