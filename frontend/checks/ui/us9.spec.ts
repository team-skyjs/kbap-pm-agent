// 제안 카드: 기본은 제안만 펼침, 근거 라벨 3종, 코드 근거 위치, 신규 단계 라벨, 채택 후 새로고침 유지
import { expect, test } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { shot } from './helpers.ts'

test('카드 구역과 근거 표시', async ({ page }, info) => {
  await mockApi(page)
  await page.goto('./#/conversations/7')
  const cards = page.locator('article.card')
  await expect(cards).toHaveCount(2)
  for (const card of await cards.all()) {
    const sections = card.locator('details.card-section')
    await expect(sections).toHaveCount(4)
    const open = await sections.evaluateAll((els) => els.map((el) => (el instanceof HTMLDetailsElement ? el.open : false)))
    expect(open).toEqual([false, true, false, false])
  }

  const funnel = cards.nth(1)
  await funnel.locator('summary', { hasText: '근거' }).click()
  for (const label of ['지표', '코드', '택사노미']) await expect(funnel.locator('.tag', { hasText: label }).first()).toBeVisible()
  await expect(funnel).toContainText('src/app/scan.tsx:405')
  await expect(funnel).toContainText('onScanFailed')
  await funnel.locator('summary', { hasText: '측정 방법' }).click()
  await expect(funnel.locator('.tag', { hasText: '신규' })).toBeVisible()
  await expect(funnel).toContainText('src/app/scan.tsx · handleRetry · 398')
  await shot(page, 'us9-open', info)
})

test('채택하면 상태 라벨이 바뀌고 새로고침 뒤에도 유지', async ({ page }, info) => {
  await mockApi(page)
  await page.goto('./#/conversations/7')
  const first = page.locator('article.card').first()
  await expect(first.locator('.status')).toHaveText('미결정')
  await first.getByRole('button', { name: '채택' }).click()
  await expect(first.locator('.status')).toHaveText('채택')
  await page.reload()
  await expect(page.locator('article.card').first().locator('.status')).toHaveText('채택')
  await shot(page, 'us9-adopted', info)
})
