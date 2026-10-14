// 대화 목록: 최근순, 긴 제목 말줄임, 현재 항목 aria-current, 제안·채택 수, 키보드 선택, 설정 링크 하단
import { expect, test } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { shot } from './helpers.ts'

const LONG = '아주 긴 대화 제목이 사이드 패널 폭을 넘어서 한 줄 말줄임으로 잘려야 하는 경우를 확인하기 위한 제목 '.repeat(2).trim()
const item = (id: number, title: string | null, updatedAt: string, proposalCount: number, adoptedCount: number) => ({
  id, title, createdAt: '2026-10-14T00:00:00.000Z', updatedAt, messageCount: 2, proposalCount, adoptedCount,
})
// 일부러 순서를 섞어 보내고 화면이 최근순으로 보이는지 확인
const LIST = [
  item(6, null, '2026-10-13T00:00:00.000Z', 0, 0),
  item(7, '스캔 퍼널 이탈 지점 개선안', '2026-10-15T09:14:41.022Z', 2, 1),
  item(5, LONG, '2026-10-14T05:40:00.000Z', 1, 0),
]

test('대화 목록 표시와 키보드 선택', async ({ page }, info) => {
  await mockApi(page, { list: LIST })
  await page.goto('./#/conversations/7')
  if (!info.project.name.startsWith('1280')) await page.getByRole('button', { name: '메뉴 열기' }).click()
  const nav = page.getByRole('navigation', { name: '대화 목록' })
  const links = nav.getByRole('link')
  await expect(links).toHaveCount(3)
  await expect(links.nth(0)).toContainText('스캔 퍼널 이탈 지점 개선안')
  await expect(links.nth(1)).toContainText(LONG.slice(0, 10))
  await expect(links.nth(2)).toContainText('새 대화')

  await expect(links.nth(0)).toHaveAttribute('aria-current', 'page')
  await expect(links.nth(1)).not.toHaveAttribute('aria-current', 'page')
  await expect(links.nth(0)).toContainText('제안 2 · 채택 1')

  const title = links.nth(1).locator('.list-title')
  expect(await title.evaluate((el) => getComputedStyle(el).textOverflow)).toBe('ellipsis')
  expect(await title.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true)

  // 설정 링크는 패널 하단
  const panel = await page.locator('#sidebar').boundingBox()
  const settings = await page.locator('#sidebar').getByRole('link', { name: '설정' }).boundingBox()
  expect(panel && settings && panel.y + panel.height - (settings.y + settings.height)).toBeLessThan(64)
  await shot(page, 'us3', info)

  // 키보드만으로 다른 대화 선택
  await links.nth(0).focus()
  await page.keyboard.press('Tab')
  await expect(links.nth(1)).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/#\/conversations\/5$/)
})
