// UI 검사 공용 도구: 접근성, 대비, 가로 넘침, 스크린샷
import { mkdirSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, type TestInfo } from '@playwright/test'

export async function expectNoSeriousA11y(page: Page): Promise<void> {
  const { violations } = await new AxeBuilder({ page }).analyze()
  const serious = violations.filter((v) => v.impact === 'critical' || v.impact === 'serious')
  expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([])
}

// WCAG 상대 휘도 대비. 입력은 rgb()/rgba() 또는 #rrggbb
export function contrast(fg: string, bg: string): number {
  const lum = (c: string) => {
    const hex = c.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i)
    const nums = hex ? hex.slice(1).map((h) => parseInt(h, 16)) : (c.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number)
    const [r, g, b] = nums.map((v) => {
      const s = v / 255
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
    })
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }
  const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x)
  return (a + 0.05) / (b + 0.05)
}

export async function expectNoHorizontalScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)
}

const SHOT_DIR = new URL('../../../_workspace/04_designer_screenshots/', import.meta.url)

// 파일명: <story>-<project>.png (ui-review 입력)
export async function shot(page: Page, story: string, info: TestInfo): Promise<void> {
  mkdirSync(SHOT_DIR, { recursive: true })
  await page.screenshot({ path: new URL(`${story}-${info.project.name}.png`, SHOT_DIR).pathname, fullPage: true })
}
