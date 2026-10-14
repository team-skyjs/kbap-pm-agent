// F6 검사: npm run build 산출물의 자산 경로가 /kbap-pm-agent/로 시작하고, 번들에 VITE_API_BASE_URL 값이 들어 있다.
// 실행: VITE_API_BASE_URL=https://... npm run build && VITE_API_BASE_URL=https://... npm run check -- f6
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'

const base = process.env.VITE_API_BASE_URL
assert(base, 'VITE_API_BASE_URL 환경변수가 필요합니다 (빌드에 쓴 값과 같아야 함)')
const dist = new URL('../dist/', import.meta.url)
const html = readFileSync(new URL('index.html', dist), 'utf8')

const refs = [...html.matchAll(/(?:src|href)="([^"]+)"/g)].map((m) => m[1])
assert(refs.length > 0, 'index.html에 자산 참조가 없습니다')
for (const r of refs) assert(r.startsWith('/kbap-pm-agent/'), `하위 경로 밖 자산: ${r}`)

const bundle = readdirSync(new URL('assets/', dist)).filter((f) => f.endsWith('.js'))
  .map((f) => readFileSync(new URL(`assets/${f}`, dist), 'utf8')).join('\n')
assert(bundle.includes(base), `번들에 ${base}가 없습니다`)
// 운영 빌드(VITE_MOCK 없음)에는 mock 데이터가 트리셰이킹으로 빠져야 한다
assert(!bundle.includes('OCR 실패 화면에'), 'mock 데이터가 번들에 남아 있습니다 (VITE_MOCK=1로 빌드했나?)')
