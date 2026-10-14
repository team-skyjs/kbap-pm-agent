// 입력창: Shift+Enter 줄바꿈, Enter 전송, 6줄 넘으면 높이 고정·내부 스크롤, 실행 중 비활성·안내,
// 오류 뒤 다시 시도로 입력 복원, 세션 만료 뒤 입력 유지, 한글 조합 중 Enter 미전송
import { expect, test, type Page } from '@playwright/test'
import { mockApi, type Scenario } from './fixtures.ts'
import { shot } from './helpers.ts'

const QUESTION = '스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘'

async function open(page: Page, scenario: Scenario) {
  await mockApi(page, { scenario })
  await page.goto('./#/conversations/8')
  const box = page.getByRole('textbox', { name: '질문 입력' })
  await expect(box).toBeEnabled()
  return box
}

const posts = (page: Page) => {
  const sent: string[] = []
  page.on('request', (r) => { if (r.method() === 'POST' && r.url().includes('/messages')) sent.push(r.url()) })
  return sent
}

test('Shift+Enter 줄바꿈, Enter 전송', async ({ page }) => {
  const box = await open(page, 'done')
  const sent = posts(page)
  await box.fill('첫 줄')
  await box.press('Shift+Enter')
  await box.pressSequentially('둘째 줄')
  await expect(box).toHaveValue('첫 줄\n둘째 줄')
  expect(sent).toEqual([])
  await box.press('Enter')
  await expect(page.locator('.msg.user').last()).toContainText('둘째 줄')
  expect(sent).toHaveLength(1)
})

test('6줄을 넘으면 높이가 고정되고 내부 스크롤', async ({ page }, info) => {
  const box = await open(page, 'done')
  await box.fill(Array.from({ length: 6 }, (_, i) => `줄 ${i + 1}`).join('\n'))
  const six = await box.evaluate((el) => el.clientHeight)
  await box.fill(Array.from({ length: 12 }, (_, i) => `줄 ${i + 1}`).join('\n'))
  const twelve = await box.evaluate((el) => ({ h: el.clientHeight, scroll: el.scrollHeight }))
  expect(twelve.h).toBeLessThanOrEqual(six + 2)
  expect(twelve.scroll).toBeGreaterThan(twelve.h)
  await shot(page, 'us7-multiline', info)
})

test('실행 중에는 비활성과 안내 문구', async ({ page }, info) => {
  const box = await open(page, 'hang')
  await box.fill(QUESTION)
  await box.press('Enter')
  await expect(box).toBeDisabled()
  await expect(page.getByText('에이전트 실행 중에는 보낼 수 없습니다')).toBeVisible()
  await shot(page, 'us7-running', info)
})

test('오류 뒤 다시 시도로 질문 복원', async ({ page }) => {
  const box = await open(page, 'error')
  await box.fill(QUESTION)
  await box.press('Enter')
  await page.getByRole('button', { name: '다시 시도' }).click()
  await expect(box).toHaveValue(QUESTION)
  await expect(box).toBeFocused()
})

test('세션 만료 뒤 입력값 유지', async ({ page }) => {
  const box = await open(page, 'expired')
  await box.fill(QUESTION)
  await box.press('Enter')
  await expect(page.getByRole('alert').filter({ hasText: '로그인이 만료' })).toBeVisible()
  await expect(box).toHaveValue(QUESTION)
})

test('한글 조합 중 Enter는 전송하지 않음', async ({ page }) => {
  const box = await open(page, 'done')
  const sent = posts(page)
  await box.fill('조합 중')
  // 조합 중 Enter 흉내: isComposing이 켜진 keydown
  await box.evaluate((el) => {
    el.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }))
    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', isComposing: true, bubbles: true, cancelable: true }))
  })
  await expect(box).toHaveValue('조합 중')
  expect(sent).toEqual([])
})
