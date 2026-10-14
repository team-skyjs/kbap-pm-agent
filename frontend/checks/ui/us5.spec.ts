// 마크다운 렌더링: 요소, 링크 안전 속성, HTML 비해석, 코드 복사, 표 가로 스크롤
import { expect, test } from '@playwright/test'
import { MARKDOWN_SAMPLE, mockApi } from './fixtures.ts'
import { shot } from './helpers.ts'

test('마크다운 표본 답변', async ({ page, context }, info) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await mockApi(page, { assistantContent: MARKDOWN_SAMPLE })
  await page.goto('./#/conversations/7')
  const md = page.locator('.md').filter({ hasText: '제목 1' })
  await expect(md).toBeVisible()

  for (const tag of ['h1', 'h2', 'h3', 'h4', 'blockquote', 'hr', 'table thead']) await expect(md.locator(tag).first()).toBeAttached()
  const tasks = md.locator('li.task-list-item input[type=checkbox]')
  await expect(tasks).toHaveCount(2)
  await expect(tasks.first()).toBeDisabled()

  const link = md.locator('a[href="https://example.com/docs"]')
  await expect(link).toHaveAttribute('target', '_blank')
  await expect(link).toHaveAttribute('rel', /noopener/)
  await expect(link).toHaveAttribute('rel', /noreferrer/)

  await expect(md).toContainText('<script>window.__xss = 1</script>')
  await expect(md.locator('script')).toHaveCount(0)
  expect(await page.evaluate(() => 'xss' in window || '__xss' in window)).toBe(false)

  const code = md.locator('.md-code').filter({ has: page.locator('code.language-ts') })
  await code.locator('.md-code-copy').click()
  await expect(code.locator('.md-code-copy')).toHaveText('복사됨')
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('track(EVENTS.scan_retry_tap, { fail_reason })')

  const scroller = md.locator('.md-table-scroll')
  expect(['auto', 'scroll']).toContain(await scroller.evaluate((el) => getComputedStyle(el).overflowX))
  if (info.project.name.startsWith('375')) {
    expect(await scroller.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true)
  }
  await shot(page, 'us5', info)
})
