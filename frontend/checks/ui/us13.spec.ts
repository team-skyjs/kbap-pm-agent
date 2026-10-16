// 대화 내보내기: 버튼 활성 조건과 메뉴 키보드, Markdown 내려받기(이름·내용·기록), PDF 인쇄 호출과 기록,
// 인쇄 매체에서 흐름 풀기·숨김·머리글·밝은 배경, 인쇄 직전·직후 제안 카드 절과 차트 폭
import { readFileSync } from 'node:fs'
import { expect, test, type Page } from '@playwright/test'
import { MARKDOWN_SAMPLE, mockApi } from './fixtures.ts'
import { expectNoSeriousA11y, shot } from './helpers.ts'

const PRINT_WIDTH = 680
const exportBtn = (page: Page) => page.getByRole('button', { name: '내보내기' })
const item = (page: Page, name: string) => page.getByRole('menuitem', { name })

// 기록 POST 본문의 format
function captureExports(page: Page) {
  const formats: string[] = []
  page.on('request', (r) => {
    if (r.method() !== 'POST' || !r.url().endsWith('/exports')) return
    const body: unknown = r.postDataJSON()
    if (typeof body === 'object' && body !== null && 'format' in body) formats.push(String(Object.getOwnPropertyDescriptor(body, 'format')?.value))
  })
  return formats
}

// 대화상자를 열지 않도록 window.print를 호출 횟수 기록으로 바꿈
async function stubPrint(page: Page) {
  await page.addInitScript(() => { window.print = () => { document.body.dataset.printed = String(Number(document.body.dataset.printed ?? 0) + 1) } })
}
const printed = (page: Page) => page.evaluate(() => Number(document.body.dataset.printed ?? 0))

test('버튼 활성 조건: 빈 대화·실행 중 비활성, 메시지 있으면 활성', async ({ page }) => {
  await mockApi(page, { scenario: 'hang' })
  await page.goto('./#/conversations/7')
  await expect(exportBtn(page)).toBeEnabled()
  await page.goto('./#/conversations/8')
  await expect(exportBtn(page)).toBeDisabled()
  await page.getByRole('textbox', { name: '질문 입력' }).fill('질문')
  await page.getByRole('textbox', { name: '질문 입력' }).press('Enter')
  await expect(exportBtn(page)).toBeDisabled()
})

test('메뉴 키보드: Enter로 열고 첫 항목 포커스, Tab 이동, ESC로 닫고 버튼 포커스', async ({ page }, info) => {
  await mockApi(page)
  await page.goto('./#/conversations/7')
  await exportBtn(page).focus()
  await page.keyboard.press('Enter')
  await expect(exportBtn(page)).toHaveAttribute('aria-expanded', 'true')
  await expect(exportBtn(page)).toHaveAttribute('aria-haspopup', 'menu')
  await expect(item(page, 'PDF로 인쇄')).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(item(page, 'Markdown 파일')).toBeFocused()
  await expectNoSeriousA11y(page)
  await shot(page, 'us13-menu', info)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('menu')).toHaveCount(0)
  await expect(exportBtn(page)).toHaveAttribute('aria-expanded', 'false')
  await expect(exportBtn(page)).toBeFocused()
})

for (const exportFail of [false, true]) {
  test(`Markdown 내려받기${exportFail ? '(기록 500이어도)' : ''}: 파일 이름·내용, 기록 markdown`, async ({ page }) => {
    const formats = captureExports(page)
    await mockApi(page, { exportFail })
    await page.goto('./#/conversations/7')
    await exportBtn(page).click()
    const download = page.waitForEvent('download')
    await item(page, 'Markdown 파일').click()
    const d = await download
    expect(d.suggestedFilename()).toMatch(/^스캔 퍼널 이탈 지점 개선안-\d{8}\.md$/)
    const text = readFileSync(await d.path(), 'utf8')
    expect(text).toMatch(/^# 스캔 퍼널 이탈 지점 개선안\n/)
    expect(text).toContain('### 제안 1. OCR 실패 화면에 재시도·직접 입력 동선 추가 — 미정')
    expect(text).toContain('### 제안 2. 스캔 실패 후 재시도 퍼널 측정 설계 — 미정')
    for (const h of ['#### 근거', '#### 제안', '#### 실행 단계', '#### 측정 방법']) expect(text).toContain(`\n${h}\n`)
    await expect.poll(() => formats).toEqual(['markdown'])
  })

  test(`PDF로 인쇄${exportFail ? '(기록 500이어도)' : ''}: print 호출, 기록 pdf`, async ({ page }) => {
    const formats = captureExports(page)
    await stubPrint(page)
    await mockApi(page, { exportFail })
    await page.goto('./#/conversations/7')
    await exportBtn(page).click()
    await item(page, 'PDF로 인쇄').click()
    await expect.poll(() => printed(page)).toBe(1)
    await expect.poll(() => formats).toEqual(['pdf'])
    await expect(exportBtn(page)).toBeFocused()
  })
}

test('Markdown 본문에 chart 블록 원문이 그대로 남음', async ({ page }) => {
  await mockApi(page, { assistantContent: MARKDOWN_SAMPLE })
  await page.goto('./#/conversations/7')
  await exportBtn(page).click()
  const download = page.waitForEvent('download')
  await item(page, 'Markdown 파일').click()
  const text = readFileSync(await (await download).path(), 'utf8')
  expect(text).toContain(MARKDOWN_SAMPLE)
})

test('인쇄 매체: 스크롤 영역이 문서 흐름으로 풀리고 조작 요소는 숨김, 머리글 표시, 배경 흰색', async ({ page }, info) => {
  await mockApi(page, { assistantContent: MARKDOWN_SAMPLE })
  await page.goto('./#/conversations/7')
  await expect(page.locator('figure.md-chart canvas')).toHaveCount(2)
  await page.emulateMedia({ media: 'print' })

  const display = (sel: string) => page.locator(sel).first().evaluate((el) => getComputedStyle(el).display)
  for (const sel of ['#sidebar', '.topbar', '.chat-input-wrap', '.decision', 'details.tools', '.md-code-copy']) {
    expect(await display(sel), sel).toBe('none')
  }
  const app = await page.locator('.app').evaluate((el) => ({ overflow: getComputedStyle(el).overflow, h: el.getBoundingClientRect().height, vh: innerHeight }))
  expect(app.overflow).toBe('visible')
  expect(app.h).toBeGreaterThan(app.vh)
  const scroll = await page.locator('.scroll').evaluate((el) => ({ overflowY: getComputedStyle(el).overflowY, sh: el.scrollHeight, ch: el.clientHeight }))
  expect(scroll.overflowY).toBe('visible')
  expect(scroll.sh).toBeLessThanOrEqual(scroll.ch + 1)

  await expect(page.locator('.print-header')).toBeVisible()
  await expect(page.locator('.print-header')).toContainText('스캔 퍼널 이탈 지점 개선안')
  await expect(page.locator('.print-header')).not.toContainText(/https?:\/\/|localhost/)
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(255, 255, 255)')
  await shot(page, 'us13-print', info)
})

test('인쇄 직전: 제안 카드 절이 모두 열리고 차트가 인쇄 폭, 직후: 원래대로', async ({ page }) => {
  await mockApi(page, { assistantContent: MARKDOWN_SAMPLE })
  await page.goto('./#/conversations/7')
  const canvas = page.locator('figure.md-chart canvas').first()
  await expect(canvas).toBeVisible()
  const openStates = () => page.locator('details.card-section').evaluateAll((els) => els.map((el) => el instanceof HTMLDetailsElement && el.open))
  const before = await openStates()
  expect(before.filter(Boolean).length).toBeLessThan(before.length)
  const screenWidth = await canvas.evaluate((c) => c.getBoundingClientRect().width)

  await page.evaluate(() => dispatchEvent(new Event('beforeprint')))
  expect((await openStates()).every(Boolean)).toBe(true)
  const printWidth = await canvas.evaluate((c) => c.getBoundingClientRect().width)
  expect(printWidth).toBeGreaterThan(0)
  expect(printWidth).toBeLessThanOrEqual(PRINT_WIDTH)
  await expect(page.locator('[data-print-date]')).toHaveText(/^\d{4}-\d{2}-\d{2}$/)

  await page.evaluate(() => dispatchEvent(new Event('afterprint')))
  expect(await openStates()).toEqual(before)
  await expect.poll(() => canvas.evaluate((c) => Math.round(c.getBoundingClientRect().width))).toBe(Math.round(screenWidth))
})
