import { expect, test, type Page } from '@playwright/test'

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

test.describe('asset register journeys (J-1 slice, J-6)', () => {
  test.beforeEach(() => {
    test.skip(!ADMIN_PASSWORD, 'Set E2E_ADMIN_PASSWORD to run authenticated E2E tests')
  })

  test('register a new asset and open its detail page', async ({ page }) => {
    await signIn(page)
    await page.goto('/assets/new')
    const name = `E2E Laptop ${Date.now()}`
    await page.getByLabel(/asset name/i).fill(name)
    await page.getByLabel(/category/i).selectOption({ index: 1 })
    await page.getByLabel(/status/i).selectOption({ label: 'Draft' })
    await page.getByRole('button', { name: /save asset/i }).click()
    // Duplicate pre-check may require an explicit confirmation.
    const saveAnyway = page.getByRole('button', { name: /save asset anyway/i })
    if (await saveAnyway.isVisible().catch(() => false)) {
      await saveAnyway.click()
    }
    await expect(page).toHaveURL(/\/assets\/[0-9a-f-]{36}$/)
    await expect(page.getByRole('heading', { name })).toBeVisible()
  })

  test('search by exact tag and open the asset', async ({ page }) => {
    await signIn(page)
    await page.goto('/assets')
    const firstTag = page.locator('a[href^="/assets/"]:not([href="/assets/new"])').first()
    await expect(firstTag).toBeVisible()
    const tag = (await firstTag.textContent())?.trim() ?? ''
    test.skip(!tag, 'No seeded assets available')

    await page.goto('/')
    const search = page.getByRole('combobox', { name: /search assets/i })
    await search.focus()
    await search.fill(tag)
    await page.waitForTimeout(500)
    const option = page.getByRole('option').first()
    await expect(option).toBeVisible({ timeout: 5000 })
    await expect(option).toContainText(tag)
    await option.click()
    await expect(page).toHaveURL(/\/assets\/[0-9a-f-]{36}$/)
  })

  test('edit with a stale version shows a conflict prompt', async ({ page, request }) => {
    await signIn(page)
    await page.goto('/assets')
    const firstRow = page.locator('tbody tr td a').first()
    await expect(firstRow).toBeVisible()
    const href = await firstRow.getAttribute('href')
    test.skip(!href, 'No seeded assets available')

    await page.goto(`${href}/edit`)
    await expect(page.getByRole('heading', { name: 'Edit asset' })).toBeVisible()

    // Simulate a concurrent update through the API using the session cookies.
    const cookies = await page.context().cookies()
    const session = cookies.find((c) => c.name === 'sessionid')
    const csrf = cookies.find((c) => c.name === 'csrftoken')
    test.skip(!session, 'No session cookie present')
    const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000/api/v1'
    const uuid = href!.split('/').pop()!
    const detail = await request.get(`${apiBase}/assets/${uuid}`)
    const asset = await detail.json()
    await request.patch(`${apiBase}/assets/${uuid}`, {
      data: { name: asset.name, category: asset.category?.uuid, description: 'Concurrent edit', version: asset.version },
      headers: {
        'If-Match': String(asset.version),
        'X-CSRFToken': csrf?.value ?? '',
        Cookie: `sessionid=${session!.value}; csrftoken=${csrf?.value ?? ''}`,
      },
    })

    await page.getByLabel(/description/i).fill('My stale edit')
    await page.getByRole('button', { name: /save changes/i }).click()
    await expect(page.getByText(/changed by someone else/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /reload latest data/i })).toBeVisible()
  })
})
