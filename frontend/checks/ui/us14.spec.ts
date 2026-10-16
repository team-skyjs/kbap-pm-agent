// Amplitude 서버 키: 설정 화면은 상태 라벨 두 가지만(연결 버튼 없음), 전송 사전 점검 거절 시 서버 안내와
// "Amplitude 없이 진행"(같은 내용을 skipAmplitude로 다시 보냄, 입력값 보존, 키보드 조작)
import { expect, test, type Page } from '@playwright/test'
import { AMPLITUDE_UNAVAILABLE_MESSAGE, mockApi } from './fixtures.ts'
import { expectNoSeriousA11y, shot } from './helpers.ts'

const QUESTION = '최근 7일 스캔 퍼널 이탈 원인 알려줘'

function captureSends(page: Page) {
  const bodies: Record<string, unknown>[] = []
  page.on('request', (r) => {
    if (r.method() !== 'POST' || !r.url().endsWith('/messages')) return
    const body: unknown = r.postDataJSON()
    if (typeof body === 'object' && body !== null) bodies.push(Object.fromEntries(Object.entries(body)))
  })
  return bodies
}

test('설정: 서버 키가 있으면 "서버 키로 연결됨", 연결 버튼 없음', async ({ page }, info) => {
  await mockApi(page, { amplitudeStatus: 'configured' })
  await page.goto('./#/settings')
  await expect(page.locator('.status', { hasText: '서버 키로 연결됨' })).toBeVisible()
  await expect(page.getByRole('button', { name: /^(다시 )?연결$/ })).toHaveCount(0)
  await expect(page.getByText('AMPLITUDE_API_KEY')).toHaveCount(0)
  await expectNoSeriousA11y(page)
  await shot(page, 'us14-settings-configured', info)
})

test('설정: 서버 키가 없으면 "키 없음"과 서버 환경 변수 안내', async ({ page }, info) => {
  await mockApi(page, { amplitudeStatus: 'missing' })
  await page.goto('./#/settings')
  await expect(page.locator('.status', { hasText: '키 없음' })).toBeVisible()
  await expect(page.getByText('AMPLITUDE_API_KEY')).toBeVisible()
  await expect(page.getByText('AMPLITUDE_SECRET_KEY')).toBeVisible()
  await expect(page.getByRole('button', { name: /^(다시 )?연결$/ })).toHaveCount(0)
  await shot(page, 'us14-settings-missing', info)
})

test('전송 거절: 서버 안내와 입력값 보존, "Amplitude 없이 진행"이 skipAmplitude로 같은 내용을 다시 보냄', async ({ page }, info) => {
  const bodies = captureSends(page)
  await mockApi(page, { amplitudeUnavailable: true })
  await page.goto('./#/conversations/8')
  const box = page.getByRole('textbox', { name: '질문 입력' })
  await box.fill(QUESTION)
  await box.press('Enter')

  await expect(page.locator('#chat-hint')).toHaveText(AMPLITUDE_UNAVAILABLE_MESSAGE)
  await expect(box).toHaveValue(QUESTION)
  await expect(page.locator('.msg.user')).toHaveCount(0)
  const skip = page.getByRole('button', { name: 'Amplitude 없이 진행' })
  await expect(skip).toBeVisible()
  await expectNoSeriousA11y(page)
  await shot(page, 'us14-refused', info)

  // 키보드로 조작
  await skip.focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('.msg.user').last()).toContainText(QUESTION)
  await expect(page.locator('.msg.assistant').last().locator('.card').first()).toBeVisible()
  await expect(skip).toHaveCount(0)
  expect(bodies).toEqual([{ content: QUESTION }, { content: QUESTION, skipAmplitude: true }])
})
