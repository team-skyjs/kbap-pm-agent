// 검사: chart-block.md 예시 세 개(선·막대 통과, pie 오류)와 검증 규칙별 오류
import assert from 'node:assert/strict'
import { parseChartBlock, type ChartSpec } from '../src/chartBlock.ts'
import { blocks } from './contract.ts'

const doc = blocks('chart-block.md', new URL('../../specs/003-frontend-redesign/contracts/', import.meta.url))
// 바깥 ````markdown 펜스 안의 첫 예시는 ```chart 줄을 포함하므로 JSON 줄만 추출
const charts = doc.flatMap((b) => b.split('\n').filter((l) => l.startsWith('{')))
assert.equal(charts.length, 3, `차트 예시 3개 기대, ${charts.length}개`)

const line = parseChartBlock(charts[0])
assert(line.ok, '선 예시 통과')
const spec: ChartSpec = line.spec
assert.equal(spec.type, 'line')
assert.equal(spec.x.length, 7)
assert.deepEqual(spec.series[0].values, [312, 298, 341, 355, 330, 362, 371])

const bar = parseChartBlock(charts[1])
assert(bar.ok && bar.spec.type === 'bar' && bar.spec.series[0].values[0] === 41.3)

assert.equal(parseChartBlock(charts[2]).ok, false, 'pie는 형식 오류')

// 규칙별 오류
const base = { type: 'line', title: 't', x: ['a', 'b'], series: [{ name: 's', values: [1, null] }] }
const bad = (o: unknown) => parseChartBlock(JSON.stringify(o)).ok
assert.equal(bad(base), true)
assert.equal(parseChartBlock('{not json').ok, false)
assert.equal(bad([base]), false)
assert.equal(bad({ ...base, extra: 1 }), false)
assert.equal(bad({ ...base, title: '' }), false)
assert.equal(bad({ ...base, title: 'x'.repeat(81) }), false)
assert.equal(bad({ ...base, x: [] }), false)
assert.equal(bad({ ...base, x: Array(367).fill('d'), series: [{ name: 's', values: Array(367).fill(1) }] }), false)
assert.equal(bad({ ...base, x: [1, 2] }), false)
assert.equal(bad({ ...base, series: [] }), false)
assert.equal(bad({ ...base, series: Array(5).fill(base.series[0]) }), false)
assert.equal(bad({ ...base, series: [{ name: 's', values: [1] }] }), false, '길이 불일치')
assert.equal(bad({ ...base, series: [{ name: 's', values: [null, null] }] }), false, '전부 null')
assert.equal(bad({ ...base, series: [{ name: 's', values: [1, '2'] }] }), false)
assert.equal(bad({ ...base, series: [{ name: '', values: [1, 2] }] }), false)
assert.equal(bad({ ...base, series: [{ name: 's', values: [1, 2], color: 'red' }] }), false)
