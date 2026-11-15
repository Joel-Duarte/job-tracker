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

  // Auto-extract into ledger & lock requirements to unlock Stage 2
  await page.getByRole('button', { name: 'Auto-Extract from Chat' }).click()
  await expect(page.locator('textarea').nth(1)).toHaveValue(/Core API endpoint to create\/ingest primary entities/)
  await page.getByRole('button', { name: 'Lock Requirements & Proceed to Diagram' }).click()

  // Stage 2: Upload diagram, verify Stage 2 unlocked while Stage 3-5 still locked
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
