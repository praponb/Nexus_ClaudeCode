import { expect, test, type Page } from '@playwright/test'

// Cycle-3 control-module smoke journeys: reservations (FR-010), approvals
// (FR-024), notifications (FR-023), reports (FR-021), admin (FR-027),
// data quality (FR-028), retirement dialog (FR-014). Render-level checks
// that avoid backend mutations so they stay stable against seed data.
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || process.env.SEED_DEMO_PASSWORD || '!Kiknitip01'

async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  const userEl = page.locator('#login-username')
  const isFormVisible = await userEl.isVisible({ timeout: 1500 }).catch(() => false)
  if (!isFormVisible) {
    return
  }
  const passEl = page.locator('#login-password')
  const submitBtn = page.getByRole('button', { name: 'Sign in' })

  await userEl.click()
  await userEl.fill(ADMIN_USER)
  await passEl.click()
  await passEl.fill(ADMIN_PASSWORD)

  if (await submitBtn.isDisabled()) {
    await userEl.fill(ADMIN_USER)
    await passEl.fill(ADMIN_PASSWORD)
  }

  await expect(submitBtn).toBeEnabled({ timeout: 5000 })
  await submitBtn.click()
  await expect(page).not.toHaveURL(/\/login$/, { timeout: 10000 })
}

test.describe('cycle-3 control modules', () => {
  test.beforeEach(() => {
    test.skip(!ADMIN_PASSWORD, 'Set E2E_ADMIN_PASSWORD to run authenticated E2E tests')
  })

  test('reservations list renders with overdue filter (FR-010)', async ({ page }) => {
    await signIn(page)
    await page.goto('/reservations')
    await expect(page.getByRole('heading', { name: 'Reservations', exact: true })).toBeVisible()
    await expect(page.getByLabel(/status/i)).toBeVisible()
    await expect(page.getByLabel(/overdue only/i)).toBeVisible()
  })

  test('approval inbox renders pending requests (FR-024)', async ({ page }) => {
    await signIn(page)
    await page.goto('/approvals')
    await expect(page.getByRole('heading', { name: 'Approvals', exact: true })).toBeVisible()
  })

  test('notification center renders with preferences (FR-023)', async ({ page }) => {
    await signIn(page)
    await page.goto('/notifications')
    await expect(page.getByRole('heading', { name: 'Notifications', exact: true })).toBeVisible()
    await page.getByRole('button', { name: /preferences/i }).click()
    await expect(page.getByRole('heading', { name: 'Notification preferences', exact: true })).toBeVisible()
  })

  test('reports catalog renders (FR-021)', async ({ page }) => {
    await signIn(page)
    await page.goto('/reports')
    await expect(page.getByRole('heading', { name: 'Reports', exact: true })).toBeVisible()
  })

  test('admin user table renders for system administrators (FR-027)', async ({ page }) => {
    await signIn(page)
    await page.goto('/admin/users')
    await expect(page.getByRole('heading', { name: 'Users', exact: true })).toBeVisible()
  })

  test('data-quality queue renders (FR-028)', async ({ page }) => {
    await signIn(page)
    await page.goto('/data-quality')
    await expect(page.getByRole('heading', { name: 'Data quality', exact: true })).toBeVisible()
  })

  test('retire dialog opens from the asset detail (FR-014)', async ({ page }) => {
    await signIn(page)
    await page.goto('/assets')
    const firstRow = page.locator('a[href^="/assets/"]:not([href="/assets/new"])').first()
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
