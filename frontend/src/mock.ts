// ponytail: 백엔드 없이 화면을 띄우는 가짜 fetch. 값은 계약서 v1.1 예시 그대로. VITE_MOCK=1일 때만 쓰인다.
// 실제 백엔드 연동이 끝나면 이 파일과 api.ts의 MOCK 분기를 지운다.

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

export async function mockFetch(path: string, init: RequestInit): Promise<Response> {
  const method = init.method ?? 'GET'
  if (method === 'GET' && path === '/api/health') return json(200, { status: 'ok', db: 'ok', version: '0.1.0' })
  return json(404, { error: { code: 'NOT_FOUND', message: `mock: ${method} ${path} 없음` } })
}
