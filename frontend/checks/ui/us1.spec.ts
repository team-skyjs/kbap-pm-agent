// 디자인 토큰: 본문 가독성(16px·1.6), 본문·보조 텍스트 대비 4.5:1, 토큰 밖 원시 값 부재
import { readdirSync, readFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { mockApi } from './fixtures.ts'
import { contrast, shot } from './helpers.ts'

const SRC = new URL('../../src/', import.meta.url)

test('본문 크기·줄 간격과 텍스트 대비', async ({ page }, info) => {
  await mockApi(page)
  await page.goto('./#/conversations/7')
  await expect(page.locator('.md').first()).toBeVisible()
  const m = await page.evaluate(() => {
    const css = (el: Element | null) => (el ? getComputedStyle(el) : null)
    const body = css(document.body)
    const muted = css(document.querySelector('.muted'))
    return {
      size: parseFloat(body?.fontSize ?? '0'), line: parseFloat(body?.lineHeight ?? '0'),
      text: body?.color ?? '', bg: body?.backgroundColor ?? '', muted: muted?.color ?? '',
    }
  })
  expect(m.size).toBeGreaterThanOrEqual(16)
  expect(m.line / m.size).toBeGreaterThanOrEqual(1.6)
  expect(contrast(m.text, m.bg)).toBeGreaterThanOrEqual(4.5)
  expect(contrast(m.muted, m.bg)).toBeGreaterThanOrEqual(4.5)
  await shot(page, 'us1', info)
})

// 화면 무관한 정적 검사라 한 프로젝트에서만
test('토큰 밖 원시 값 없음', async ({}, info) => {
  test.skip(info.project.name !== '1280-light', '정적 검사는 한 번만')
  const offenders: string[] = []
  for (const f of readdirSync(SRC).filter((n) => n.endsWith('.css'))) {
    let css = readFileSync(new URL(f, SRC), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')
    // :root 블록(다크 미디어 쿼리 안 포함)은 토큰 정의라 제외, 미디어 쿼리 조건의 px도 제외
    css = css.replace(/:root\s*\{[^}]*\}/g, '').replace(/@media[^{]*\{/g, '{')
    for (const [i, line] of css.split('\n').entries()) {
      const hex = line.match(/#[0-9a-f]{3,8}\b/i)
      const px = [...line.matchAll(/(?<![\w-])(\d*\.?\d+)px\b/g)].find((x) => x[1] !== '0' && x[1] !== '1')
      if (hex || px) offenders.push(`${f}:${i + 1}: ${line.trim()}`)
    }
  }
  for (const f of readdirSync(SRC).filter((n) => n.endsWith('.tsx'))) {
    if (/style=\{\{/.test(readFileSync(new URL(f, SRC), 'utf8'))) offenders.push(`${f}: style={{...}}`)
  }
  expect(offenders).toEqual([])
})
