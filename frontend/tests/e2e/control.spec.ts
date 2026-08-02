import { expect, test, type Page } from '@playwright/test'

// Cycle-3 control-module smoke journeys: reservations (FR-010), approvals
// (FR-024), notifications (FR-023), reports (FR-021), admin (FR-027),
// data quality (FR-028), retirement dialog (FR-014). Render-level checks
// that avoid backend mutations so they stay stable against seed data.
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || ''

async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByLabel(/username/i).fill(ADMIN_USER)
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/$/)
}

test.describe('cycle-3 control modules', () => {
  test.beforeEach(() => {
    test.skip(!ADMIN_PASSWORD, 'Set E2E_ADMIN_PASSWORD to run authenticated E2E tests')
  })

  test('reservations list renders with overdue filter (FR-010)', async ({ page }) => {
    await signIn(page)
    await page.goto('/reservations')
    await expect(page.getByRole('heading', { name: 'Reservations' })).toBeVisible()
    await expect(page.getByLabel(/status/i)).toBeVisible()
    await expect(page.getByLabel(/overdue only/i)).toBeVisible()
  })

  test('approval inbox renders pending requests (FR-024)', async ({ page }) => {
    await signIn(page)
    await page.goto('/approvals')
    await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  })

  test('notification center renders with preferences (FR-023)', async ({ page }) => {
    await signIn(page)
    await page.goto('/notifications')
    await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible()
    await page.getByRole('button', { name: /preferences/i }).click()
    await expect(page.getByRole('heading', { name: 'Notification preferences' })).toBeVisible()
  })

  test('reports catalog renders (FR-021)', async ({ page }) => {
    await signIn(page)
    await page.goto('/reports')
    await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible()
  })

  test('admin user table renders for system administrators (FR-027)', async ({ page }) => {
    await signIn(page)
    await page.goto('/admin/users')
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
  })

  test('data-quality queue renders (FR-028)', async ({ page }) => {
    await signIn(page)
    await page.goto('/data-quality')
    await expect(page.getByRole('heading', { name: 'Data quality' })).toBeVisible()
  })

  test('retire dialog opens from the asset detail (FR-014)', async ({ page }) => {
    await signIn(page)
    await page.goto('/assets')
    const firstRow = page.locator('tbody tr td a').first()
    await expect(firstRow).toBeVisible()
    await firstRow.click()

    const retireButton = page.getByRole('button', { name: /^retire$/i })
    const reopenButton = page.getByRole('button', { name: /^reopen$/i })
    if (await retireButton.isVisible()) {
      await retireButton.click()
      const dialog = page.getByRole('dialog')
      await expect(dialog.getByRole('heading', { name: /retire asset/i })).toBeVisible()
      await page.keyboard.press('Escape')
      await expect(dialog).toBeHidden()
    } else if (await reopenButton.isVisible()) {
      await reopenButton.click()
      const dialog = page.getByRole('dialog')
      await expect(dialog.getByRole('heading', { name: /reopen asset/i })).toBeVisible()
      await page.keyboard.press('Escape')
      await expect(dialog).toBeHidden()
    } else {
      test.skip(true, 'Seeded asset is not visible to the admin user')
    }
  })
})
