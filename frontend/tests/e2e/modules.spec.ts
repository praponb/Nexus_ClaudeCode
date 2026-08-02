import { expect, test, type Page } from '@playwright/test'

// Cycle-2 module smoke journeys: import wizard (J-7), export center (FR-019),
// stocktakes (FR-022), reservation dialog (FR-010). Render-level checks that
// avoid backend mutations so they stay stable against seed data.
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || ''

async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByLabel(/username/i).fill(ADMIN_USER)
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/$/)
}

test.describe('cycle-2 modules', () => {
  test.beforeEach(() => {
    test.skip(!ADMIN_PASSWORD, 'Set E2E_ADMIN_PASSWORD to run authenticated E2E tests')
  })

  test('import wizard offers the CSV template and upload step (J-7)', async ({ page }) => {
    await signIn(page)
    await page.goto('/imports')
    await expect(page.getByRole('heading', { name: 'Import assets' })).toBeVisible()
    await expect(page.getByRole('link', { name: /download csv template/i })).toBeVisible()
    await expect(page.getByLabel(/csv file/i)).toBeVisible()
  })

  test('export center renders with a create action (FR-019)', async ({ page }) => {
    await signIn(page)
    await page.goto('/exports')
    await expect(page.getByRole('heading', { name: 'Export center' })).toBeVisible()
    await expect(page.getByRole('button', { name: /create csv export/i })).toBeVisible()
  })

  test('stocktake list renders with create action for managers (FR-022)', async ({ page }) => {
    await signIn(page)
    await page.goto('/stocktakes')
    await expect(page.getByRole('heading', { name: 'Stocktakes' })).toBeVisible()
    await expect(page.getByRole('button', { name: /new stocktake/i })).toBeVisible()
  })

  test('reservation dialog opens from the asset detail and closes with Escape (FR-010)', async ({ page }) => {
    await signIn(page)
    await page.goto('/assets')
    const firstRow = page.locator('tbody tr td a').first()
    await expect(firstRow).toBeVisible()
    await firstRow.click()

    await page.getByRole('button', { name: /^reserve$/i }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('heading', { name: /reserve asset/i })).toBeVisible()
    await expect(dialog.getByLabel(/reserved from/i)).toBeVisible()
    await expect(dialog.getByLabel(/reserved until/i)).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  })
})
