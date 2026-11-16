import { test, expect } from '@playwright/test'

// Minimal valid 1x1 transparent PNG bytes
const SAMPLE_PNG_BUFFER = Buffer.from(
  '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082',
  'hex'
)

test('navigates via Agent System Design Lab tab, supports 3+ columns, custom/AI challenges, edit/delete/reset, and theme switching', async ({
  page,
  isMobile,
}) => {
  const errors = []
  page.on('pageerror', (err) => errors.push(err.message))
  page.on('console', (msg) => {
    if (msg.type() === 'warning' && msg.text().includes('[Vue warn]')) {
      errors.push(msg.text())
    }
  })

  await page.goto('/')
  if (isMobile) {
    await page.getByRole('button', { name: 'Toggle navigation menu' }).click()
    await expect(page.locator('.mobile-nav-link').filter({ hasText: 'System Design' })).toHaveCount(0)
    await page.locator('.mobile-nav-link').filter({ hasText: 'Agent' }).click()
  } else {
    await expect(page.locator('.nav-link').filter({ hasText: 'System Design' })).toHaveCount(0)
    await page.locator('.nav-link').filter({ hasText: 'Agent' }).first().click()
  }

  await expect(page).toHaveURL(/\/chat$/)
  await page.getByTestId('mode-btn-system-design').click()

  // Lobby shows clean scenario grid directly (no redundant top header banner or bottom session list)
  await expect(page.getByRole('heading', { name: 'Interview Challenge Scenarios' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Your Practice & Interview Sessions' })).toHaveCount(0)
  await expect(page.getByText('Design a URL Shortener')).toBeVisible()
  await expect(page.getByText('Design Spotify for 100,000 Users')).toBeVisible()

  if (!isMobile) {
    const colCount = await page.locator('.sd-challenges-grid').evaluate((el) => {
      return getComputedStyle(el).gridTemplateColumns.trim().split(/\s+/).length
    })
    expect(colCount).toBeGreaterThanOrEqual(3)
  }

  // Create AI-generated custom challenge + manual challenge
  await page.getByTestId('open-new-challenge-modal-btn').click()
  await expect(page.getByTestId('new-challenge-modal')).toBeVisible()
  await page.getByTestId('generate-topic-input').fill('Real-Time Feature Flag Distribution')
  await page.getByTestId('submit-generate-challenge-btn').click()
  await expect(page.getByText('Design Real-Time Feature Flag Distribution')).toBeVisible()

  await page.getByTestId('open-new-challenge-modal-btn').click()
  await page.getByTestId('tab-manual-challenge').click()
  await page.getByTestId('manual-title-input').fill('Design a Webhook Retry Bus')
  await page.getByTestId('manual-summary-input').fill('Multi-tenant webhook delivery with exponential backoff.')
  await page.getByTestId('manual-prompt-input').fill('Design a reliable webhook retry engine for SaaS tenants.')
  await page.getByTestId('manual-tags-input').fill('webhooks, queues')
  await page.getByTestId('submit-manual-challenge-btn').click()
  await expect(page.getByText('Design a Webhook Retry Bus')).toBeVisible()

  // Edit the newly created manual challenge via card pencil button
  await page.getByTestId('edit-challenge-btn').last().click()
  await expect(page.getByRole('heading', { name: 'Edit Challenge Scenario' })).toBeVisible()
  await page.getByTestId('manual-title-input').fill('Design an Enterprise Webhook Bus')
  await page.getByTestId('submit-manual-challenge-btn').click()
  await expect(page.getByText('Design an Enterprise Webhook Bus')).toBeVisible()

  // Delete a built-in challenge + custom challenge, then reset default 8 challenges
  await page
    .getByTestId('challenge-card-spotify-100k')
    .getByTestId('delete-challenge-btn')
    .click()
  await expect(page.getByText('Design Spotify for 100,000 Users')).toHaveCount(0)

  await page.getByTestId('reset-default-challenges-btn').click()
  await expect(page.getByText('Design Spotify for 100,000 Users')).toBeVisible()
  // Custom challenge remains preserved across reset-defaults
  await expect(page.getByText('Design an Enterprise Webhook Bus')).toBeVisible()

  // Toggle Daylight & Midnight themes
  await page.locator('.theme-toggle').click()
  await page.locator('.theme-mode-btn', { hasText: 'Daylight' }).click()
  await expect(page.locator('html')).toHaveClass(/daylight/)
  await page.locator('.theme-mode-btn', { hasText: 'Midnight' }).click()
  await expect(page.locator('html')).not.toHaveClass(/daylight/)

  // Settings Preferences tab also exposes Reset Default 8 Challenges
  await page.goto('/settings?tab=preferences')
  await expect(page.getByTestId('settings-reset-sd-challenges-btn')).toBeVisible()

  expect(errors).toEqual([])
})

test('completes full 5-stage adaptive loop with gated stepper, sleek input bar, and frontier packet tab', async ({
  page,
}) => {
  const errors = []
  page.on('pageerror', (err) => errors.push(err.message))
  page.on('console', (msg) => {
    if (msg.type() === 'warning' && msg.text().includes('[Vue warn]')) {
      errors.push(msg.text())
    }
  })

  await page.goto('/chat?mode=system_design')
  await expect(page.getByText('DEMO MODE')).toBeVisible()

  // Clicking the card body/title should not start a session; only the primary button does
  const urlCard = page.getByTestId('challenge-card-url-shortener')
  await urlCard.getByRole('heading', { name: 'Design a URL Shortener' }).click()
  await expect(page.getByTestId('back-to-challenges-btn')).toHaveCount(0)

  await expect(urlCard.getByTestId('start-challenge-btn')).toHaveText(/Start Challenge/)
  await urlCard.getByTestId('start-challenge-btn').click()

  // Verify compact header and strict stage gating (stages 2-5 start locked)
  await expect(page.getByRole('heading', { name: 'Design a URL Shortener' })).toBeVisible()
  await expect(page.getByTestId('back-to-challenges-btn')).toBeVisible()
  await expect(page.getByTestId('stage-step-REQUIREMENTS')).toBeEnabled()
  await expect(page.getByTestId('stage-step-DESIGN')).toBeDisabled()
  await expect(page.getByTestId('stage-step-REVIEW')).toBeDisabled()
  await expect(page.getByTestId('stage-step-DEFENCE')).toBeDisabled()
  await expect(page.getByTestId('stage-step-COMPLETED')).toBeDisabled()

  // Stage 1: Requirements discovery via sleek chat-input-bar + inline hint icon button
  const reqInput = page.getByTestId('req-chat-input')
  await reqInput.fill('What read/write ratio and p99 redirect latency should we target?')
  await page.getByTestId('req-send-btn').click()
  await expect(page.getByText(/10:1 read-to-write traffic/)).toBeVisible()

  // Returning to lobby should show "Resume Session" + "+" fresh-session button and reopen the same session
  await page.getByTestId('back-to-challenges-btn').click()
  await expect(urlCard.getByTestId('start-challenge-btn')).toHaveText(/Resume Session/)
  await expect(urlCard.getByTestId('new-session-btn')).toBeVisible()
  await urlCard.getByTestId('start-challenge-btn').click()
  await expect(page.getByTestId('back-to-challenges-btn')).toBeVisible()
  await expect(page.getByText(/10:1 read-to-write traffic/)).toBeVisible()

  await page.getByTestId('req-hint-btn').click()
  await expect(page.locator('.sd-hint-tag').first()).toBeVisible()

  // Turn-by-turn live ledger sync already populated requirements; Re-sync Ledger remains available
  await expect(page.getByTestId('live-sync-pill')).toBeVisible()
  await expect(page.locator('textarea').nth(1)).toHaveValue(/high read fan-out|Core API/)
  await page.getByTestId('resync-ledger-btn').click()
  await expect(page.locator('textarea').nth(1)).toHaveValue(/Core API endpoint to create\/ingest primary entities/)
  await page.getByRole('button', { name: 'Lock Requirements & Proceed to Diagram' }).click()

  // Locking Stage 1 opens the dedicated full-screen Design Studio; Back returns to Stage 2 card for image upload
  await expect(page).toHaveURL(/\/system-design\/\d+\/design/)
  await expect(page.getByTestId('design-studio-page')).toBeVisible()
  await page.getByTestId('studio-back-btn').click()

  await expect(page.getByTestId('open-design-studio-btn')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Upload Architecture Diagram' })).toBeVisible()
  await expect(page.getByTestId('stage-step-DESIGN')).toBeEnabled()
  await expect(page.getByTestId('stage-step-REVIEW')).toBeDisabled()

  await page.locator('.diagram-file-input').setInputFiles({
    name: 'url-shortener-v1.png',
    mimeType: 'image/png',
    buffer: SAMPLE_PNG_BUFFER,
  })
  await page
    .getByPlaceholder(/Added Redis read cache/)
    .fill('Added Redis cache ahead of Postgres primary')
  await page.getByRole('button', { name: 'Upload Diagram Revision' }).click()

  await page.getByTestId('review-web-search-checkbox').check()
  const analyzeBtn = page.getByRole('button', { name: /Analyze Architecture \(v1\)/ })
  await expect(analyzeBtn).toBeVisible()
  await analyzeBtn.click()

  // Stage 3: Multimodal review unlocks Review + Defence, and shows summary back on Diagram tab
  await expect(page.getByRole('heading', { name: 'Architecture Critique' })).toBeVisible()
  await expect(page.getByText(/\[Web-Grounded\]/)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Visual Clarifications Needed' })).toBeVisible()
  await expect(page.getByTestId('stage-step-DEFENCE')).toBeEnabled()

  await page.getByTestId('stage-step-DESIGN').click()
  await expect(page.getByTestId('diagram-review-summary')).toBeVisible()
  await page.getByRole('button', { name: 'Open Full Critique' }).click()

  // Stage 4: Interactive Architecture Defence (uncluttered, no frontier card here)
  await page.getByRole('button', { name: 'Proceed to Architecture Defence' }).click()
  await expect(page.getByTestId('frontier-packet-card')).toHaveCount(0)
  await expect(page.getByTestId('stage-step-COMPLETED')).toBeDisabled()

  await page.getByTestId('defence-web-search-toggle').click()
  await expect(page.getByTestId('defence-web-search-toggle')).toHaveAttribute('aria-pressed', 'true')
  const defenceInput = page.getByTestId('defence-chat-input')
  await defenceInput.fill(
    'If Redis fails or evicts hot keys, circuit-broken read-through queries hit a read replica with single-flight coalescing.'
  )
  await page.getByTestId('defence-send-btn').click()
  await expect(page.getByText(/\[Web-Grounded Context\]/)).toBeVisible()
  await expect(page.getByTestId('stage-step-COMPLETED')).toBeEnabled()

  // Stage 5: Complete local AI evaluation first, then switch to Frontier Second Opinion tab
  await page.getByTestId('evaluate-session-btn').click()
  await expect(page.getByRole('heading', { name: 'Final Interview Scorecard' })).toBeVisible()
  await expect(page.getByText('INTERVIEW READY')).toBeVisible()
  await expect(page.getByTestId('frontier-packet-card')).toHaveCount(0)

  await page.getByTestId('toggle-frontier-panel-btn').click()
  await expect(page.getByTestId('frontier-packet-card')).toBeVisible()
  await page.getByTestId('prepare-frontier-packet-btn').click()
  const packetTextarea = page.getByTestId('frontier-packet-textarea')
  await expect(packetTextarea).toBeVisible()
  await expect(packetTextarea).toHaveValue(/ASSISTED \/ HINT REQUESTED/)
  await expect(packetTextarea).toHaveValue(/Requirements Clarity/)

  await page.getByTestId('import-frontier-textarea').fill(`\`\`\`json
{
  "overall_score": 92,
  "readiness_rating": "STRONG_HIRE",
  "executive_summary": "Frontier review confirms disciplined edge caching and circuit-breaker design.",
  "rubric_scores": [
    {
      "dimension": "Right-Sizing & Simplicity (YAGNI)",
      "score": 5,
      "evidence": "Kept stateless API and Redis cache ahead of Postgres without premature microservices.",
      "critique": "Clean balance of simplicity and failover resilience."
    }
  ],
  "key_strengths": ["Circuit-broken cache degradation"],
  "critical_gaps": ["Document multi-AZ replica failover RTO"],
  "recommended_next_steps": ["Add p99 tail latency budget alert thresholds"]
}
\`\`\``)
  await page.getByTestId('import-frontier-submit-btn').click()
  await expect(page.getByText('STRONG HIRE')).toBeVisible()
  await expect(page.locator('.eval-score-value')).toHaveText('92')
  await expect(page.getByText('Right-Sizing & Simplicity (YAGNI)')).toBeVisible()

  expect(errors).toEqual([])
})

test('preserves URL session recovery (F-06), custom challenge fields on edit (F-07), session history on delete (F-05), and Queue SD filters (F-04)', async ({
  page,
  isMobile,
}) => {
  const errors = []
  page.on('pageerror', (err) => errors.push(err.message))
  page.on('console', (msg) => {
    if (msg.type() === 'warning' && msg.text().includes('[Vue warn]')) {
      errors.push(msg.text())
    }
  })

  await page.goto('/chat?mode=system_design')
  await expect(page.getByRole('heading', { name: 'Interview Challenge Scenarios' })).toBeVisible()

  // F-07: Create custom manual challenge with tags, expected components, and scale notes
  await page.getByTestId('open-new-challenge-modal-btn').click()
  await page.getByTestId('tab-manual-challenge').click()
  await page.getByTestId('manual-title-input').fill('Design a Webhook Audit Bus')
  await page.getByTestId('manual-summary-input').fill('Reliable webhook delivery with audit persistence.')
  await page.getByTestId('manual-prompt-input').fill('Design an audit-grade webhook delivery pipeline.')
  await page.getByTestId('manual-tags-input').fill('webhooks, queues')
  await page.getByTestId('manual-expected-components-input').fill('API Gateway\nRetry Queue')
  await page.getByTestId('manual-scale-notes-input').fill('5k events/sec peak, 100ms p99')
  await page.getByTestId('submit-manual-challenge-btn').click()
  await expect(page.getByText('Design a Webhook Audit Bus')).toBeVisible()

  const customCard = page.locator('.challenge-card', { hasText: 'Design a Webhook Audit Bus' })

  // Edit custom challenge -> pre-populated fields must appear and preserve updates
  await customCard.getByTestId('edit-challenge-btn').click()
  await expect(page.getByTestId('manual-tags-input')).toHaveValue('webhooks, queues')
  await expect(page.getByTestId('manual-expected-components-input')).toHaveValue('API Gateway\nRetry Queue')
  await expect(page.getByTestId('manual-scale-notes-input')).toHaveValue('5k events/sec peak, 100ms p99')
  await page.getByTestId('manual-expected-components-input').fill('API Gateway\nRetry Queue\nDead-Letter Store')
  await page.getByTestId('manual-scale-notes-input').fill('10k events/sec peak, 99.99% delivery')
  await page.getByTestId('submit-manual-challenge-btn').click()

  await customCard.getByTestId('edit-challenge-btn').click()
  await expect(page.getByTestId('manual-expected-components-input')).toHaveValue(
    'API Gateway\nRetry Queue\nDead-Letter Store'
  )
  await expect(page.getByTestId('manual-scale-notes-input')).toHaveValue('10k events/sec peak, 99.99% delivery')
  await page.getByRole('button', { name: 'Cancel' }).click()

  // F-06: Start challenge -> URL gets ?mode=system_design&sessionId=...
  await customCard.getByTestId('start-challenge-btn').click()
  await expect(page.getByTestId('back-to-challenges-btn')).toBeVisible()
  await expect(page).toHaveURL(/mode=system_design.*sessionId=\d+/)

  // Reload page -> recovers the exact active session
  await page.reload()
  await expect(page.getByTestId('back-to-challenges-btn')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Design a Webhook Audit Bus' })).toBeVisible()

  // Browser Back -> returns to lobby without sessionId; Browser Forward -> reopens session
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Interview Challenge Scenarios' })).toBeVisible()
  await expect(page).not.toHaveURL(/sessionId=/)
  await page.goForward()
  await expect(page.getByTestId('back-to-challenges-btn')).toBeVisible()
  await page.getByTestId('back-to-challenges-btn').click()
  await expect(page.getByRole('heading', { name: 'Interview Challenge Scenarios' })).toBeVisible()

  // F-05: Deleting a challenge that has a session archives the card but keeps session history accessible
  await customCard.getByTestId('delete-challenge-btn').click()
  await expect(page.locator('.challenge-card', { hasText: 'Design a Webhook Audit Bus' })).toHaveCount(0)
  if (isMobile) {
    const expandBtn = page.locator('.btn-expand-sidebar')
    if (await expandBtn.isVisible()) {
      await expandBtn.click()
    }
  }
  const sidebarSessionItem = page
    .locator('.chat-list-item.interview-session-item', { hasText: 'Design a Webhook Audit Bus' })
    .first()
  await expect(sidebarSessionItem).toBeVisible()
  await sidebarSessionItem.click()
  await expect(page.getByTestId('back-to-challenges-btn')).toBeVisible()

  // F-04: QueueView exposes SD Review and SD Eval filters
  await page.goto('/queue')
  await expect(page.getByTestId('queue-filter-sd-review')).toBeVisible()
  await expect(page.getByTestId('queue-filter-sd-eval')).toBeVisible()
  await page.getByTestId('queue-filter-sd-review').click()
  await page.getByTestId('queue-filter-sd-eval').click()

  expect(errors).toEqual([])
})

test('supports seeded blind starts, explicit variant picker, sidebar seed display, seed replay, and QueueView deep-link', async ({
  page,
  isMobile,
}) => {
  const errors = []
  page.on('pageerror', (err) => errors.push(err.message))
  page.on('console', (msg) => {
    if (msg.type() === 'warning' && msg.text().includes('[Vue warn]')) {
      errors.push(msg.text())
    }
  })

  await page.goto('/chat?mode=system_design')
  await expect(page.getByTestId('open-seed-modal-lobby-btn')).toBeVisible()

  // 1-click Start -> rolls blind seed and hides variant title
  const urlCard = page.getByTestId('challenge-card-url-shortener')
  await urlCard.getByTestId('start-challenge-btn').click()
  await expect(page.getByTestId('active-session-seed-badge')).toBeVisible()
  const seedBadgeText = await page.getByTestId('active-session-seed-badge').innerText()
  const rolledSeed = seedBadgeText.replace('Seed: #', '').trim()
  expect(rolledSeed.length).toBeGreaterThanOrEqual(4)
  await expect(page.getByTestId('active-session-blind-badge')).toBeVisible()
  await expect(page.getByTestId('active-session-variant-badge')).toHaveCount(0)

  // Active Session Header -> New Variant / Replay Seed modal -> explicit Variant selection
  await page.getByTestId('open-seed-modal-active-btn').click()
  await expect(page.getByTestId('seed-variant-modal')).toBeVisible()
  await page.getByTestId('seed-mode-variant-btn').click()
  await page.getByTestId('seed-variant-option-enterprise-compliance').click()
  await page.getByTestId('seed-modal-launch-btn').click()

  await expect(page.getByTestId('active-session-variant-badge')).toHaveText(
    'Enterprise Compliance Profile'
  )
  const explicitSessionUrl = page.url()
  const explicitSessionIdMatch = explicitSessionUrl.match(/sessionId=(\d+)/)
  expect(explicitSessionIdMatch).not.toBeNull()
  const explicitSessionId = Number(explicitSessionIdMatch[1])

  // Back to challenges -> no duplicate bottom session list; AgentChatView sidebar shows seeds & revealed variant
  await page.getByTestId('back-to-challenges-btn').click()
  await expect(page.getByTestId('past-sessions-section')).toHaveCount(0)

  if (isMobile) {
    const expandBtn = page.locator('.btn-expand-sidebar')
    if (await expandBtn.isVisible()) {
      await expandBtn.click()
    }
  }
  const sidebarItems = page.locator('.chat-list-item.interview-session-item')
  await expect(sidebarItems.filter({ hasText: `#${rolledSeed}` })).toBeVisible()
  await expect(sidebarItems.filter({ hasText: 'Enterprise Compliance Profile' })).toBeVisible()

  // Close sidebar on mobile before opening Lobby seed modal
  if (isMobile) {
    const closeSidebarBtn = page.locator('.btn-icon-sidebar[title="Collapse Sidebar"]')
    if (await closeSidebarBtn.isVisible()) {
      await closeSidebarBtn.click()
    }
  }

  // Replay rolledSeed via Lobby modal -> keeps profile blind while matching deterministic seed
  await page.getByTestId('open-seed-modal-lobby-btn').click()
  await page.getByTestId('seed-mode-seed-btn').click()
  await page.getByTestId('seed-modal-seed-input').fill(rolledSeed)
  await page.getByTestId('seed-modal-launch-btn').click()
  await expect(page.getByTestId('active-session-seed-badge')).toHaveText(`Seed: #${rolledSeed}`)
  await expect(page.getByTestId('active-session-blind-badge')).toBeVisible()

  // QueueView -> System Design task links directly to /chat?mode=system_design&sessionId=... (not /agent)
  await page.evaluate((sid) => {
    const raw = localStorage.getItem('jt_demo_db_v1')
    const db = raw ? JSON.parse(raw) : {}
    db.intake_evaluations = [
      {
        id: 9901,
        task_type: 'SYSTEM_DESIGN_EVALUATION',
        status: 'COMPLETED',
        stage: 'COMPLETED',
        progress: 100,
        company_name: 'System Design Lab',
        role_title: 'Design a URL Shortener',
        result_json: {
          session_id: sid,
          overall_score: 91,
          readiness_rating: 'STRONG_HIRE',
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      ...(db.intake_evaluations || []),
    ]
    localStorage.setItem('jt_demo_db_v1', JSON.stringify(db))
  }, explicitSessionId)

  await page.goto('/queue')
  await page.getByTestId('queue-filter-sd-eval').click()
  const openSessionLink = page.getByTestId('queue-open-sd-session-btn').first()
  await expect(openSessionLink).toBeVisible()
  await expect(openSessionLink).toHaveAttribute(
    'href',
    `/chat?mode=system_design&sessionId=${explicitSessionId}`
  )
  await openSessionLink.click()
  await expect(page).toHaveURL(new RegExp(`/chat\\?mode=system_design&sessionId=${explicitSessionId}`))
  await expect(page.getByTestId('active-session-variant-badge')).toHaveText(
    'Enterprise Compliance Profile'
  )

  expect(errors).toEqual([])
})

test('Tailored Challenge Modal filters active apps with fuzzy search, prepares Frontier Prompt, detects 409 duplicates, and imports JSON', async ({
  page,
}) => {
  const errors = []
  page.on('pageerror', (err) => errors.push(err.message))

  await page.goto('/chat?mode=system_design')
  await page.evaluate(() => {
    const raw = localStorage.getItem('jt_demo_db_v1')
    const db = raw ? JSON.parse(raw) : {}
    const apps = [
      {
        id: 8101,
        company_id: 8101,
        company_name: 'Rejected Legacy Co',
        company: { id: 8101, name: 'Rejected Legacy Co', notes: 'Old notes' },
        position: 'Legacy Backend Engineer',
        status: 'REJECTED',
        notes: 'Should never appear in ongoing picker',
      },
      {
        id: 8102,
        company_id: 8102,
        company_name: 'Applied Cloud Startup',
        company: { id: 8102, name: 'Applied Cloud Startup' },
        position: 'Platform Engineer',
        status: 'APPLIED',
        notes: '',
      },
      {
        id: 8103,
        company_id: 8103,
        company_name: 'Stripe Infrastructure',
        company: {
          id: 8103,
          name: 'Stripe Infrastructure',
          notes: 'Multi-region ledger cells and idempotency keys',
        },
        position: 'Staff Systems Engineer',
        status: 'TECHNICAL_INTERVIEW',
        notes: 'Recruiter hinted deep focus on webhook ordering and Kafka DLQs',
        job_posting: {
          description_markdown: 'Build resilient global payment event pipelines.',
          required_skills: ['Go', 'Kafka', 'PostgreSQL'],
        },
      },
    ]
    db.applications = apps
    localStorage.setItem('jt_demo_db_v1', JSON.stringify(db))
  })
  await page.reload()
  await expect(page.locator('.sd-challenges-grid')).toBeVisible()

  await page.getByTestId('open-new-challenge-modal-btn').click()
  await expect(page.getByTestId('new-challenge-modal')).toBeVisible()
  await expect(page.getByTestId('tab-generate-challenge')).toHaveClass(/active/)
  await expect(page.getByTestId('tab-frontier-challenge')).toBeVisible()
  // Frontier Chat panel should NOT clutter the AI Generate tab before switching
  await expect(page.getByTestId('frontier-challenge-panel')).toHaveCount(0)

  // Clicking Prepare Frontier Prompt with empty topic and no selected app shows explicit validation without asking for Extra Focus
  await page.getByTestId('prepare-frontier-challenge-prompt-btn').click()
  await expect(page.getByTestId('tailor-input-error')).toBeVisible()
  await expect(page.getByTestId('tailor-input-error')).toContainText('Topic / Scenario Focus')
  await expect(page.getByTestId('tailor-input-error')).not.toContainText('extra focus')
  await expect(page.getByTestId('tab-generate-challenge')).toHaveClass(/active/)

  const pickerList = page.getByTestId('tailor-app-picker-list')
  await expect(pickerList).not.toContainText('Rejected Legacy Co')
  await expect(pickerList).toContainText('Applied Cloud Startup')
  await expect(pickerList).toContainText('Stripe Infrastructure')

  // Switch to Interview & OA Only -> hides APPLIED, retains TECHNICAL_INTERVIEW
  await page.getByTestId('app-stage-filter-interview').click()
  await expect(pickerList).not.toContainText('Applied Cloud Startup')
  await expect(pickerList).toContainText('Stripe Infrastructure')

  // Switch back to Active Ongoing & verify fuzzy match finds Stripe Infrastructure
  await page.getByTestId('app-stage-filter-active').click()
  await page.getByTestId('challenge-app-search-input').fill('strp infra')
  await expect(pickerList).toContainText('Stripe Infrastructure')
  await expect(pickerList).not.toContainText('Applied Cloud Startup')

  await page.getByTestId('tailor-app-option-8103').click()
  await expect(page.getByTestId('tailor-input-error')).toHaveCount(0)
  await expect(page.getByTestId('selected-tailor-app')).toContainText('Stripe Infrastructure')
  await expect(page.getByTestId('challenge-context-signals')).toContainText('Application Notes')

  await page
    .getByTestId('generate-extra-context-input')
    .fill('Emphasize transactional outbox vs CDC trade-offs.')
  await expect(page.getByTestId('challenge-context-signals')).toContainText('Extra Focus Clues')

  // Prepare Frontier Prompt -> auto-switches to clean Frontier Chat tab & prepares prompt
  await page.getByTestId('prepare-frontier-challenge-prompt-btn').click()
  await expect(page.getByTestId('tab-frontier-challenge')).toHaveClass(/active/)
  await expect(page.getByTestId('frontier-challenge-panel')).toBeVisible()
  const promptPreview = page.getByTestId('frontier-challenge-prompt-preview')
  await expect(promptPreview).toBeVisible()
  const promptVal = await promptPreview.inputValue()
  expect(promptVal).toContain('Recruiter hinted deep focus on webhook ordering')
  expect(promptVal).toContain('EXISTING CHALLENGES — DO NOT DUPLICATE')
  expect(promptVal).toContain('Design a URL Shortener')

  // Attempt importing a duplicate overlapping URL Shortener -> triggers 409 warning banner + Create Anyway
  const dupPayload = JSON.stringify({
    title: 'Build a URL Shortener Service',
    category: 'DISTRIBUTED_SYSTEMS',
    difficulty: 'MEDIUM',
    prompt_summary: 'Shorten links cleanly with low latency redirects.',
    initial_prompt: 'Design a short link platform.',
    interviewer_brief: { expected_components: ['API', 'KV'], defence_questions: ['How handle hot keys?'] },
  })
  await page.getByTestId('import-frontier-challenge-input').fill(dupPayload)
  await page.getByTestId('import-frontier-challenge-submit-btn').click()
  await expect(page.getByTestId('duplicate-challenge-warning')).toBeVisible()
  await expect(page.getByTestId('create-anyway-challenge-btn')).toBeVisible()

  // Replace with distinct frontier-generated challenge JSON & import cleanly
  const validPayload = JSON.stringify({
    title: 'Design a Stripe Webhook Delivery Ledger',
    category: 'DISTRIBUTED_SYSTEMS',
    difficulty: 'HARD',
    prompt_summary: 'Ordered, idempotent webhook fanout and DLQ isolation at payment scale.',
    initial_prompt: 'Design a multi-tenant webhook delivery ledger for payment state transitions.',
    tags: ['webhooks', 'stripe', 'frontier-imported'],
    interviewer_brief: {
      variants: [
        {
          variant_id: 'burst-dlq',
          title: 'Merchant Burst & Tenant DLQ',
          focus_summary: 'Noisy neighbor queue isolation under traffic spikes.',
          expected_components: ['Outbox Poller', 'Partitioned Queue', 'Tenant DLQ'],
          defence_questions: ['How do you isolate one slow merchant webhook endpoint?'],
        },
        {
          variant_id: 'strict-ordering',
          title: 'Strict Event Ordering Profile',
          focus_summary: 'Per-account sequence guarantees without head-of-line stalling.',
          expected_components: ['Sequence Ledger', 'Circuit Breaker'],
          defence_questions: ['How do you recover sequence gaps after regional failover?'],
        },
      ],
    },
  })
  await page.getByTestId('import-frontier-challenge-input').fill(`\`\`\`json\n${validPayload}\n\`\`\``)
  await page.getByTestId('import-frontier-challenge-submit-btn').click()

  await expect(page.getByTestId('new-challenge-modal')).toBeHidden()
  await expect(page.locator('.sd-challenges-grid')).toContainText('Design a Stripe Webhook Delivery Ledger')

  expect(errors).toEqual([])
})

test('builds architecture in Interactive Canvas Builder with Studio Coach Chat, Undo, Reveal Requirements, and Solo/Coached XP', async ({
  page,
}, testInfo) => {
  const errors = []
  page.on('pageerror', (err) => errors.push(err.message))
  page.on('console', (msg) => {
    if (msg.type() === 'warning' && msg.text().includes('[Vue warn]')) {
      errors.push(msg.text())
    }
  })

  await page.goto('/chat?mode=system_design')
  await page.getByTestId('challenge-card-url-shortener').getByTestId('start-challenge-btn').click()

  // Stage 1: Verify Reveal Requirements shortcut & live Q&A ledger population, then lock and jump to Studio
  await expect(page.getByTestId('reveal-requirements-btn')).toBeVisible()
  await expect(page.getByTestId('jump-to-studio-btn')).toBeVisible()
  await page.getByTestId('req-chat-input').fill('What read/write traffic targets apply?')
  await page.getByTestId('req-send-btn').click()
  await expect(page.locator('textarea').nth(1)).toHaveValue(/Core API/)
  await page.getByRole('button', { name: 'Lock Requirements & Proceed to Diagram' }).click()

  // Dedicated full-screen Design Studio route with minimal header (no 3-mode switcher, no -pts badge)
  await expect(page).toHaveURL(/\/system-design\/\d+\/design/)
  await expect(page.getByTestId('design-studio-page')).toBeVisible()
  await expect(page.getByTestId('diagram-canvas-builder')).toBeVisible()
  await expect(page.getByTestId('stage-step-DESIGN')).toHaveCount(0)
  await expect(page.getByTestId('studio-mode-switcher')).toHaveCount(0)
  await expect(page.getByTestId('guidance-penalty-badge')).toHaveCount(0)
  await expect(page.getByTestId('studio-assistance-pill')).toContainText('Solo')

  // Desktop opens with 4-Tab Docked Sidebar on Reqs tab (and zero redundant topbar toggle button); mobile opens collapsed
  if (testInfo.project.name.includes('mobile')) {
    await expect(page.getByTestId('learning-coach-drawer')).toHaveCount(0)
    await expect(page.getByTestId('toggle-coach-drawer-btn')).toBeVisible()
    await page.getByTestId('toggle-coach-drawer-btn').click()
  } else {
    await expect(page.getByTestId('toggle-coach-drawer-btn')).toHaveCount(0)
  }
  await expect(page.getByTestId('learning-coach-drawer')).toBeVisible()
  await expect(page.getByTestId('studio-requirements-reference')).toBeVisible()
  await page
    .getByTestId('canvas-notes-input')
    .fill('Edge gateway routes hot lookups to Redis Cluster and async key invalidation.')

  // Switch to Coach tab -> Apply to Canvas + Undo
  await page.getByTestId('coach-tab-chat').click()
  await page.getByTestId('coach-starter-write-path').click()
  await expect(page.getByTestId('coach-chat-thread')).toContainText('Write Path')
  await page.getByTestId('coach-apply-action-btn').first().click()
  await expect(page.getByTestId('studio-undo-btn')).toBeVisible()
  await expect(page.getByTestId('studio-assistance-pill')).toContainText('Coached')
  await page.getByTestId('studio-undo-btn').click()
  await expect(page.getByTestId('studio-undo-btn')).toHaveCount(0)

  // Switch to Bank tab: Next Hint & Reveal All Required (clicking twice does NOT crash!)
  await page.getByTestId('coach-tab-bank').click()
  await page.getByTestId('hint-next-component-btn').click()
  await expect(page.getByTestId('diagram-hint-tray')).toBeVisible()

  await page.getByTestId('reveal-bank-btn').click()
  await expect(page.getByTestId('diagram-hint-tray')).toContainText('URL / Payload Safety Filter')
  await page.getByTestId('reveal-bank-btn').click()
  await expect(page.getByTestId('reveal-bank-btn')).toBeEnabled()
  await expect(page.getByTestId('path-milestones-section')).toContainText('Read Path')
  await expect(page.getByTestId('diagram-hint-tray')).toContainText('Task Queue')
  await expect(page.getByTestId('diagram-hint-tray')).not.toContainText('Flink')

  // Collapse sidebar on mobile (or test desktop collapse/reopen cycle) before canvas interactions
  await page.getByTestId('collapse-studio-sidebar-btn').click()
  await expect(page.getByTestId('learning-coach-drawer')).toHaveCount(0)
  await expect(page.getByTestId('toggle-coach-drawer-btn')).toBeVisible()
  if (!testInfo.project.name.includes('mobile')) {
    await page.getByTestId('toggle-coach-drawer-btn').click()
    await expect(page.getByTestId('learning-coach-drawer')).toBeVisible()
    await expect(page.getByTestId('toggle-coach-drawer-btn')).toHaveCount(0)
  }

  // Inspect ? explanation popover inside Guided Bank
  await page.getByTestId('hint-info-btn').first().click()
  await expect(page.getByTestId('hint-info-popover')).toBeVisible()

  // Add canonical blocks from palette + create a Custom Block
  await page.getByTestId('palette-search-input').fill('Redis')
  await page.getByTestId('palette-block-distributed_cache').click()
  await page.getByTestId('palette-search-input').fill('')
  await page.getByTestId('palette-block-api_gateway').click()

  await page.getByTestId('open-custom-block-btn').click()
  await page.getByTestId('custom-block-name-input').fill('Base62 Key Ring')
  await page.getByTestId('custom-block-tech-input').fill('Go + Etcd Lease')
  await page.getByTestId('add-custom-block-btn').click()

  await expect(page.getByTestId('canvas-node-distributed_cache')).toBeVisible()
  await expect(page.getByTestId('canvas-node-api_gateway')).toBeVisible()
  await expect(page.getByTestId('canvas-node-custom')).toBeVisible()

  // Fit view then wire handle-to-handle directly on the canvas -> opens inline wire popover automatically
  await page.getByRole('button', { name: 'Fit' }).click()
  const srcHandle = page
    .getByTestId('canvas-node-distributed_cache')
    .locator('.vue-flow__handle.source')
    .first()
  const dstHandle = page
    .getByTestId('canvas-node-api_gateway')
    .locator('.vue-flow__handle.target')
    .first()
  await srcHandle.scrollIntoViewIfNeeded()
  await dstHandle.scrollIntoViewIfNeeded()
  if (testInfo.project.name.includes('mobile')) {
    await srcHandle.dispatchEvent('click')
    await dstHandle.dispatchEvent('click')
  } else {
    const srcBox = await srcHandle.boundingBox()
    const dstBox = await dstHandle.boundingBox()
    await page.mouse.move(srcBox.x + srcBox.width / 2, srcBox.y + srcBox.height / 2)
    await page.mouse.down()
    await page.mouse.move(dstBox.x + dstBox.width / 2, dstBox.y + dstBox.height / 2, { steps: 12 })
    await page.mouse.up()
  }

  await expect(page.getByTestId('edge-popover')).toBeVisible()
  await page.getByTestId('edge-label-input').fill('Invalidates key cache')
  await page.getByTestId('edge-async-checkbox').check()
  await page.getByTestId('edge-popover').getByRole('button', { name: 'Done' }).click()
  await expect(page.getByTestId('edge-popover')).toHaveCount(0)

  // Clicking the drawn wire label re-opens inline popover with saved label
  await page.locator('.vue-flow__edge-textwrapper').first().click()
  await expect(page.getByTestId('edge-popover')).toBeVisible()
  await expect(page.getByTestId('edge-label-input')).toHaveValue('Invalidates key cache')
  await page.getByTestId('edge-popover').getByRole('button', { name: 'Done' }).click()

  // Open More -> View Flow JSON modal to verify structured flow JSON
  await page.getByTestId('studio-more-btn').click()
  await page.getByTestId('open-flow-json-modal-btn').click()
  await expect(page.getByTestId('studio-flow-json-modal')).toBeVisible()
  await expect(page.getByTestId('flow-json-preview')).toContainText('"nodes"')
  await page.getByTestId('studio-flow-json-modal').getByRole('button', { name: 'Close' }).click()

  // Open sidebar (on mobile) -> Checks tab & run Check Topology
  if (testInfo.project.name.includes('mobile')) {
    await page.getByTestId('toggle-coach-drawer-btn').click()
  }
  await page.getByTestId('coach-tab-checks').click()
  await page.getByTestId('check-topology-btn').click()
  await expect(page.getByTestId('topology-diagnostics-section')).toBeVisible()

  // Save Canvas Revision v1 & run Stage 3 Review -> redirects cleanly back to Stage 3 critique
  await page.getByTestId('save-canvas-btn').click()
  await page.getByTestId('analyze-canvas-btn').click()

  await expect(page).toHaveURL(/\/chat\?mode=system_design.*stage=REVIEW/)
  await expect(page.getByRole('heading', { name: 'Architecture Critique' })).toBeVisible()
  await expect(page.getByText('Visual Clarifications Needed')).toHaveCount(0)

  // Clicking Revise in Design Studio opens Studio with Stage 3 Fix Checklist open in Checks tab
  await page.getByTestId('revise-in-studio-btn').click()
  await expect(page).toHaveURL(/\/system-design\/\d+\/design.*fixReview=1/)
  await expect(page.getByTestId('review-fix-checklist')).toBeVisible()
  await page.getByTestId('studio-back-btn').click()
  await page.getByTestId('stage-step-REVIEW').click()

  // Proceed through Stage 4 Defence to Stage 5 Evaluation & check zero penalty + Coached Run + 100 XP
  await page.getByRole('button', { name: 'Proceed to Architecture Defence' }).click()
  await page.getByTestId('defence-chat-input').fill('Cache misses fall back cleanly to read replicas with singleflight coalescing.')
  await page.getByTestId('defence-send-btn').click()
  await page.getByTestId('evaluate-session-btn').click()

  await expect(page.locator('.eval-score-value')).toHaveText('86')
  await expect(page.getByTestId('eval-assistance-badge')).toContainText('Coached Run')
  await expect(page.getByTestId('eval-xp-badge')).toContainText('+100 XP')

  expect(errors).toEqual([])
})
