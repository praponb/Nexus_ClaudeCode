import { expect, test } from '@playwright/test'

// Requires the compose stack with seeded dev users. Credentials are dev-only
// and documented in the backend README; override via env for other envs.
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || ''

test.describe('sign-in (J-6)', () => {
  test('shows the sign-in form with labeled fields', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
    await expect(page.getByLabel(/username/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('rejects invalid credentials with a generic message', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/username/i).fill('definitely-not-a-user')
    await page.getByLabel(/password/i).fill('wrong-password')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    // Must not reveal whether the username or the password was wrong.
    await expect(page.getByRole('alert')).not.toContainText(/password is incorrect/i)
  })

  test('signs in and lands on the dashboard', async ({ page }) => {
    test.skip(!ADMIN_PASSWORD, 'Set E2E_ADMIN_PASSWORD to run authenticated E2E tests')
    await page.goto('/login')
    await page.getByLabel(/username/i).fill(ADMIN_USER)
    await page.getByLabel(/password/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('redirects unauthenticated users to sign-in with a return URL', async ({ page }) => {
    await page.goto('/assets')
    await expect(page).toHaveURL(/\/login\?next=%2Fassets/)
  })
})
