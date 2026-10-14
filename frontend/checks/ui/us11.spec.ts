// 접근성: 키보드만으로 새 대화 → 입력 → Enter → 제안 채택, 주요 화면 axe 심각·중대 위반 0
import { expect, test, type Locator, type Page } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { expectNoSeriousA11y } from './helpers.ts'

const isMobile = (project: string) => !project.startsWith('1280')

// 대상에 포커스가 갈 때까지 Tab (최대 횟수 초과 시 실패)
async function tabTo(page: Page, target: Locator, max = 80) {
  for (let i = 0; i < max; i++) {
    if (await target.evaluate((el) => el === document.activeElement)) return
    await page.keyboard.press('Tab')
  }
  throw new Error(`Tab ${max}회 안에 도달하지 못함`)
}

test('키보드만으로 질문하고 제안 채택', async ({ page }, info) => {
  await mockApi(page, { scenario: 'done' })
  await page.goto('./')
  if (isMobile(info.project.name)) {
    await tabTo(page, page.getByRole('button', { name: '메뉴 열기' }))
    await page.keyboard.press('Enter')
    // Drawer가 다음 프레임에 첫 요소로 포커스를 옮기므로 그 뒤부터 Tab
    await expect.poll(() => page.evaluate(() => !!document.getElementById('sidebar')?.contains(document.activeElement))).toBe(true)
  }
  await tabTo(page, page.getByRole('button', { name: '새 대화' }))
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/#\/conversations\/8$/)

  const box = page.getByRole('textbox', { name: '질문 입력' })
  await tabTo(page, box)
  await page.keyboard.type('스캔 퍼널 개선안 알려줘')
  await page.keyboard.press('Enter')
  const card = page.locator('.msg.assistant').last().locator('article.card').first()
  await expect(card).toBeVisible()

  await tabTo(page, card.getByRole('button', { name: '채택' }))
  await page.keyboard.press('Enter')
  await expect(card.locator('.status')).toHaveText('채택')
})

test('axe: 채팅·카드 펼침·설정·Drawer', async ({ page }, info) => {
  await mockApi(page)
  await page.goto('./#/conversations/7')
  await expect(page.locator('article.card').first()).toBeVisible()
  await expectNoSeriousA11y(page)

  await page.locator('details.card-section').evaluateAll((els) => els.forEach((el) => el instanceof HTMLDetailsElement && (el.open = true)))
  await expectNoSeriousA11y(page)

  if (isMobile(info.project.name)) {
    await page.getByRole('button', { name: '메뉴 열기' }).click()
    await expect(page.getByRole('dialog', { name: '사이드 패널' })).toBeVisible()
    await expectNoSeriousA11y(page)
    await page.keyboard.press('Escape')
  }

  await page.goto('./#/settings')
  await expect(page.locator('.status', { hasText: '연결됨' })).toBeVisible()
  await expectNoSeriousA11y(page)
})
