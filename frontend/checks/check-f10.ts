// 검사: 대화 Markdown 내보내기(export-markdown.md 규격). 계약 상세·Proposal 예시로 생성 결과의 구조, 원문 보존, 파일 이름 규칙
import assert from 'node:assert/strict'
import { parseConversationDetail, parseProposal, type ConversationDetail } from '../src/api.ts'
import { exportFileName, localStamp, toMarkdown } from '../src/exportMarkdown.ts'
import { blocks, jsonBlock } from './contract.ts'

const now = new Date(2026, 9, 17, 12, 30)
const base: ConversationDetail = parseConversationDetail(jsonBlock('04-conversations.md', 2))
const funnel = parseProposal(jsonBlock('02-objects.md', 2))
const [userMsg, agentMsg] = base.messages
// 계약 상세 예시의 개선 제안에 Proposal 예시(측정 설계, 근거 3종, 채택)를 더함
const detail: ConversationDetail = { ...base, messages: [userMsg, { ...agentMsg, proposals: [...agentMsg.proposals, { ...funnel, seq: 2 }] }] }
const md = toMarkdown(detail, now)

// 머리글
assert(md.startsWith('# 스캔 퍼널 이탈 지점 개선안\n\n- 대화 생성: '), md.slice(0, 80))
assert(md.includes(`- 대화 생성: ${localStamp(base.createdAt)}\n- 내보낸 날짜: 2026-10-17\n- 메시지: 2개\n\n---\n\n`))
assert.match(localStamp(base.createdAt), /^\d{4}-\d{2}-\d{2} \d{2}:\d{2} \(UTC[+-]\d{2}:\d{2}\)$/)

// 메시지: 역할·시각 제목과 본문 원문
assert(md.includes(`## 사용자 · ${localStamp(userMsg.createdAt)}\n\n${userMsg.content}`))
assert(md.includes(`## 에이전트 · ${localStamp(agentMsg.createdAt)}\n\n${agentMsg.content}`))

// 제안: 상태 라벨, 유형, 네 절, 근거 3종, 퍼널 표, 메모
assert(md.includes('### 제안 1. OCR 실패 화면에 재시도·직접 입력 동선 추가 — 미정\n\n- 유형: 개선 제안'))
assert(md.includes('### 제안 2. 스캔 실패 후 재시도 퍼널 측정 설계 — 채택\n\n- 유형: 측정 설계'))
for (const h of ['#### 근거', '#### 제안', '#### 실행 단계', '#### 측정 방법']) assert.equal(md.split(`\n${h}\n`).length - 1, 2, h)
assert(md.includes('- [지표] 실패한 scan_complete 중 fail_reason=ocr_empty가 62%다. — 62% (Amplitude segmentation'))
assert(md.includes('- [코드] 실패 시 scan_complete를 success=false로 보내고 끝나며, 재시도 버튼 핸들러에는 이벤트가 없다. — `src/app/scan.tsx` · `onScanFailed` · L405\n  ```\n  track(EVENTS.scan_complete'))
assert(md.includes('- [택사노미] scan_complete는 성공·실패를 success 속성으로 구분한다. — `scan_complete`'))
assert(md.includes('1. src/app/scan.tsx 실패 상태 UI에 버튼 2개를 추가한다.\n2. 직접 입력은 기존 search 화면으로 이동시킨다.'))
assert(md.includes('- 핵심 지표: scan_start 대비 scan_complete(success=true) 전환율\n- 기준값: 41.3% · 목표: 48%'))
assert(md.includes('- 기준값: - · 목표: 35%'))
assert(md.includes('| 순서 | 이벤트 | 구분 | 조건 | 위치 | 속성 |\n|---|---|---|---|---|---|\n| 1 | scan_complete | 기존 | success=false | - | - |'))
assert(md.includes('| 2 | scan_retry_tap | 신규 | - | src/app/scan.tsx · handleRetry · L398 | fail_reason(string) |'))
assert(md.includes('#### 결정 메모\n\nKB-812로 이번 스프린트에 진행'))
assert(md.endsWith('\n') && !md.endsWith('\n\n'), '파일 끝 줄바꿈 하나')

// 넣지 않는 것: 도구 호출·사용량
assert(!md.includes('query_funnel') && !md.includes('costUsd') && !md.includes('anthropic:'))

// chart 블록 원문 보존(003 차트 형식 선 예시)
const chartLine = blocks('chart-block.md', new URL('../../specs/003-frontend-redesign/contracts/', import.meta.url))
  .flatMap((b) => b.split('\n')).find((l) => l.startsWith('{"type":"line"'))
assert(chartLine)
const chartContent = `추세입니다.\n\n\`\`\`chart\n${chartLine}\n\`\`\`\n\n| a | b |\n|---|---|\n| 1 | 2 |`
const withChart = toMarkdown({ ...detail, messages: [{ ...agentMsg, proposals: [], content: chartContent }] }, now)
assert(withChart.includes(chartContent), 'chart 블록·표 원문 그대로')

// 실패 메시지
const failed = toMarkdown({ ...detail, messages: [{ ...agentMsg, status: 'failed', errorCode: 'UPSTREAM_ERROR', content: '', proposals: [] }] }, now)
assert(failed.includes(`## 에이전트 · ${localStamp(agentMsg.createdAt)}\n\n> 실패: UPSTREAM_ERROR`))

// 제목 없음
assert(toMarkdown({ ...detail, title: null }, now).startsWith('# 새 대화\n'))

// 운영 정보: 본문 원문(content) 밖에 주소 없음
const withoutContent = toMarkdown({ ...detail, messages: detail.messages.map((m) => ({ ...m, content: '' })) }, now)
assert(!/https?:\/\//.test(withoutContent), '생성 부분에 http(s) 주소 없음')

// 파일 이름
assert.equal(exportFileName('스캔 퍼널 이탈 지점 개선안', 7, now), '스캔 퍼널 이탈 지점 개선안-20261017.md')
assert.equal(exportFileName(null, 8, now), '대화-8-20261017.md')
assert.equal(exportFileName('a/b:c*d?"e<f>g|h\\i', 1, now), 'a-b-c-d--e-f-g-h-i-20261017.md')
assert.equal(exportFileName('  여러   공백  .', 1, now), '여러 공백-20261017.md')
assert.equal(exportFileName('...', 3, now), '대화-3-20261017.md')
assert.equal(exportFileName('가'.repeat(80), 1, now), `${'가'.repeat(60)}-20261017.md`)
assert.equal(exportFileName('탭\t과\n줄바꿈', 1, now), '탭-과-줄바꿈-20261017.md')
