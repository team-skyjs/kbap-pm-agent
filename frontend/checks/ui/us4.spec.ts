// 메시지 표현: 긴 URL·긴 코드에도 가로 넘침 없음, 사용자 메시지만 배경, AI 메시지 아바타 없음
import { expect, test } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { expectNoHorizontalScroll, shot } from './helpers.ts'

const LONG_URL = `https://example.com/${'very-long-path-segment-'.repeat(12)}end`
const LONG_CODE = `track(EVENTS.scan_complete, { ${'property_name_that_is_long: value, '.repeat(10)}})`
const CONTENT = `긴 주소: ${LONG_URL}\n\n\`\`\`ts\n${LONG_CODE}\n\`\`\`\n\n보통 문단입니다.`

test('메시지 구분과 넘침', async ({ page }, info) => {
  await mockApi(page, { assistantContent: CONTENT })
  await page.goto('./#/conversations/7')
  await expect(page.locator('.msg.assistant .md').first()).toBeVisible()
  await expectNoHorizontalScroll(page)

  // 스레드 폭을 넘는 요소가 없는지(코드 블록은 내부 스크롤)
  const overflow = await page.locator('.thread').first().evaluate((t) => t.scrollWidth - t.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)

  const bg = (sel: string) => page.locator(sel).first().evaluate((el) => getComputedStyle(el).backgroundColor)
  expect(await bg('.msg.user')).not.toBe('rgba(0, 0, 0, 0)')
  expect(await bg('.msg.assistant')).toBe('rgba(0, 0, 0, 0)')
  await expect(page.locator('.msg.assistant img, .msg.assistant .avatar')).toHaveCount(0)
  await shot(page, 'us4', info)
})
