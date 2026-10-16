// 대화 Markdown 내보내기. 형식 기준: specs/005-conversation-export/contracts/export-markdown.md
// 입력은 화면이 가진 대화 상세와 시각뿐(주소·호스트명이 파일에 섞이지 않도록 location·API 주소를 읽지 않음)
import type { ConversationDetail, Evidence, FunnelStep, Message, Proposal } from './api.ts'

const pad = (n: number) => String(n).padStart(2, '0')

function ymd(d: Date, sep: string): string {
  return [d.getFullYear(), pad(d.getMonth() + 1), pad(d.getDate())].join(sep)
}

// 브라우저 로컬 시간 YYYY-MM-DD HH:mm (UTC±HH:MM)
export function localStamp(iso: string): string {
  const d = new Date(iso)
  const off = -d.getTimezoneOffset()
  const sign = off >= 0 ? '+' : '-'
  const abs = Math.abs(off)
  return `${ymd(d, '-')} ${pad(d.getHours())}:${pad(d.getMinutes())} (UTC${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)})`
}

export function exportFileName(title: string | null, id: number, now: Date): string {
  const cleaned = (title ?? '')
    .replace(/[\\/:*?"<>|\u0000-\u001f\u007f]/g, '-')
    .replace(/\s+/g, ' ')
    .replace(/^[\s.]+|[\s.]+$/g, '')
    .slice(0, 60)
  return `${cleaned || `대화-${id}`}-${ymd(now, '')}.md`
}

const DECISION: Record<Proposal['decision']['status'], string> = { adopted: '채택', on_hold: '보류', pending: '미정' }
const TYPE: Record<Proposal['type'], string> = { improvement: '개선 제안', funnel_design: '측정 설계' }

// snippet 안에 ``` 가 있으면 더 긴 펜스로 감쌈
function fence(text: string, indent: string): string {
  const longest = Math.max(2, ...[...text.matchAll(/`+/g)].map((m) => m[0].length))
  const f = '`'.repeat(longest + 1)
  return [f, ...text.split('\n'), f].map((l) => indent + l).join('\n')
}

function evidenceLine(e: Evidence): string {
  switch (e.kind) {
    case 'metric':
      return `- [지표] ${e.summary} — ${e.value} (${e.source})`
    case 'code': {
      const where = [`\`${e.file}\``, e.function === null ? null : `\`${e.function}\``, `L${e.line}`].filter((x) => x !== null).join(' · ')
      return `- [코드] ${e.summary} — ${where}\n${fence(e.snippet, '  ')}`
    }
    case 'taxonomy':
      return `- [택사노미] ${e.summary} — \`${e.eventName}\``
  }
}

const cell = (s: string) => s.replace(/\|/g, '\\|').replace(/\n/g, ' ')

function funnelTable(steps: FunnelStep[]): string {
  const rows = steps.map((s) => {
    const loc = s.location ? [s.location.file, s.location.function, s.location.line === null ? null : `L${s.location.line}`].filter((x) => x !== null).join(' · ') : '-'
    const props = s.properties.length ? s.properties.map((p) => `${p.name}(${p.type})`).join(', ') : '-'
    return `| ${s.order} | ${cell(s.eventName)} | ${s.status === 'new' ? '신규' : '기존'} | ${cell(s.condition ?? '-')} | ${cell(loc)} | ${cell(props)} |`
  })
  return ['| 순서 | 이벤트 | 구분 | 조건 | 위치 | 속성 |', '|---|---|---|---|---|---|', ...rows].join('\n')
}

function proposalBlock(p: Proposal): string {
  const m = p.measurement
  const parts = [
    `### 제안 ${p.seq}. ${p.title} — ${DECISION[p.decision.status]}`,
    `- 유형: ${TYPE[p.type]}`,
    '#### 근거',
    p.evidence.map(evidenceLine).join('\n'),
    '#### 제안',
    p.proposal,
    '#### 실행 단계',
    p.steps.map((s, i) => `${i + 1}. ${s}`).join('\n'),
    '#### 측정 방법',
    `- 핵심 지표: ${m.primaryMetric}\n- 기준값: ${m.baseline ?? '-'} · 목표: ${m.target ?? '-'}`,
  ]
  if (m.funnel.length) parts.push(funnelTable(m.funnel))
  if (p.decision.note) parts.push('#### 결정 메모', p.decision.note)
  return parts.join('\n\n')
}

function messageBlock(m: Message): string {
  const parts = [`## ${m.role === 'user' ? '사용자' : '에이전트'} · ${localStamp(m.createdAt)}`]
  // 본문은 원문 그대로(표·코드·chart 블록 보존)
  if (m.content) parts.push(m.content)
  if (m.status === 'failed') parts.push(`> 실패: ${m.errorCode ?? 'INTERNAL_ERROR'}`)
  for (const p of [...m.proposals].sort((a, b) => a.seq - b.seq)) parts.push(proposalBlock(p))
  return parts.join('\n\n')
}

export function toMarkdown(detail: ConversationDetail, now: Date): string {
  const messages = [...detail.messages].sort((a, b) => a.createdAt.localeCompare(b.createdAt))
  const head = [
    // 제목의 줄바꿈이 Markdown 제목을 깨지 않도록 공백 한 칸으로 접음
    `# ${(detail.title ?? '새 대화').replace(/\s+/g, ' ')}`,
    `- 대화 생성: ${localStamp(detail.createdAt)}\n- 내보낸 날짜: ${ymd(now, '-')}\n- 메시지: ${messages.length}개`,
    '---',
  ]
  return [...head, ...messages.map(messageBlock)].join('\n\n').replace(/\n+$/, '') + '\n'
}
