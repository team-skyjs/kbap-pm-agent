// 스트리밍 상태 6종: 상태별 표시가 하나씩만, 진행→완료 입력창 위치 고정, 위로 스크롤 중 자동 스크롤 없음,
// 동작 줄이기에서 대기 애니메이션 0s, live 모드에서 실제 fake 백엔드 경로
import { expect, test, type Page } from '@playwright/test'
import { LIVE, MARKDOWN_SAMPLE, PARTIAL_PREFIX, mockApi, type Scenario } from './fixtures.ts'
import { shot } from './helpers.ts'

const QUESTION = '스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘'
const MARKS = {
  sent: '.typing', progress: '.tools', done: '.card', partial: '.notice-block', error: '.error-row',
} as const

async function send(page: Page, scenario: Scenario, extra: Parameters<typeof mockApi>[1] = {}) {
  await mockApi(page, { scenario, ...extra })
  await page.goto('./#/conversations/8')
  const box = page.getByRole('textbox', { name: '질문 입력' })
  await box.fill(QUESTION)
  await box.press('Enter')
  return box
}

for (const scenario of ['sent', 'progress', 'done', 'partial', 'error'] as const) {
  test(`상태 표시: ${scenario}`, async ({ page }, info) => {
    test.skip(LIVE, '고정 응답 전용')
    await send(page, scenario)
    const last = page.locator('.msg.assistant').last()
    await expect(last.locator(MARKS[scenario]).first()).toBeVisible()
    // 진행 행은 완료·부분 완료·오류에도 남을 수 있어 대기 표시·안내·오류·카드만 배타 확인
    for (const [other, sel] of Object.entries(MARKS)) {
      if (other === scenario || sel === '.tools') continue
      await expect(last.locator(sel), `${scenario}에 ${other} 표시가 있음`).toHaveCount(0)
    }
    if (scenario === 'progress') await expect(last.locator('.tools summary')).toContainText('조회 중')
    if (scenario === 'partial') await expect(last.locator('.notice-block')).toContainText(PARTIAL_PREFIX)
    await shot(page, `us8-${scenario}`, info)
  })
}

test('상태 표시: 세션 만료', async ({ page }, info) => {
  test.skip(LIVE, '고정 응답 전용')
  const box = await send(page, 'expired')
  await expect(page.getByRole('alert').filter({ hasText: '로그인이 만료' })).toBeVisible()
  await expect(box).toHaveValue(QUESTION)
  await shot(page, 'us8-expired', info)
})

test('진행에서 완료로 바뀌어도 입력창 위치가 그대로', async ({ page }) => {
  test.skip(LIVE, '고정 응답 전용')
  const box = await send(page, 'progress', { completeAfterPoll: true })
  const last = page.locator('.msg.assistant').last()
  await expect(last.locator('.tools summary')).toContainText('조회 중')
  const before = await box.boundingBox()
  // 실행 중 3초 주기 재조회에서 완료로 전환
  await expect(last.locator('.tools summary')).toContainText('✓', { timeout: 10_000 })
  const after = await box.boundingBox()
  expect(before && after && Math.abs(after.y - before.y)).toBeLessThanOrEqual(2)
})

test('위로 스크롤한 상태에서는 새 메시지가 와도 위치 유지', async ({ page }) => {
  test.skip(LIVE, '고정 응답 전용')
  await mockApi(page, { scenario: 'done', assistantContent: MARKDOWN_SAMPLE })
  await page.goto('./#/conversations/7')
  await expect(page.locator('figure.md-chart canvas')).toHaveCount(2)
  const scroller = page.locator('.scroll')
  await scroller.evaluate((el) => { el.scrollTop = 0; el.dispatchEvent(new Event('scroll')) })
  const box = page.getByRole('textbox', { name: '질문 입력' })
  await box.fill(QUESTION)
  await box.press('Enter')
  await expect(page.locator('.msg.user').last()).toContainText(QUESTION)
  await expect(page.locator('.msg.assistant').last().locator('.card').first()).toBeAttached()
  expect(await scroller.evaluate((el) => el.scrollTop)).toBeLessThanOrEqual(4)
})

test('동작 줄이기에서 대기 애니메이션 없음', async ({ page }, info) => {
  test.skip(LIVE || !info.project.name.endsWith('reduced'), 'reduced 프로젝트 전용')
  await send(page, 'sent')
  const dot = page.locator('.msg.assistant').last().locator('.typing span').first()
  await expect(dot).toBeVisible()
  expect(await dot.evaluate((el) => getComputedStyle(el).animationDuration)).toBe('0s')
})

test('live: 실제 fake 백엔드로 진행에서 완료까지', async ({ page }) => {
  test.skip(!LIVE, 'CHECK_UI_LIVE=1에서만')
  const created = await page.request.post('http://localhost:8000/api/conversations', { data: {} })
  const { id } = await created.json()
  await page.goto(`./#/conversations/${id}`)
  const box = page.getByRole('textbox', { name: '질문 입력' })
  await box.fill(QUESTION)
  await box.press('Enter')
  const last = page.locator('.msg.assistant').last()
  await expect(last.locator('.tools')).toBeVisible({ timeout: 5_000 })
  await expect(last.locator('.card').first()).toBeVisible({ timeout: 30_000 })
})
