import { lazy, memo, Suspense, useState } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkCjkFriendly from 'remark-cjk-friendly'
import remarkGfm from 'remark-gfm'
import { parseChartBlock } from './chartBlock.ts'

// 차트 라이브러리는 차트 블록이 처음 나올 때만 별도 청크로 로드
const ChartBlock = lazy(() => import('./ChartBlock.tsx'))

type HastNode = { type: string; value?: string; tagName?: string; properties?: Record<string, unknown>; children?: HastNode[] }

function textOf(n: HastNode): string {
  return n.value ?? (n.children ?? []).map(textOf).join('')
}

function CodeBlock({ lang, code }: { lang: string; code: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')
  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setState('copied')
    } catch {
      // 복사 미지원 환경에서도 버튼은 유지, 실패만 짧게 안내
      setState('failed')
    }
    setTimeout(() => setState('idle'), 1500)
  }
  return (
    <div className="md-code">
      <div className="md-code-bar">
        <span className="md-code-lang">{lang || 'text'}</span>
        <button type="button" className="md-code-copy" onClick={() => void copy()} aria-live="polite">
          {state === 'copied' ? '복사됨' : state === 'failed' ? '복사 실패' : '복사'}
        </button>
      </div>
      <pre><code className={lang ? `language-${lang}` : undefined}>{code}</code></pre>
    </div>
  )
}

const components: Components = {
  // 새 탭, 원래 창 접근 권한 차단
  a: ({ node: _node, children, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer">{children}</a>,
  // 넓은 표는 감싸개 안에서 가로 스크롤, 키보드로도 스크롤하도록 포커스 가능 영역
  table: ({ node: _node, children, ...props }) => (
    <div className="md-table-scroll" tabIndex={0} role="region" aria-label="표"><table {...props}>{children}</table></div>
  ),
  pre: ({ node }) => {
    const code = node?.children.find((c): c is typeof c & HastNode => c.type === 'element' && c.tagName === 'code')
    const cls = code?.properties?.className
    const lang = (Array.isArray(cls) ? cls : []).map(String).find((c) => c.startsWith('language-'))?.slice('language-'.length) ?? ''
    const text = code ? textOf(code).replace(/\n$/, '') : ''
    if (lang === 'chart') {
      const parsed = parseChartBlock(text)
      if (parsed.ok) {
        return (
          <Suspense fallback={<div className="md-chart-loading">차트 불러오는 중…</div>}>
            <ChartBlock spec={parsed.spec} />
          </Suspense>
        )
      }
    }
    return <CodeBlock lang={lang} code={text} />
  },
}

// 답변·제안 텍스트 공용 렌더러. 모델이 쓴 HTML은 해석하지 않고 문자로 표시(react-markdown 기본 동작)
// remark-cjk-friendly: 문장부호 뒤 닫는 강조에 한글 조사가 붙어도(**41%**로) 강조로 인식
function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkCjkFriendly]} components={components}>{children}</ReactMarkdown>
    </div>
  )
}

// 입력창 타이핑 같은 부모 리렌더마다 다시 파싱하면 차트 spec 객체가 바뀌어 차트가 파괴·재생성됨, 본문 문자열이 같으면 건너뜀
export default memo(Markdown)
