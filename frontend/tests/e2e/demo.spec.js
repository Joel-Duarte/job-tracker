import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

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
