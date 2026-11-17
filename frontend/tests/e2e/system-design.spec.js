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

  // Audit & upgrade custom challenge in-place via Frontier bridge inside Edit modal
  await page.getByTestId('edit-challenge-btn').last().click()
  await page.getByTestId('challenge-audit-frontier-toggle').click()
  await page.getByTestId('challenge-audit-frontier-prepare-btn').click()
  await expect(page.getByTestId('challenge-audit-frontier-prompt-preview')).toHaveValue(/Design an Enterprise Webhook Bus/)
  await page.getByTestId('challenge-audit-frontier-import-input').fill(
    JSON.stringify({
      title: 'Design a Global Webhook Relay',
      category: 'DISTRIBUTED_SYSTEMS',
      difficulty: 'HARD',
      prompt_summary: 'Upgraded geo-distributed webhook relay scenario.',
      initial_prompt: 'Design a geo-replicated webhook delivery engine.',
      tags: ['webhooks', 'upgraded'],
    })
  )
  await page.getByTestId('challenge-audit-frontier-import-btn').click()
  await expect(page.getByRole('heading', { name: 'Design a Global Webhook Relay' })).toBeVisible()

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
  await page.getByTestId('lock-requirements-btn').click()

  // Locking Stage 1 opens the dedicated full-screen Design Studio; Back returns to Stage 2 card for image upload
  await expect(page).toHaveURL(/\/system-design\/\d+\/design/)
  await expect(page.getByTestId('design-studio-page')).toBeVisible()
  await page.getByTestId('studio-back-btn').click()

  await expect(page.getByTestId('open-design-studio-btn')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Upload Architecture Diagram' })).toBeVisible()
  await expect(page.getByTestId('stage-step-DESIGN')).toBeEnabled()
  await expect(page.getByTestId('stage-step-REVIEW')).toBeDisabled()
  await expect(page.locator('.sd-brief-disclosure')).toHaveCount(0)

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
  await expect(page.locator('.sd-critique-copy')).toContainText('[Web-Grounded]')
  await expect(page.locator('.sd-critique-disclosure')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Visual Clarifications Needed' })).toBeVisible()
  await expect(page.getByTestId('stage-step-DEFENCE')).toBeEnabled()

  await page.getByTestId('stage-step-DESIGN').click()
  await expect(page.getByTestId('diagram-review-summary')).toBeVisible()
  await expect(page.getByTestId('diagram-review-summary')).not.toContainText('[Web-Grounded]')
  await expect(page.locator('.sd-review-summary-copy')).toHaveCount(0)
  await expect(page.locator('.sd-revision-row')).toHaveCount(1)
  await expect(page.locator('.sd-revision-preview')).toContainText(
    'Added Redis cache ahead of Postgres primary'
  )
  await expect(page.getByTestId('diagram-review-summary').locator('.sd-review-metric')).toHaveCount(3)
  await expect(
    page.getByTestId('diagram-review-summary').getByRole('button', { name: 'Open Full Critique' })
  ).toHaveClass(/btn-primary/)
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

  // QueueView -> System Design tasks (completed + failed) link directly to /chat?mode=system_design&sessionId=... & never show Edit Job Description
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
      {
        id: 9902,
        task_type: 'SYSTEM_DESIGN_REVIEW',
        status: 'FAILED',
        stage: 'ANALYZING',
        error_message: 'LM Studio connection timed out',
        title_hint: 'System Design Review • Design a URL Shortener',
        result_json: { session_id: sid },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 9903,
        task_type: 'EMAIL_SYNC',
        status: 'FAILED',
        stage: 'FAILED',
        error_message: 'IMAP credentials rejected',
        title_hint: 'Inbox Sync',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 9904,
        task_type: 'JOB_ASSESSMENT',
        status: 'FAILED',
        stage: 'SCRAPING',
        error_message: 'SCRAPE_FAILED: Cloudflare blocked',
        title_hint: 'Staff Backend Engineer Lead',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      ...(db.intake_evaluations || []),
    ]
    localStorage.setItem('jt_demo_db_v1', JSON.stringify(db))
  }, explicitSessionId)

  await page.goto('/queue')
  await page.getByTestId('queue-filter-sd-review').click()
  const failedSdCard = page.locator('.task-card', { hasText: 'LM Studio connection timed out' })
  await expect(failedSdCard).toBeVisible()
  await expect(failedSdCard.getByTestId('queue-fix-jd-btn')).toHaveCount(0)
  await expect(failedSdCard).not.toContainText('Edit Job Description')
  await expect(failedSdCard).not.toContainText('Provide Description')
  await expect(failedSdCard.getByTestId('queue-error-sd-link')).toHaveAttribute(
    'href',
    `/chat?mode=system_design&sessionId=${explicitSessionId}`
  )

  await page.getByRole('button', { name: 'All Types' }).click()
  const failedEmailCard = page.locator('.task-card', { hasText: 'IMAP credentials rejected' })
  await expect(failedEmailCard.getByTestId('queue-fix-jd-btn')).toHaveCount(0)
  await expect(failedEmailCard.getByTestId('queue-error-email-link')).toHaveAttribute(
    'href',
    '/settings?tab=email_accounts'
  )
  const failedJobCard = page.locator('.task-card', { hasText: 'SCRAPE_FAILED: Cloudflare blocked' })
  await expect(failedJobCard.getByTestId('queue-fix-jd-btn')).toBeVisible()

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
  test.slow()
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
  await page.getByTestId('lock-requirements-btn').click()

  // Dedicated full-screen Design Studio route with minimal header (no 3-mode switcher, no -pts badge)
  await expect(page).toHaveURL(/\/system-design\/\d+\/design/)
  await expect(page.getByTestId('design-studio-page')).toBeVisible()
  await expect(page.getByTestId('diagram-canvas-builder')).toBeVisible()
  await expect(page.getByTestId('stage-step-DESIGN')).toHaveCount(0)
  await expect(page.getByTestId('studio-mode-switcher')).toHaveCount(0)
  await expect(page.getByTestId('guidance-penalty-badge')).toHaveCount(0)
  await expect(page.getByTestId('studio-assistance-pill')).toContainText('Solo')

  async function openStudioMore() {
    if (!(await page.getByTestId('studio-more-dropdown').isVisible())) {
      await page.getByTestId('studio-more-btn').click()
    }
  }

  async function clickStudioMoreItem(testId) {
    await openStudioMore()
    await page.getByTestId(testId).click()
  }

  // Studio panels remain visible and cannot disappear behind a collapsed drawer.
  await expect(page.getByTestId('learning-coach-drawer')).toBeVisible()
  await expect(page.getByTestId('palette-collapse-btn')).toHaveCount(0)
  await openStudioMore()
  await expect(page.getByTestId('toggle-coach-drawer-btn')).toHaveCount(0)
  await page.getByTestId('studio-more-btn').click()
  await expect(page.getByTestId('studio-requirements-reference')).toBeVisible()
  await page
    .getByTestId('canvas-notes-input')
    .fill('Edge gateway routes hot lookups to Redis Cluster and async key invalidation.')

  // Switch to Coach tab -> Apply to Canvas + Undo
  await page.getByTestId('coach-tab-chat').click()
  await page.getByTestId('coach-starter-guide').click()
  await expect(page.getByTestId('coach-chat-thread')).toContainText('next missing block or connection')
  await page.getByTestId('coach-starter-write-path').click()
  await expect(page.getByTestId('coach-chat-thread')).toContainText('Write Path')
  await page.getByTestId('coach-apply-action-btn').first().click()
  await expect(page.getByTestId('coach-action-preview-modal')).toBeVisible()
  await expect(page.getByTestId('coach-action-preview-modal')).toContainText('Before')
  await page.getByTestId('confirm-coach-action-btn').click()
  await openStudioMore()
  await expect(page.getByTestId('studio-undo-btn')).toBeVisible()
  await expect(page.getByTestId('studio-assistance-pill')).toContainText('Coached')
  await clickStudioMoreItem('studio-undo-btn')
  await openStudioMore()
  await expect(page.getByTestId('studio-undo-btn')).toHaveCount(0)
  await page.getByTestId('studio-more-btn').click()

  // Guidance lives in the Assistant, not in a canvas-top tray.
  await page.getByTestId('coach-tab-bank').click()
  await expect(page.getByText('Next: reveal the next required block')).toHaveCount(0)
  const revealNextButton = page.getByTestId('reveal-next-step-btn')
  const revealAllButton = page.getByTestId('reveal-bank-btn')
  const [nextButtonBox, allButtonBox] = await Promise.all([
    revealNextButton.boundingBox(),
    revealAllButton.boundingBox(),
  ])
  expect(allButtonBox.y).toBe(nextButtonBox.y)
  expect(allButtonBox.x).toBeGreaterThan(nextButtonBox.x)
  await expect(page.getByTestId('diagram-hint-tray')).toHaveCount(0)
  await revealNextButton.click()
  await expect(page.getByTestId('guided-next-component')).toBeVisible()
  await expect(page.getByTestId('all-revealed-components')).toHaveCount(0)
  await expect(page.getByTestId('guided-next-component').locator('.sd-guided-next-reason')).toHaveText(
    /\S+/
  )

  await page.getByTestId('reveal-bank-btn').click()
  const allRevealed = page.getByTestId('all-revealed-components')
  await allRevealed.locator(':scope > summary').click()
  await expect(allRevealed).toContainText('URL / Payload Safety Filter')
  const featuredBlockName = await page
    .getByTestId('guided-next-component')
    .locator('.sd-guided-next-title strong')
    .innerText()
  await expect(
    allRevealed.locator('.sd-revealed-component > summary').filter({ hasText: featuredBlockName })
  ).toHaveCount(0)
  await page.getByTestId('reveal-bank-btn').click()
  await expect(page.getByTestId('reveal-bank-btn')).toBeEnabled()
  await expect(page.getByTestId('reference-blueprint-framing')).toContainText('Reference Blueprint')
  await expect(page.getByTestId('path-milestones-section')).toContainText('Read Path')
  await expect(allRevealed).toContainText('Task Queue')
  await expect(allRevealed).not.toContainText('Flink')

  // Empty canvas must keep Checks badge at 0 (no 11-item spoiler Missing cards) & show non-spoiling Capability Readiness
  await expect(page.getByTestId('coach-tab-checks').locator('.sd-tab-badge')).toHaveCount(0)
  await page.getByTestId('coach-tab-checks').click()
  await expect(page.getByTestId('capability-readiness-section')).toBeVisible()
  await expect(page.getByTestId('topology-diagnostics-section')).not.toContainText('not yet on canvas')
  await page.getByTestId('coach-tab-bank').click()

  // Clicking Build Flow in Bank constructs an Undo-able end-to-end flow on canvas
  await page.getByTestId('build-path-flow-btn').first().click()
  await expect(page.getByTestId('coach-action-preview-modal')).toBeVisible()
  await page.getByTestId('confirm-coach-action-btn').click()
  await expect(page.getByTestId('canvas-node-web_client')).toBeVisible()
  await openStudioMore()
  await expect(page.getByTestId('studio-undo-btn')).toBeEnabled()
  await clickStudioMoreItem('studio-undo-btn')
  await expect(page.getByTestId('canvas-node-web_client')).toHaveCount(0)

  // Verify Reqs Scale Math, Bank Study Notes, and External Coach workflow while sidebar is open
  await page.getByTestId('studio-tab-reqs').click()
  await expect(page.getByTestId('studio-scale-math-card')).toBeVisible()

  await page.getByTestId('coach-tab-bank').click()
  await expect(page.getByTestId('bank-study-notes')).toBeVisible()

  await page.getByTestId('coach-tab-chat').click()
  await page.getByTestId('toggle-external-coach-btn').click()
  await page.getByTestId('copy-external-coach-initial-btn').click()
  await expect(page.getByTestId('frontier-coach-prompt-preview')).toHaveValue(/External System Design Studio Coach/)
  await page.getByTestId('external-coach-action-input').fill(
    JSON.stringify({
      blocks: [
        { type_id: 'api_gateway', label: 'API Gateway' },
        { type_id: 'app_service', label: 'Application Service' },
      ],
      edges: [
        {
          source_type_id: 'api_gateway',
          source_label: 'API Gateway',
          target_type_id: 'app_service',
          target_label: 'Application Service',
          label: 'request',
          delivery_mode: 'sync',
        },
      ],
    })
  )
  await page.getByTestId('apply-external-coach-action-btn').click()
  await expect(page.getByTestId('coach-action-preview-modal')).toBeVisible()
  await expect(page.getByTestId('coach-action-preview-modal')).toContainText('Not on canvas')
  await page.getByTestId('confirm-coach-action-btn').click()
  await expect(page.getByTestId('canvas-node-api_gateway')).toBeVisible()
  await expect(page.getByTestId('canvas-node-app_service')).toBeVisible()

  const gatewayNodeId = await page
    .locator('.vue-flow__node')
    .filter({ has: page.getByTestId('canvas-node-api_gateway') })
    .getAttribute('data-id')
  const edgeId = await page.locator('.vue-flow__edge').first().getAttribute('data-id')
  await page.getByTestId('external-coach-action-input').fill(
    JSON.stringify({
      node_updates: [{ node_id: gatewayNodeId, changes: { tech_stack: 'Reviewed API Engine' } }],
      edge_updates: [
        {
          edge_id: edgeId,
          changes: { delivery_mode: 'async', protocol: 'Kafka', label: 'enqueue request' },
        },
      ],
    })
  )
  await page.getByTestId('apply-external-coach-action-btn').click()
  const editPreview = page.getByTestId('coach-action-preview-modal')
  await expect(editPreview).toContainText('Before')
  await expect(editPreview).toContainText('Technology: Not set')
  await expect(editPreview).toContainText('Technology: Reviewed API Engine')
  await expect(editPreview).toContainText('Delivery: sync')
  await expect(editPreview).toContainText('Delivery: async')
  await page.getByTestId('confirm-coach-action-btn').click()

  await page.getByTestId('canvas-node-api_gateway').click()
  await expect(page.getByTestId('inspector-node-tech')).toHaveValue('Reviewed API Engine')
  await page.getByTestId('node-popover').getByRole('button', { name: 'Done' }).click()
  await page.locator('.vue-flow__edge-textwrapper').first().click()
  await expect(page.getByTestId('edge-label-input')).toHaveValue('enqueue request')
  await expect(page.getByTestId('edge-async-checkbox')).toBeChecked()
  await page.getByTestId('edge-popover').getByRole('button', { name: 'Done' }).click()

  await clickStudioMoreItem('studio-undo-btn')
  await page.getByTestId('canvas-node-api_gateway').click()
  await expect(page.getByTestId('inspector-node-tech')).toHaveValue('')
  await page.getByTestId('node-popover').getByRole('button', { name: 'Done' }).click()
  await page.locator('.vue-flow__edge-textwrapper').first().click()
  await expect(page.getByTestId('edge-label-input')).toHaveValue('request')
  await expect(page.getByTestId('edge-async-checkbox')).not.toBeChecked()
  await page.getByTestId('edge-popover').getByRole('button', { name: 'Done' }).click()
  await clickStudioMoreItem('studio-undo-btn')
  await expect(page.getByTestId('canvas-node-api_gateway')).toHaveCount(0)
  await expect(page.getByTestId('canvas-node-app_service')).toHaveCount(0)
  await page.getByTestId('coach-tab-bank').click()

  // Assistant remains available while using the canvas and More actions.
  await expect(page.getByTestId('learning-coach-drawer')).toBeVisible()
  await openStudioMore()
  await expect(page.getByTestId('toggle-coach-drawer-btn')).toHaveCount(0)
  await page.getByTestId('studio-more-btn').click()

  // The featured item stays out of the revealed list; infrastructure items retain cloud equivalents.
  const revealedBank = page.getByTestId('all-revealed-components')
  await revealedBank.locator(':scope > summary').click()
  const featuredBlock = page.getByTestId('guided-next-component')
  await expect(featuredBlock).toContainText('Web / Browser Client')
  await expect(featuredBlock.getByTestId('hint-cloud-equivalents')).toHaveCount(0)
  const infrastructureHint = revealedBank
    .getByTestId('guided-component-details')
    .filter({ hasText: /CDN|Load Balancer|API Gateway|Distributed Cache/i })
    .first()
  await infrastructureHint.locator(':scope > summary').click()
  const cloudEquivalents = infrastructureHint.getByTestId('hint-cloud-equivalents')
  await cloudEquivalents.locator(':scope > summary').click()
  await expect(cloudEquivalents).toContainText('AWS:')
  await expect(cloudEquivalents).toContainText('Azure:')

  // Switch Cloud Provider Lens -> AWS, verify client actors stay cloud-agnostic while static_hosting + cache translate live
  await page.getByTestId('cloud-provider-select').selectOption('aws')
  await page.getByTestId('palette-block-web_client').click()
  await expect(page.getByTestId('canvas-node-web_client')).toContainText('Web / Browser Client')
  await expect(page.getByTestId('node-cloud-badge-web_client')).toHaveCount(0)

  await page.getByTestId('palette-block-static_hosting').click()
  await expect(page.getByTestId('canvas-node-static_hosting')).toContainText('Amazon S3 + CloudFront SPA')
  await expect(page.getByTestId('node-cloud-badge-static_hosting')).toHaveText('AWS')

  await page.getByTestId('palette-search-input').fill('ElastiCache')
  await page.getByTestId('palette-block-distributed_cache').click()
  await page.getByTestId('palette-search-input').fill('')
  await expect(page.getByTestId('canvas-node-distributed_cache')).toContainText('Amazon ElastiCache (Redis)')
  await expect(page.getByTestId('node-cloud-badge-distributed_cache')).toHaveText('AWS')

  // Component palette stays open and available while placing blocks.
  const apiGatewayPaletteItem = page.getByTestId('palette-block-api_gateway')
  const apiGatewayCategory = page.locator('.sd-palette-category-details').filter({ has: apiGatewayPaletteItem })
  await apiGatewayCategory.locator('summary').click()
  await expect(apiGatewayPaletteItem).toBeVisible()
  await apiGatewayPaletteItem.click()
  await expect(page.getByTestId('canvas-node-api_gateway')).toContainText('Amazon API Gateway')
  await expect(page.getByTestId('all-revealed-components')).toContainText('On canvas')

  // Local helper to drag/tap handle-to-handle directly on the canvas
  async function wireCanvasNodes(srcTypeId, dstTypeId) {
    await page.getByRole('button', { name: 'Fit' }).click()
    const srcHandle = page
      .getByTestId(`canvas-node-${srcTypeId}`)
      .locator('.vue-flow__handle.source')
      .first()
    const dstHandle = page
      .getByTestId(`canvas-node-${dstTypeId}`)
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
  }

  // Wiring Web / Browser Client -> Amazon API Gateway shows live Correct connection toast
  await wireCanvasNodes('web_client', 'api_gateway')
  await expect(page.getByTestId('edge-popover')).toBeVisible()
  await expect(page.locator('.toast-container')).toContainText('Correct connection')
  await page.getByTestId('edge-popover').getByRole('button', { name: 'Done' }).click()

  // Place Primary Relational DB & wire -> Redis to trigger live Wire Warning diagnostic
  await page
    .locator('.sd-palette-category-details')
    .filter({ hasText: 'Databases & Storage' })
    .locator('summary')
    .click()
  await page.getByTestId('palette-block-relational_db').click()
  await wireCanvasNodes('relational_db', 'distributed_cache')
  await expect(page.getByTestId('edge-popover')).toBeVisible()
  await expect(page.locator('.toast-container')).toContainText('Check wire')
  await page.getByTestId('edge-popover').getByRole('button', { name: 'Done' }).click()

  // Switch Cloud Provider Lens to Azure -> live-translates placed canonical nodes & shows Cross-Cloud Equivalents on click
  await page.getByTestId('cloud-provider-select').selectOption('azure')
  await expect(page.getByTestId('canvas-node-api_gateway')).toContainText('Azure API Management (APIM)')
  await expect(page.getByTestId('node-cloud-badge-api_gateway')).toHaveText('Azure')
  await expect(page.getByTestId('canvas-node-web_client')).toContainText('Web / Browser Client')
  await expect(page.getByTestId('node-cloud-badge-web_client')).toHaveCount(0)
  await page.getByTestId('canvas-node-api_gateway').click()
  await expect(page.getByTestId('node-popover')).toBeVisible()
  await expect(page.getByTestId('node-cloud-equivalents')).toContainText('OCI API Gateway')
  await page.getByTestId('node-resilience-chip').first().click()
  await expect(page.getByTestId('inspector-node-notes')).not.toHaveValue('')
  await page.getByTestId('node-popover').getByRole('button', { name: 'Done' }).click()

  await page.getByTestId('open-custom-block-btn').click()
  const customBlockDialog = page.getByTestId('custom-block-form')
  await expect(customBlockDialog).toBeVisible()
  await expect(customBlockDialog).toHaveAttribute('aria-modal', 'true')
  await page.getByTestId('custom-block-name-input').fill('Base62 Key Ring')
  await page.getByTestId('custom-block-tech-input').fill('Go + Etcd Lease')
  await page.getByTestId('add-custom-block-btn').click()
  await expect(page.getByTestId('custom-block-modal')).toHaveCount(0)

  await expect(page.getByTestId('canvas-node-distributed_cache')).toBeVisible()
  await expect(page.getByTestId('canvas-node-api_gateway')).toBeVisible()
  await expect(page.getByTestId('canvas-node-custom')).toBeVisible()

  // Wire handle-to-handle directly on the canvas -> opens inline wire popover automatically
  await wireCanvasNodes('distributed_cache', 'api_gateway')

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

  // Open More -> verify Web Search critique toggle + View Flow JSON modal
  await page.getByTestId('studio-more-btn').click()
  await expect(page.getByTestId('review-web-search-checkbox')).toBeVisible()
  await page.getByTestId('open-flow-json-modal-btn').click()
  await expect(page.getByTestId('studio-flow-json-modal')).toBeVisible()
  await expect(page.getByTestId('flow-json-preview')).toContainText('"nodes"')
  await page.getByTestId('studio-flow-json-modal').getByRole('button', { name: 'Close' }).click()

  // Checks remain available in the persistent Assistant on every viewport.
  await page.getByTestId('coach-tab-checks').click()
  await expect(page.getByTestId('verified-connections-checklist')).toContainText('Correct connection')
  await expect(page.getByTestId('live-wire-warnings')).toContainText('Check wire')
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

  // Proceed through Stage 4 Defence (also exercising External Defence Sparring) to Stage 5 Evaluation
  await page.getByRole('button', { name: 'Proceed to Architecture Defence' }).click()
  await page.getByTestId('toggle-stage4-external-defence-btn').click()
  await expect(
    page.getByRole('dialog', { name: 'Spar in External AI (ChatGPT/Claude)' })
  ).toBeVisible()
  await page.getByTestId('copy-frontier-defence-prompt-btn').click()
  await expect(page.getByTestId('frontier-defence-prompt-preview')).toHaveValue(/External Stage 4 Architecture Defence/)
  await page.getByTestId('import-frontier-defence-textarea').fill('Defended Redis LRU + Read Replica cache-aside fallback under 50ms p99.')
  await page.getByTestId('import-frontier-defence-submit-btn').click()
  await page.getByTestId('defence-chat-input').fill('Cache misses fall back cleanly to read replicas with singleflight coalescing.')
  await page.getByTestId('defence-send-btn').click()
  await page.getByTestId('evaluate-session-btn').click()

  await expect(page.locator('.eval-score-value')).toHaveText('86')
  await expect(page.getByTestId('eval-assistance-badge')).toContainText('Coached Run')
  await expect(page.getByTestId('eval-xp-badge')).toContainText('+100 XP')

  expect(errors).toEqual([])
})

test('keeps System Design Lab stages viewport-fitted in Midnight and Daylight', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name.includes('mobile'))
  test.slow()

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/chat?mode=system_design')
  await page.getByTestId('challenge-card-url-shortener').getByTestId('start-challenge-btn').click()
  await expect(page.getByTestId('req-chat-input')).toBeVisible()

  async function setTheme(theme) {
    await page.evaluate((selectedTheme) => {
      document.documentElement.classList.toggle('daylight', selectedTheme === 'Daylight')
    }, theme)
    if (theme === 'Daylight') {
      await expect(page.locator('html')).toHaveClass(/daylight/)
    } else {
      await expect(page.locator('html')).not.toHaveClass(/daylight/)
    }
  }

  async function captureLayout(stage, selector) {
    await expect(page.locator('.toast-container')).toHaveCount(0)
    for (const theme of ['Midnight', 'Daylight']) {
      await setTheme(theme)
      for (const [width, height] of [
        [1440, 900],
        [1280, 720],
      ]) {
        await page.setViewportSize({ width, height })
        await expect(page.locator(selector)).toBeVisible()
        await page.locator('.sd-embedded-container, .sd-studio-page').first().evaluate(async (root) => {
          await Promise.all(root.getAnimations().map((animation) => animation.finished.catch(() => {})))
        })
        const layout = await page.evaluate(() => {
          const root = document.querySelector('.sd-embedded-container, .sd-studio-page')
          const queueWidget = document.querySelector('.floating-queue-widget')
          const queueWidgetRect = queueWidget?.getBoundingClientRect()
          const visiblePrimaryButtons = [...document.querySelectorAll('.sd-embedded-container .btn-primary')]
            .map((button) => ({ button, rect: button.getBoundingClientRect() }))
            .filter(({ button, rect }) =>
              getComputedStyle(button).display !== 'none' &&
              rect.width > 0 &&
              rect.height > 0
            )
          const panelSelectors = [
            '.sd-chat-panel',
            '.sd-ledger-panel',
            '.sd-studio-launch-card',
            '.sd-upload-card',
            '.sd-review-column',
            '.sd-defence-sidebar',
            '.sd-studio-palette',
            '.sd-flow-stage',
            '.sd-studio-sidebar',
            '.sd-evaluation-content',
            '.sd-eval-highlights',
            '.sd-eval-rubric-panel',
            '.sd-rubric-list',
          ]
          return {
            documentHeight: document.documentElement.scrollHeight,
            documentWidth: document.documentElement.scrollWidth,
            viewportHeight: window.innerHeight,
            viewportWidth: window.innerWidth,
            queueWidget: queueWidgetRect
              ? {
                  top: queueWidgetRect.top,
                  bottom: queueWidgetRect.bottom,
                  left: queueWidgetRect.left,
                  right: queueWidgetRect.right,
                }
              : null,
            primaryButtons: visiblePrimaryButtons.map(({ button, rect }) => {
              return {
                label: button.textContent.trim(),
                top: rect.top,
                bottom: rect.bottom,
                left: rect.left,
                right: rect.right,
              }
            }),
            panels: panelSelectors.flatMap((panelSelector) =>
              [...document.querySelectorAll(panelSelector)].map((panel) => {
                const rect = panel.getBoundingClientRect()
                const rootRect = root.getBoundingClientRect()
                return {
                  selector: panelSelector,
                  top: rect.top,
                  bottom: rect.bottom,
                  left: rect.left,
                  right: rect.right,
                  rootTop: rootRect.top,
                  rootBottom: rootRect.bottom,
                  rootLeft: rootRect.left,
                  rootRight: rootRect.right,
                }
              })
            ),
          }
        })

        expect(layout.documentHeight).toBeLessThanOrEqual(layout.viewportHeight + 1)
        expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth + 1)
        if (layout.queueWidget) {
          expect(layout.queueWidget.bottom).toBeGreaterThan(layout.viewportHeight - 80)
          expect(layout.queueWidget.right).toBeGreaterThan(layout.viewportWidth - 80)
          for (const button of layout.primaryButtons) {
            const overlaps =
              layout.queueWidget.left < button.right &&
              layout.queueWidget.right > button.left &&
              layout.queueWidget.top < button.bottom &&
              layout.queueWidget.bottom > button.top
            expect(
              overlaps,
              `${stage} floating alert overlaps ${button.label}: ${JSON.stringify({ button, widget: layout.queueWidget })}`
            ).toBe(false)
          }
        }
        for (const panel of layout.panels) {
          expect(panel.top, `${stage} ${panel.selector} top`).toBeGreaterThanOrEqual(panel.rootTop - 1)
          expect(panel.bottom, `${stage} ${panel.selector} bottom`).toBeLessThanOrEqual(panel.rootBottom + 1)
          expect(panel.left, `${stage} ${panel.selector} left`).toBeGreaterThanOrEqual(panel.rootLeft - 1)
          expect(panel.right, `${stage} ${panel.selector} right`).toBeLessThanOrEqual(panel.rootRight + 1)
          if (layout.queueWidget && panel.selector === '.sd-rubric-list') {
            const overlaps =
              layout.queueWidget.left < panel.right &&
              layout.queueWidget.right > panel.left &&
              layout.queueWidget.top < panel.bottom &&
              layout.queueWidget.bottom > panel.top
            expect(overlaps, `${stage} floating alert overlaps evaluation rubric content`).toBe(false)
          }
        }
        await page.screenshot({
          path: `/tmp/system-design-${stage}-${theme.toLowerCase()}-${width}x${height}.png`,
        })
      }
    }
  }

  await captureLayout('requirements', '[data-testid="req-chat-input"]')
  await page.getByTestId('lock-requirements-btn').click()
  await expect(page.getByTestId('design-studio-page')).toBeVisible()
  await captureLayout('studio', '[data-testid="diagram-canvas-builder"]')
  await page.getByTestId('studio-back-btn').click()
  await expect(page.getByTestId('open-design-studio-btn')).toBeVisible()
  await captureLayout('diagram', '[data-testid="open-design-studio-btn"]')

  await page.locator('.diagram-file-input').setInputFiles({
    name: 'url-shortener-layout.png',
    mimeType: 'image/png',
    buffer: SAMPLE_PNG_BUFFER,
  })
  await page.getByRole('button', { name: 'Upload Diagram Revision' }).click()
  await page.getByRole('button', { name: /Analyze Architecture \(v1\)/ }).click()
  await expect(page.getByRole('heading', { name: 'Architecture Critique' })).toBeVisible()
  await captureLayout('review', '[data-testid="revise-in-studio-btn"]')

  await page.getByRole('button', { name: 'Proceed to Architecture Defence' }).click()
  await expect(page.getByTestId('defence-chat-input')).toBeVisible()
  await captureLayout('defence', '[data-testid="defence-chat-input"]')
  await page.getByTestId('defence-chat-input').fill('The read replica absorbs fallback traffic when the cache is unavailable.')
  await page.getByTestId('defence-send-btn').click()
  await page.getByTestId('evaluate-session-btn').click()
  await expect(page.locator('.eval-score-value')).toBeVisible()
  await captureLayout('evaluation', '.eval-score-value')
})
