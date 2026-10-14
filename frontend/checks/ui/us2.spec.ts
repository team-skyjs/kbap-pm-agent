// 앱 셸: 넓은 화면 사이드 패널 접기 유지, 좁은 화면 Drawer(열기·ESC·배경 닫기·스크롤 잠금·포커스 가두기), 가로 넘침, 본문 최대 폭
import { expect, test, type Page } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { expectNoHorizontalScroll, shot } from './helpers.ts'

const isMobile = (project: string) => !project.startsWith('1280')
const focusInSidebar = (page: Page) => page.evaluate(() => !!document.getElementById('sidebar')?.contains(document.activeElement))

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.goto('./#/conversations/7')
  await expect(page.locator('.md').first()).toBeVisible()
})

test('넓은 화면: 접기 상태가 새로고침 뒤에도 유지되고 본문 폭은 최대 폭 이하', async ({ page }, info) => {
  test.skip(isMobile(info.project.name), '넓은 화면 전용')
  const maxPx = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--content-max')))
  expect(maxPx).toBeGreaterThan(0)
  const threadWidth = await page.locator('.thread').first().evaluate((el) => el.getBoundingClientRect().width)
  expect(threadWidth).toBeLessThanOrEqual(maxPx)

  await page.getByRole('button', { name: '사이드 패널 접기' }).click()
  await expect(page.locator('#sidebar')).toBeHidden()
  await page.reload()
  await expect(page.getByRole('button', { name: '사이드 패널 펼치기' })).toBeVisible()
  await expect(page.locator('#sidebar')).toBeHidden()
  await shot(page, 'us2-collapsed', info)

  await page.getByRole('button', { name: '사이드 패널 펼치기' }).click()
  await expect(page.locator('#sidebar')).toBeVisible()
})

test('좁은 화면: Drawer 열기·포커스 가두기·스크롤 잠금·ESC·배경 닫기', async ({ page }, info) => {
  test.skip(!isMobile(info.project.name), '좁은 화면 전용')
  const menu = page.getByRole('button', { name: '메뉴 열기' })
  const dialog = page.getByRole('dialog', { name: '사이드 패널' })

  await menu.click()
  await expect(dialog).toBeVisible()
  expect(await page.evaluate(() => getComputedStyle(document.body).overflow)).toBe('hidden')
  await expect.poll(() => focusInSidebar(page)).toBe(true)

  // 포커스 순환: 요소 수보다 많이 눌러도 Drawer 밖으로 나가지 않음 (양방향)
  const count = await dialog.locator('button, a[href], [tabindex="0"]').count()
  for (let i = 0; i < count + 2; i++) {
    await page.keyboard.press('Tab')
    expect(await focusInSidebar(page), `Tab ${i + 1}회 뒤 포커스가 Drawer 밖`).toBe(true)
  }
  for (let i = 0; i < count + 2; i++) {
    await page.keyboard.press('Shift+Tab')
    expect(await focusInSidebar(page), `Shift+Tab ${i + 1}회 뒤 포커스가 Drawer 밖`).toBe(true)
  }
  await shot(page, 'us2-drawer', info)

  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(menu).toBeFocused()
  expect(await page.evaluate(() => getComputedStyle(document.body).overflow)).not.toBe('hidden')

  // 배경 클릭: Drawer 오른쪽 바깥 지점
  await menu.click()
  await expect(dialog).toBeVisible()
  const vp = page.viewportSize()
  if (vp) await page.mouse.click(vp.width - 4, Math.round(vp.height / 2))
  await expect(dialog).toBeHidden()

  await expectNoHorizontalScroll(page)
  await shot(page, 'us2', info)
})
