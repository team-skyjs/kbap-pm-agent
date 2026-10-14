### POST /api/integrations/amplitude/connect
- 용도: Amplitude MCP OAuth 시작. 프론트는 받은 URL을 새 탭으로 연다.
- 요청: 본문 없음.
- 응답 200:
```json
{"authorizationUrl": "https://app.amplitude.com/oauth/authorize?response_type=code&client_id=mcp-4f2a91&redirect_uri=https%3A%2F%2Fpm-agent.example.com%2Fapi%2Fintegrations%2Famplitude%2Fcallback&state=Zx81kQ&code_challenge=Q9v0aR3&code_challenge_method=S256"}
```
  (URL의 호스트·쿼리는 Amplitude가 정한다. 프론트는 문자열을 그대로 연다.)
- 에러: `UPSTREAM_ERROR`.
- 비고: 승인 완료는 이 응답으로 알 수 없다. 프론트는 새 탭을 연 뒤 `GET /api/settings`를 3초 간격으로 최대 2분 다시 읽어 `amplitude.status`가 `"connected"`가 되면 멈춘다.

### GET /api/integrations/amplitude/callback
- 용도: Amplitude가 브라우저를 돌려보내는 OAuth 콜백. 앱 수준 인증(`ACCESS_TOKEN`)이 필요 없다. 프론트가 직접 부르지 않는다.
- 접근 계층: 다른 경로와 같이 Cloudflare Access 뒤에 있다. 브라우저 최상위 이동이라 Access 세션 쿠키로 통과한다. 통과하지 못하는 것으로 확인되면 이 경로에만 Access 우회 정책을 둔다(specs/002-access-gate research R2). `state` 검증은 백엔드가 그대로 한다.
- 요청: 쿼리 `code`, `state` (Amplitude가 붙인다).
- 응답 200: `text/html` 한 줄 페이지. 성공 시 "Amplitude 연결 완료. 이 탭을 닫아도 됩니다.", 실패 시 "Amplitude 연결 실패: {사유}". JSON 아님.

