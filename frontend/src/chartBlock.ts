// ```chart 블록 파서. 형식 기준: specs/003-frontend-redesign/contracts/chart-block.md
// 모델 오타를 조용히 넘기지 않으려고 추가 키도 오류로 처리, 오류면 화면은 원문 코드 블록

export type ChartSpec = {
  type: 'line' | 'bar'
  title: string
  x: string[]
  series: { name: string; values: (number | null)[] }[]
}

export type ChartParse = { ok: true; spec: ChartSpec } | { ok: false; reason: string }

function fail(reason: string): ChartParse {
  return { ok: false, reason }
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function exactKeys(o: Record<string, unknown>, keys: string[]): boolean {
  const got = Object.keys(o)
  return got.length === keys.length && keys.every((k) => got.includes(k))
}

const isLen = (s: unknown, min: number, max: number): s is string => typeof s === 'string' && s.length >= min && s.length <= max

export function parseChartBlock(text: string): ChartParse {
  let v: unknown
  try {
    v = JSON.parse(text)
  } catch {
    return fail('JSON 파싱 실패')
  }
  if (!isRecord(v)) return fail('최상위가 객체가 아님')
  if (!exactKeys(v, ['type', 'title', 'x', 'series'])) return fail('키는 type·title·x·series만 허용')
  const type = v.type
  if (type !== 'line' && type !== 'bar') return fail('type은 line 또는 bar')
  if (!isLen(v.title, 1, 80)) return fail('title은 1~80자 문자열')

  const xRaw = v.x
  if (!Array.isArray(xRaw) || xRaw.length < 1 || xRaw.length > 366) return fail('x는 1~366개 배열')
  const x: string[] = []
  for (const item of xRaw) {
    if (typeof item !== 'string') return fail('x 원소는 문자열')
    x.push(item)
  }

  const seriesRaw = v.series
  if (!Array.isArray(seriesRaw) || seriesRaw.length < 1 || seriesRaw.length > 4) return fail('series는 1~4개 배열')
  const series: ChartSpec['series'] = []
  for (const [i, s] of seriesRaw.entries()) {
    if (!isRecord(s) || !exactKeys(s, ['name', 'values'])) return fail(`series[${i}] 키는 name·values만 허용`)
    if (!isLen(s.name, 1, 40)) return fail(`series[${i}].name은 1~40자 문자열`)
    const valuesRaw = s.values
    if (!Array.isArray(valuesRaw) || valuesRaw.length !== x.length) return fail(`series[${i}].values 길이가 x와 다름`)
    const values: (number | null)[] = []
    for (const n of valuesRaw) {
      if (n === null) values.push(null)
      else if (typeof n === 'number' && Number.isFinite(n)) values.push(n)
      else return fail(`series[${i}].values 원소는 유한한 숫자 또는 null`)
    }
    if (values.every((n) => n === null)) return fail(`series[${i}].values가 전부 null`)
    series.push({ name: s.name, values })
  }
  return { ok: true, spec: { type, title: v.title, x, series } }
}
