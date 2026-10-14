// 질문 다듬기: 버튼 활성 조건, 진행 중 입력 잠금, 비교 카드, 네 가지 선택(전송 본문·입력창 값·선택 기록),
// 실패 안내와 원문 유지, 선택 기록 실패에도 전송, 키보드 조작과 포커스 이동, axe
import { expect, test, type Page } from '@playwright/test'
import { REFINE, mockApi } from './fixtures.ts'
import { expectNoSeriousA11y, shot } from './helpers.ts'

const ORIGINAL = '스캔 이탈 왜 많아?'
const REFINED = String(REFINE.refined)

const box = (page: Page) => page.getByRole('textbox', { name: '질문 입력' })
const refineBtn = (page: Page) => page.getByRole('button', { name: '질문 다듬기', exact: true })
const card = (page: Page) => page.getByRole('region', { name: '질문 다듬기 결과' })

// 요청 본문 기록: 메시지 전송 content와 선택 기록 choice
function capture(page: Page) {
  const sent: string[] = []
  const choices: string[] = []
  page.on('request', (r) => {
    if (r.method() !== 'POST') return
    const body: unknown = r.postDataJSON()
    const field = (k: string) => (typeof body === 'object' && body !== null && k in body ? String(Object.getOwnPropertyDescriptor(body, k)?.value) : '')
    if (r.url().endsWith('/messages')) sent.push(field('content'))
    if (r.url().endsWith('/choice')) choices.push(field('choice'))
  })
  return { sent, choices }
}

async function openCard(page: Page, opts: Parameters<typeof mockApi>[1] = {}) {
  await mockApi(page, { scenario: 'done', refine: 'ok', ...opts })
  await page.goto('./#/conversations/8')
  await box(page).fill(ORIGINAL)
  await refineBtn(page).click()
  await expect(card(page)).toBeVisible()
}

test('버튼 활성 조건: 빈 입력·실행 중 비활성', async ({ page }) => {
  await mockApi(page, { scenario: 'hang', refine: 'ok' })
  await page.goto('./#/conversations/8')
  await expect(refineBtn(page)).toBeDisabled()
  await box(page).fill(ORIGINAL)
  await expect(refineBtn(page)).toBeEnabled()
  await box(page).press('Enter')
  await expect(refineBtn(page)).toBeDisabled()
})

test('다듬는 동안 입력창 잠금, 끝나면 비교 카드', async ({ page }, info) => {
  await mockApi(page, { refine: 'ok', refineDelayMs: 1500 })
  await page.goto('./#/conversations/8')
  await box(page).fill(ORIGINAL)
  await refineBtn(page).click()
  await expect(box(page)).toBeDisabled()
  await expect(refineBtn(page)).toBeDisabled()
  await expect(card(page)).toBeVisible()
  await expect(card(page)).toContainText(ORIGINAL)
  await expect(card(page)).toContainText(REFINED)
  await expect(card(page)).toContainText(String(REFINE.summary))
  await expect(box(page)).toBeEnabled()
  await expectNoSeriousA11y(page)
  await shot(page, 'us12-card', info)
})

test('개선안으로 보내기: 개선안 전송, 선택 refined', async ({ page }) => {
  const rec = capture(page)
  await openCard(page)
  await card(page).getByRole('button', { name: '개선안으로 보내기' }).click()
  await expect(card(page)).toHaveCount(0)
  await expect(page.locator('.msg.user').last()).toContainText(REFINED)
  await expect.poll(() => rec.choices).toEqual(['refined'])
  expect(rec.sent).toEqual([REFINED])
})

test('원문으로 보내기: 원문 전송, 선택 original', async ({ page }) => {
  const rec = capture(page)
  await openCard(page)
  await card(page).getByRole('button', { name: '원문으로 보내기' }).click()
  await expect(page.locator('.msg.user').last()).toContainText(ORIGINAL)
  await expect.poll(() => rec.choices).toEqual(['original'])
  expect(rec.sent).toEqual([ORIGINAL])
})

test('입력창에 넣기 후 편집해 전송: 넣을 때는 기록 없음, 전송 때 refined', async ({ page }) => {
  const rec = capture(page)
  await openCard(page)
  await card(page).getByRole('button', { name: '입력창에 넣기' }).click()
  await expect(card(page)).toHaveCount(0)
  await expect(box(page)).toHaveValue(REFINED)
  await box(page).press('End')
  await box(page).pressSequentially(' 주 단위로')
  expect(rec.choices).toEqual([])
  expect(rec.sent).toEqual([])
  await box(page).press('Enter')
  await expect(page.locator('.msg.user').last()).toContainText('주 단위로')
  await expect.poll(() => rec.choices).toEqual(['refined'])
  expect(rec.sent).toEqual([`${REFINED} 주 단위로`])
})

test('입력창에 넣기 후 비우면 cancelled', async ({ page }) => {
  const rec = capture(page)
  await openCard(page)
  await card(page).getByRole('button', { name: '입력창에 넣기' }).click()
  await expect(box(page)).toHaveValue(REFINED)
  await box(page).fill('')
  await expect.poll(() => rec.choices).toEqual(['cancelled'])
  expect(rec.sent).toEqual([])
})

test('입력창에 넣기 후 다른 대화로 옮기면 cancelled', async ({ page }) => {
  const rec = capture(page)
  await openCard(page)
  await card(page).getByRole('button', { name: '입력창에 넣기' }).click()
  await expect(box(page)).toHaveValue(REFINED)
  await page.goto('./#/conversations/7')
  await expect(page.locator('article.card').first()).toBeVisible()
  await expect.poll(() => rec.choices).toEqual(['cancelled'])
  expect(rec.sent).toEqual([])
})

test('닫기와 ESC: 카드만 닫히고 원문 유지, 선택 cancelled', async ({ page }) => {
  const rec = capture(page)
  await openCard(page)
  await card(page).getByRole('button', { name: '닫기' }).click()
  await expect(card(page)).toHaveCount(0)
  await expect(box(page)).toHaveValue(ORIGINAL)

  await refineBtn(page).click()
  await expect(card(page)).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(card(page)).toHaveCount(0)
  await expect(box(page)).toHaveValue(ORIGINAL)
  await expect.poll(() => rec.choices).toEqual(['cancelled', 'cancelled'])
  expect(rec.sent).toEqual([])
})

test('다듬기 실패: 카드 없이 안내, 원문 유지', async ({ page }, info) => {
  await mockApi(page, { refine: 'fail' })
  await page.goto('./#/conversations/8')
  await box(page).fill(ORIGINAL)
  await refineBtn(page).click()
  await expect(page.getByText('질문 다듬기 모델 응답 오류입니다').or(page.getByText('외부 서비스')).first()).toBeVisible()
  await expect(card(page)).toHaveCount(0)
  await expect(box(page)).toHaveValue(ORIGINAL)
  await expect(box(page)).toBeEnabled()
  await shot(page, 'us12-error', info)
})

test('선택 기록이 실패해도 전송은 진행', async ({ page }) => {
  const rec = capture(page)
  await openCard(page, { choiceFail: true })
  await card(page).getByRole('button', { name: '개선안으로 보내기' }).click()
  await expect(page.locator('.msg.user').last()).toContainText(REFINED)
  await expect(page.locator('.msg.assistant').last().locator('.card').first()).toBeVisible()
  expect(rec.sent).toEqual([REFINED])
})

test('키보드만으로: 버튼 → 카드 포커스 → ESC 후 입력창 포커스', async ({ page }) => {
  await mockApi(page, { refine: 'ok' })
  await page.goto('./#/conversations/8')
  await box(page).focus()
  await page.keyboard.type(ORIGINAL)
  await refineBtn(page).focus()
  await page.keyboard.press('Enter')
  await expect(card(page)).toBeVisible()
  await expect(card(page).getByRole('button', { name: '개선안으로 보내기' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(card(page)).toHaveCount(0)
  await expect(box(page)).toBeFocused()

  // 다시 열어 Tab으로 다른 선택까지 도달
  await refineBtn(page).focus()
  await page.keyboard.press('Enter')
  await expect(card(page)).toBeVisible()
  for (let i = 0; i < 6; i++) {
    if (await card(page).getByRole('button', { name: '입력창에 넣기' }).evaluate((el) => el === document.activeElement)) break
    await page.keyboard.press('Shift+Tab')
  }
  await page.keyboard.press('Enter')
  await expect(box(page)).toHaveValue(REFINED)
  await expect(box(page)).toBeFocused()
})
