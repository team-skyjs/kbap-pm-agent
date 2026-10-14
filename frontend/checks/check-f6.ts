// 검사: 빌드 산출물 자산 경로가 /assets/로 시작, 번들에 절대 API 주소 없음 (같은 출처 상대 경로 호출)
// 실행: npm run build && npm run check -- f6
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'

const dist = new URL('../dist/', import.meta.url)
const html = readFileSync(new URL('index.html', dist), 'utf8')

const refs = [...html.matchAll(/(?:src|href)="([^"]+)"/g)].map((m) => m[1])
assert(refs.length > 0, 'index.html에 자산 참조가 없습니다')
for (const r of refs) assert(r.startsWith('/assets/'), `/assets/ 밖 자산: ${r}`)

const bundle = readdirSync(new URL('assets/', dist)).filter((f) => f.endsWith('.js'))
  .map((f) => readFileSync(new URL(`assets/${f}`, dist), 'utf8')).join('\n')
// React 오류 안내 링크 같은 일반 URL은 허용, /api 경로가 붙은 절대 주소와 로컬 백엔드 주소만 금지
const abs = bundle.match(/https?:\/\/[^"'`\s]*\/api\//)
assert(!abs, `번들에 절대 API 주소: ${abs?.[0]}`)
assert(!bundle.includes('localhost:8000'), '번들에 로컬 백엔드 주소가 있습니다')
assert(bundle.includes('"/api/health"') || bundle.includes("'/api/health'") || bundle.includes('`/api/health`'), '상대 경로 /api/health 호출이 번들에 없습니다')
