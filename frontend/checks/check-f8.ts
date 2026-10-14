// 검사: 마크다운 렌더러의 안전·한글 굵게 처리 (HTML 비해석, 링크 속성, 조사 붙은 굵게, 코드 안 ** 유지)
import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import Markdown from '../src/Markdown.tsx'

const html = (md: string) => renderToStaticMarkup(createElement(Markdown, null, md))

assert(html('<script>alert(1)</script>').includes('&lt;script&gt;'), 'HTML은 문자로 표시')
assert(!html('<script>alert(1)</script>').includes('<script>'))
assert(html('[a](https://example.com)').includes('target="_blank" rel="noopener noreferrer"'))

assert(html('완료 비율이 **41%**로 낮다').includes('<strong>41%</strong>로'))
assert(html('**scan_complete(성공)**에서').includes('<strong>scan_complete(성공)</strong>에서'))
assert(html('**A**와 **B%**는').includes('<strong>A</strong>와 <strong>B%</strong>는'))
assert(html('`**코드**로`').includes('<code>**코드**로</code>'), '인라인 코드 안은 그대로')
assert(html('```\n**x**로\n```').includes('**x**로'), '코드 블록 안은 그대로')
assert(!html('2 ** 3 ** 4').includes('<strong>'), '공백 둘러싼 **는 굵게 아님')
