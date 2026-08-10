import { expect, test, type Page } from '@playwright/test'

// Cycle-2 workflow journeys (J-1 assignment completion, scan manual entry).
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

  await userEl.fill(ADMIN_USER)
  await passEl.fill(ADMIN_PASSWORD)
  await expect(submitBtn).toBeEnabled()
  await submitBtn.click()
  await expect(page).not.toHaveURL(/\/login$/, { timeout: 10000 })
}

test.describe('lifecycle workflows', () => {
  test.beforeEach(() => {
    test.skip(!ADMIN_PASSWORD, 'Set E2E_ADMIN_PASSWORD to run authenticated E2E tests')
  })

  test('assign an asset to a department (J-1 completion)', async ({ page }) => {
    await signIn(page)
    await page.goto('/assets')
    const firstRow = page.locator('a[href^="/assets/"]:not([href="/assets/new"])').first()
    await expect(firstRow).toBeVisible()
    const href = await firstRow.getAttribute('href')
    test.skip(!href, 'No seeded assets available')

    await page.goto(`${href}/assign`)
    await expect(page.getByRole('heading', { name: 'Assign asset' })).toBeVisible()
    await page.getByRole('radio', { name: 'A department' }).check()
    await page.getByLabel(/department/i).selectOption({ index: 1 })
    await page.getByRole('button', { name: /assign asset/i }).click()
    await expect(page).toHaveURL(new RegExp(`${href}$`))
    await expect(page.getByText(/assigned/i).first()).toBeVisible()
  })

  test('scan page manual entry handles unknown codes non-destructively', async ({ page }) => {
    await signIn(page)
    await page.goto('/scan')
    await page.getByLabel(/enter asset tag manually/i).fill('NOPE-404-NOT-REAL')
    await page.getByRole('button', { name: /look up/i }).click()
    await expect(page.getByText(/unknown code/i)).toBeVisible()
    await expect(page.getByText(/nothing was changed/i)).toBeVisible()
  })

  test('asset detail exposes workflow actions', async ({ page }) => {
    await signIn(page)
    await page.goto('/assets')
    const firstRow = page.locator('a[href^="/assets/"]:not([href="/assets/new"])').first()
    await expect(firstRow).toBeVisible()
    await firstRow.click()
    await expect(page.getByRole('link', { name: /^assign$/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /^transfer$/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /^return$/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /report exception/i })).toBeVisible()
  })
})
