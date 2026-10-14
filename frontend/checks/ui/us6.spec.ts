// 차트 블록: 선·막대 렌더, 형식 오류는 원문 코드 블록, 대체 표, 다크에서 그려짐, 차트 없는 화면은 차트 청크 미요청
import { expect, test } from '@playwright/test'
import { MARKDOWN_SAMPLE, mockApi } from './fixtures.ts'
import { shot } from './helpers.ts'

const CHART_REQUEST = /ChartBlock|chart\.js|chart_js/

test('차트 블록 렌더링', async ({ page }, info) => {
  await mockApi(page, { assistantContent: MARKDOWN_SAMPLE })
  await page.goto('./#/conversations/7')
  const charts = page.locator('figure.md-chart')
  await expect(charts.locator('canvas')).toHaveCount(2)
  await expect(page.locator('code.language-chart')).toHaveCount(1)
  await expect(page.locator('code.language-chart')).toContainText('"pie"')

  await expect(charts.nth(0).locator('[role=img]')).toHaveAttribute('aria-label', '최근 7일 스캔 시작 사용자 수')
  await expect(charts.nth(1).locator('[role=img]')).toHaveAttribute('aria-label', '국가별 스캔 완료율(%)')
  await expect(charts.nth(0).locator('table tbody tr')).toHaveCount(7)
  await expect(charts.nth(1).locator('table tbody tr')).toHaveCount(3)

  // 등장 애니메이션이 끝날 때까지 대기: 연속 두 프레임 사이 캔버스 이미지가 같아지면 완료
  for (const c of await charts.locator('canvas').all()) {
    await expect.poll(() => c.evaluate((el) => new Promise<boolean>((done) => {
      if (!(el instanceof HTMLCanvasElement)) return done(false)
      const before = el.toDataURL()
      requestAnimationFrame(() => requestAnimationFrame(() => done(el.toDataURL() === before)))
    }))).toBe(true)
  }

  // 캔버스에 실제로 그려졌는지 픽셀 샘플 (라이트·다크 모두)
  await expect.poll(() => charts.nth(0).locator('canvas').evaluate((c) => {
    if (!(c instanceof HTMLCanvasElement)) return 0
    const ctx = c.getContext('2d')
    if (!ctx) return 0
    const d = ctx.getImageData(0, 0, c.width, c.height).data
    let painted = 0
    for (let i = 3; i < d.length; i += 4) if (d[i] > 0) painted++
    return painted
  })).toBeGreaterThan(100)
  // 채팅은 내부 스크롤 영역이라 전체 페이지 캡처로는 안 보여 차트로 이동 후 촬영
  await charts.first().scrollIntoViewIfNeeded()
  await shot(page, 'us6', info)
})

test('차트 블록이 없는 대화는 차트 청크를 받지 않는다', async ({ page }) => {
  const requested: string[] = []
  page.on('request', (r) => { if (CHART_REQUEST.test(r.url())) requested.push(r.url()) })
  await mockApi(page)
  await page.goto('./#/conversations/7')
  await expect(page.locator('.md, .msg, main').first()).toBeVisible()
  await page.waitForLoadState('networkidle')
  expect(requested).toEqual([])
})
