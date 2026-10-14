// npm run check -- f1   → checks/check-f1.ts 하나
// npm run check         → checks/check-*.ts 전부
import { readdirSync } from 'node:fs'

const only = process.argv[2]
const files = readdirSync(new URL('.', import.meta.url))
  .filter((f) => /^check-f\d\.ts$/.test(f))
  // f6은 빌드 산출물이 필요해 이름으로 부를 때만 돈다
  .filter((f) => (only ? f === `check-${only}.ts` : f !== "check-f6.ts"))
  .sort()
if (files.length === 0) throw new Error(`검사 없음: ${only ?? '(전체)'}`)
for (const f of files) {
  await import(`./${f}`)
  console.log(`OK ${f}`)
}
