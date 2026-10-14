// 설정 화면: 상태 라벨 텍스트, 폼 포커스 윤곽선, 접근 토큰 저장(기존 localStorage 키), 375 가로 넘침 없음
import { expect, test } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { expectNoHorizontalScroll, shot } from './helpers.ts'

test('설정 화면 표시와 토큰 저장', async ({ page }, info) => {
  await mockApi(page)
  await page.goto('./#/settings')
  await expect(page.locator('.status', { hasText: '연결됨' })).toBeVisible()
  await expect(page.getByText('fake (시연)').or(page.getByText('real'))).toBeVisible()

  const token = page.getByRole('textbox', { name: '접근 토큰' }).or(page.getByLabel('접근 토큰'))
  await token.focus()
  const ring = await token.evaluate((el) => {
    const s = getComputedStyle(el)
    return { outline: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0, shadow: s.boxShadow !== 'none' }
  })
  expect(ring.outline || ring.shadow).toBe(true)

  await token.fill('secret-token')
  await page.getByRole('button', { name: '저장', exact: true }).click()
  expect(await page.evaluate(() => localStorage.getItem('kbap-pm-agent.accessToken'))).toBe('secret-token')

  await expectNoHorizontalScroll(page)
  await shot(page, 'us10', info)
})
