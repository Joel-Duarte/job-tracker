import { test, expect } from '@playwright/test'

const pages = [
  ['/', '.kanban-container'],
  ['/companies', '.companies-view-container'],
  ['/assessments', '.assessments-page'],
  ['/tasks', '.tasks-page'],
  ['/queue', '.queue-page-layout'],
  ['/analytics', '.analytics-content'],
  ['/staging', '.staging-workspace-container'],
  ['/chat', '.chat-main'],
  ['/settings', '.settings-content-area'],
  ['/diagnostics', '.page-title'],
]

for (const [path, selector] of pages) {
  test(`${path} renders its primary view in demo mode`, async ({ page }) => {
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => {
      if (message.type() === 'warning' && message.text().includes('[Vue warn]')) {
        errors.push(message.text())
      }
    })
    await page.goto(path)
    await expect(page.getByText('DEMO MODE')).toBeVisible()
    await expect(page.locator(`main ${selector}`).first()).toBeVisible()
    expect(errors).toEqual([])
  })
}

test('profile route redirects to profile settings', async ({ page }) => {
  await page.goto('/profile')
  await expect(page).toHaveURL(/\/settings\?tab=profile$/)
  await expect(page.getByRole('button', { name: 'My Profile / CV' })).toHaveClass(/active/)
})

test('analytics tabs reveal the selected dashboard', async ({ page }) => {
  await page.goto('/analytics')
  await page.getByRole('button', { name: 'Pipeline Funnel Performance' }).click()
  await expect(page.getByRole('heading', { name: /Funnel Progression/, level: 2 })).toBeVisible()
  await page.getByRole('button', { name: 'Role Alignment & CV Tuning' }).click()
  await expect(page.getByRole('heading', { name: /Role Alignment & Vocabulary/ })).toBeVisible()
})

test('settings tabs switch and profile route is deep linkable', async ({ page }) => {
  await page.goto('/settings')
  await page.getByRole('button', { name: /AI Providers/ }).click()
  await expect(page.locator('.tab-content')).toBeVisible()
  await page.getByRole('button', { name: 'Preferences' }).click()
  await expect(page.getByRole('heading', { name: 'System & Workspace Preferences' })).toBeVisible()
  await page.goto('/settings?tab=profile')
  await expect(page.getByRole('button', { name: 'My Profile / CV' })).toHaveClass(/active/)
})

test('queue filters change the selected task group', async ({ page }) => {
  await page.goto('/queue')
  await page.locator('.tab-bar').getByRole('button', { name: /Failed/ }).click()
  await expect(page.locator('.tab-bar').getByRole('button', { name: /Failed/ })).toHaveClass(/active/)
  await page.locator('.type-filter-group').getByRole('button', { name: 'Job Leads' }).click()
  await expect(page.locator('.type-filter-group').getByRole('button', { name: 'Job Leads' })).toHaveClass(/active/)
})

test('task metrics and search change the visible task list', async ({ page }) => {
  await page.goto('/tasks')
  await page.locator('.metric-card').filter({ hasText: 'All Tasks' }).click()
  await expect(page.locator('.metric-card').filter({ hasText: 'All Tasks' })).toHaveClass(/active/)
  await page.getByPlaceholder('Search task title, company, or role...').fill('unlikely task phrase')
  await expect(page.locator('.task-card')).toHaveCount(0)
})

test('assessment filters and archive tab respond', async ({ page }) => {
  await page.goto('/assessments')
  await page.locator('.eval-filter-toolbar').getByRole('button', { name: '80%+' }).click()
  await expect(page.locator('.eval-filter-toolbar').getByRole('button', { name: '80%+' })).toHaveClass(/active/)
  await page.getByRole('button', { name: /Passed \/ Not Applied/ }).click()
  await expect(page.getByRole('button', { name: /Passed \/ Not Applied/ })).toHaveClass(/active/)
})

test('staging queue can switch between pending and resolved', async ({ page }) => {
  await page.goto('/staging')
  await page.getByRole('button', { name: 'Resolved' }).click()
  await expect(page.getByRole('button', { name: 'Resolved' })).toHaveClass(/active/)
  await page.getByRole('button', { name: /Pending/ }).click()
  await expect(page.getByRole('button', { name: /Pending/ })).toHaveClass(/active/)
})

test('agent workspace switches to interview setup', async ({ page }) => {
  await page.goto('/chat')
  await page.getByRole('button', { name: 'Live Mock Interview Simulator' }).click()
  await expect(page.getByRole('heading', { name: 'Interactive Live Mock Interview' })).toBeVisible()
})

test('diagnostics switches reports', async ({ page }) => {
  await page.goto('/diagnostics')
  await page.getByRole('button', { name: 'Detailed Costs' }).click()
  await expect(page.getByRole('button', { name: 'Detailed Costs' })).toHaveClass(/btn-primary/)
  await page.getByRole('button', { name: 'Quality & Grounding' }).click()
  await expect(page.getByRole('button', { name: 'Quality & Grounding' })).toHaveClass(/btn-primary/)
})

test('theme switch persists across navigation', async ({ page }) => {
  await page.goto('/')
  await page.locator('.theme-toggle').click()
  await page.getByRole('button', { name: 'Midnight' }).click()
  await expect(page.locator('html')).not.toHaveClass(/daylight/)
  await page.goto('/companies')
  await expect(page.locator('html')).not.toHaveClass(/daylight/)
})
