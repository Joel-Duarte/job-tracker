import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('LinkedIn advisory only appears for LinkedIn hostnames', async ({ page, isMobile }) => {
  await page.goto('/')
  if (isMobile) {
    await page.getByRole('button', { name: 'Toggle navigation menu' }).click()
    await page.getByRole('button', { name: 'Job Intake' }).last().click()
  } else {
    await page.getByRole('button', { name: 'Job Intake' }).first().click()
  }
  const urlInput = page.getByPlaceholder(/https:\/\/jobs\.lever\.co/)
  await urlInput.fill('https://linkedin.com.attacker.example/jobs/123')
  await expect(page.getByText('LinkedIn Anti-Bot Protection')).toBeHidden()
  await urlInput.fill('https://www.linkedin.com/jobs/view/123')
  await expect(page.getByText('LinkedIn Anti-Bot Protection')).toBeVisible()
})

test('demo pipeline search and archive work', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('DEMO MODE')).toBeVisible()
  await expect(page.getByRole('button', { name: /Active Pipeline/ })).toBeVisible()

  const search = page.getByPlaceholder('Search company, role, or keywords...')
  await search.fill('Stripe')
  await expect(page.locator('.kanban-container')).toContainText('Stripe')
  await search.fill('an-unmatched-company')
  await expect(page.locator('.kanban-container')).not.toContainText('Stripe')

  await page.getByRole('button', { name: /Archived \/ Closed/ }).click()
  await expect(page.locator('.archive-view-container')).toBeVisible()
})

test('demo company can be added and found', async ({ page }) => {
  await page.goto('/companies')
  await expect(page.getByRole('heading', { name: 'Companies Directory' })).toBeVisible()
  await page.getByRole('button', { name: 'Add Company' }).click()
  const modal = page.locator('.add-company-modal')
  await expect(modal).toBeVisible()
  await modal.getByPlaceholder('e.g. Stripe, Acme Corp, Linear').fill('QA Fixture Ltd')
  await modal.getByRole('button', { name: 'Create Only' }).click()
  await expect(modal).toBeHidden()
  await page.getByPlaceholder('Search companies...').fill('QA Fixture Ltd')
  await expect(page.locator('.company-card')).toHaveCount(1)
  await expect(page.locator('.company-card')).toContainText('QA Fixture Ltd')
})

test('company card opens its detail drawer', async ({ page }) => {
  await page.goto('/companies')
  await page.locator('.company-card').filter({ hasText: 'Stripe' }).first().click()
  await expect(page.getByRole('dialog', { name: 'Company Details' })).toBeVisible()
  await expect(page.getByRole('dialog', { name: 'Company Details' })).toContainText('Stripe')
})

test('company form exposes accessible fields', async ({ page }) => {
  await page.goto('/companies')
  await page.getByRole('button', { name: 'Add Company' }).click()
  const modal = page.locator('.add-company-modal')
  await expect(modal).toBeVisible()
  const results = await new AxeBuilder({ page }).include('.add-company-modal').analyze()
  expect(results.violations.map(({ id, nodes }) => ({
    id,
    targets: nodes.flatMap((node) => node.target),
  }))).toEqual([])
})

test('company form is accessible in midnight mode', async ({ page }) => {
  await page.goto('/companies')
  await page.locator('.theme-toggle').click()
  await page.getByRole('button', { name: 'Midnight' }).click()
  await page.locator('.theme-toggle').click()
  await page.getByRole('button', { name: 'Add Company' }).click()
  const results = await new AxeBuilder({ page }).include('.add-company-modal').analyze()
  expect(results.violations.map((violation) => violation.id)).toEqual([])
})

test('company form keeps its desktop layout', async ({ page, isMobile }) => {
  test.skip(isMobile, 'Desktop visual baseline')
  await page.goto('/companies')
  await page.getByRole('button', { name: 'Add Company' }).click()
  const modal = page.locator('.add-company-modal')
  await expect(modal).toBeVisible()
  await page.addStyleTag({ content: '.add-company-modal, .add-company-modal * { font-family: "DejaVu Sans", sans-serif !important; }' })
  await expect(modal).toHaveCSS('width', '520px')
  await expect(modal).toHaveScreenshot('add-company-form.png', { animations: 'disabled', maxDiffPixelRatio: 0.02 })
})

test('mobile navigation opens and reaches companies', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile navigation is only present at small viewports')
  await page.goto('/')
  await page.getByRole('button', { name: 'Toggle navigation menu' }).click()
  await page.getByRole('link', { name: 'Companies' }).last().click()
  await expect(page).toHaveURL(/\/companies$/)
  await expect(page.getByRole('heading', { name: 'Companies Directory' })).toBeVisible()
})

test('demo agent describes current tools and reads the saved pipeline', async ({ page }) => {
  await page.goto('/chat')
  const input = page.getByPlaceholder('Ask the agent to search applications, check interview dates, or change statuses...')
  await input.fill('What tools can you use?')
  await input.press('Enter')
  await expect(page.locator('.msg-assistant').last()).toContainText('Application Documents')
  await expect(page.locator('.msg-assistant').last()).toContainText('Company Intelligence')
  await input.fill('Summarize my active pipeline')
  await input.press('Enter')
  await expect(page.locator('.msg-assistant').last()).toContainText('Stripe')
  await expect(page.locator('.msg-assistant').last()).toContainText('Linear')
  await expect(page.locator('.msg-assistant').last()).not.toContainText('scheduled in 2 days')
  await input.fill('Show my cover letter for Stripe')
  await input.press('Enter')
  await expect(page.locator('.msg-assistant').last()).toContainText('Dear Hiring Team at Stripe')
  await input.fill('Show my deadlines')
  await input.press('Enter')
  await expect(page.locator('.msg-assistant').last()).toContainText('Pending action items')
  await input.fill('Tell me about Stripe')
  await input.press('Enter')
  await expect(page.locator('.msg-assistant').last()).toContainText('Company Intelligence')
  await input.fill('Show my candidate profile')
  await input.press('Enter')
  await expect(page.locator('.msg-assistant').last()).toContainText('John Souls')
  await input.fill('Show my mock interview history')
  await input.press('Enter')
  await expect(page.locator('.msg-assistant').last()).toContainText('score 93')
})

test('demo grounding shows verdicts and rewrites and purge clears audits', async ({ page }) => {
  await page.goto('/diagnostics')
  await page.getByRole('button', { name: 'Quality & Grounding' }).click()
  await expect(page.locator('.quality-view-body')).toContainText('3 / 4 passed')
  await expect(page.locator('.quality-view-body')).toContainText('75%')
  await expect(page.locator('.quality-view-body')).toContainText('AWS certification')
  await expect(page.locator('.quality-view-body')).toContainText('Grounded')
  await expect(page.locator('.quality-view-body')).toContainText('Flagged')
  await expect(page.locator('.quality-metric-card').filter({ hasText: 'Auto-Rewrites Done' })).toContainText('1')
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Purge Logs' }).click()
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('jt_demo_db_v1')).quality_audits.length)).toBe(0)
  await page.getByRole('button', { name: 'Refresh quality metrics' }).click()
  await expect(page.getByText('No Quality Audits Yet')).toBeVisible()
})

test('existing demo sessions receive audits without losing saved applications', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.kanban-container')).toContainText('Stripe')
  await page.evaluate(() => {
    const db = JSON.parse(localStorage.getItem('jt_demo_db_v1'))
    delete db.quality_audits
    db.applications.find(app => app.company_name === 'Stripe').position = 'My saved demo role'
    localStorage.setItem('jt_demo_db_v1', JSON.stringify(db))
  })
  await page.goto('/diagnostics')
  await page.getByRole('button', { name: 'Quality & Grounding' }).click()
  await expect(page.locator('.quality-view-body')).toContainText('3 / 4 passed')
  await page.goto('/')
  await expect(page.locator('.kanban-container')).toContainText('My saved demo role')
})
