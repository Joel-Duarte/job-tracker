import { test, expect } from '@playwright/test'

for (const theme of ['midnight', 'daylight']) {
  test(`time zone override persists and validates input in ${theme}`, async ({ page }) => {
    await page.goto('/settings?tab=preferences')
    await page.evaluate((mode) => document.documentElement.classList.toggle('daylight', mode === 'daylight'), theme)
    const input = page.getByLabel('Display time zone')
    await expect(input).toBeVisible()
    await input.fill('America/New_York')
    await page.getByRole('button', { name: 'Save time zone', exact: true }).click()
    await expect(page.getByText('Manual override', { exact: true })).toBeVisible()
    await page.reload()
    await expect(input).toHaveValue('America/New_York')
    await input.fill('Invalid/Zone')
    await page.getByRole('button', { name: 'Save time zone', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('valid IANA time zone')
    await page.getByRole('button', { name: 'Use browser time zone', exact: true }).click()
    await expect(page.getByText('Detected from browser', { exact: true })).toBeVisible()
    await expect(input).not.toHaveValue('Invalid/Zone')
  })
}

test('date-only email deadlines remain date-only on tasks', async ({ page }) => {
  await page.goto('/tasks')
  await expect.poll(() => page.evaluate(() => Boolean(localStorage.getItem('jt_demo_db_v1')))).toBe(true)
  await page.evaluate(() => {
    const db = JSON.parse(localStorage.getItem('jt_demo_db_v1'))
    const task = db.action_items[0]
    task.title = 'Submit verified assessment'
    task.due_date = null
    task.temporal_metadata = { version: 2, deadline: { date: '2026-11-03', precision: 'date' } }
    localStorage.setItem('jt_demo_db_v1', JSON.stringify(db))
  })
  await page.reload()
  await expect(page.getByText('Due: 2026-11-03 (date only)', { exact: true })).toBeVisible()
})

for (const theme of ['midnight', 'daylight']) {
  test(`email timeline distinguishes proposals, invites and uncertain times in ${theme}`, async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.application-card').first()).toBeVisible()
    await page.evaluate(() => {
      const db = JSON.parse(localStorage.getItem('jt_demo_db_v1'))
      db.system_settings.DISPLAY_TIMEZONE = 'Europe/Lisbon'
      db.system_settings.TIMEZONE_SOURCE = 'manual'
      const app = db.applications.find(a => a.company_name === 'Datadog')
      app.temporal_version = 2
      app.scheduled_interview_at = null
      app.events = [{
        id: 'email-proposal', email_subject: 'Interview availability', email_event_type: 'INTERVIEW_REQUESTED',
        email_received_at: '2026-10-23T12:00:00Z', source_channel: 'EMAIL',
        raw_payload: { temporal: { version: 2, meeting_proposal: 'Tuesday at 14:00', issues: ['AMBIGUOUS_TIMEZONE'] } },
      }, {
        id: 'email-invite', email_subject: 'Calendar invitation', email_event_type: 'INTERVIEW_SCHEDULED',
        email_received_at: '2026-10-22T12:00:00Z', source_channel: 'EMAIL',
        raw_payload: { temporal: { version: 2 }, scheduled_at: '2026-10-24T14:00:00Z', schedule_state: 'confirmed', calendar: { start: '2026-10-24T10:00:00-04:00', timezone: 'America/New_York' } },
      }]
      app.latest_event = app.events[0]
      localStorage.setItem('jt_demo_db_v1', JSON.stringify(db))
    })
    await page.reload()
    await page.evaluate(mode => document.documentElement.classList.toggle('daylight', mode === 'daylight'), theme)
    const card = page.locator('.application-card').filter({ hasText: 'Datadog' })
    await expect(card.locator('.date-green, .date-yellow, .date-red')).toHaveCount(0)
    await card.locator('.card-position').click()
    await expect(page.getByText('Proposed meeting: Tuesday at 14:00', { exact: true })).toBeVisible()
    await expect(page.getByText('Time requires review: AMBIGUOUS_TIMEZONE', { exact: true })).toBeVisible()
    await expect(page.getByText(/Confirmed by calendar invite:/)).toContainText('15:00')
    await expect(page.getByText(/Original calendar time:/)).toContainText('America/New_York')
  })
}

test('uncertain thread boundaries explain why staging needs review', async ({ page, isMobile }) => {
  await page.goto('/staging')
  await expect(page.locator('.queue-item-card').first()).toBeVisible()
  await page.evaluate(() => {
    const db = JSON.parse(localStorage.getItem('jt_demo_db_v1'))
    db.staging_items.forEach(item => { item.extracted_data.temporal = { version: 2, issues: ['INTERLEAVED_REPLY_REVIEW'] } })
    localStorage.setItem('jt_demo_db_v1', JSON.stringify(db))
  })
  await page.reload()
  if (isMobile) await page.locator('.queue-item-card').first().click()
  await expect(page.getByText('Intake requires review: INTERLEAVED_REPLY_REVIEW', { exact: true })).toBeVisible()
})
