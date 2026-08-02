import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Automated axe checks supplement (not replace) manual keyboard/screen-reader
// passes on critical journeys (layout.md §22).
test.describe('accessibility smoke', () => {
  test('sign-in page has no detectable WCAG A/AA violations', async ({ page }) => {
    await page.goto('/login')
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze()
    expect(results.violations).toEqual([])
  })

  test('sign-in page is keyboard operable', async ({ page }) => {
    await page.goto('/login')
    await page.keyboard.press('Tab')
    // Focus must land on an interactive element with a visible indicator path.
    const focused = await page.evaluate(() => document.activeElement?.tagName)
    expect(['INPUT', 'BUTTON', 'A']).toContain(focused)
  })
})
