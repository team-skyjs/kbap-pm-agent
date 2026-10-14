// 뼈대 확인: 고정 응답으로 앱이 뜨고 헬스 호출이 왕복하며 콘솔 오류가 없음
import { expect, test } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { shot } from './helpers.ts'

test('앱이 뜨고 헬스가 표시된다', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  await mockApi(page)
  const health = page.waitForResponse((r) => r.url().includes('/api/health') && r.ok())
  await page.goto('./')
  await health
  await expect(page.locator('#root')).not.toBeEmpty()
  await expect(page.getByText(/\bok\b/).first()).toBeVisible()
  expect(errors).toEqual([])
  await shot(page, 'smoke', info)
})
