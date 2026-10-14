### POST /api/integrations/amplitude/connect
- 용도: Amplitude MCP OAuth 시작. 프론트는 받은 URL을 새 탭으로 연다.
- 요청: 본문 없음.
- 응답 200:
```json
{"authorizationUrl": "https://app.amplitude.com/oauth/authorize?response_type=code&client_id=mcp-4f2a91&redirect_uri=https%3A%2F%2Fpm-agent-api.simhani1.dev%2Fapi%2Fintegrations%2Famplitude%2Fcallback&state=Zx81kQ&code_challenge=Q9v0aR3&code_challenge_method=S256"}
```
  (URL의 호스트·쿼리는 Amplitude가 정한다. 프론트는 문자열을 그대로 연다.)
- 에러: `UPSTREAM_ERROR`.
- 비고: 승인 완료는 이 응답으로 알 수 없다. 프론트는 새 탭을 연 뒤 `GET /api/settings`를 3초 간격으로 최대 2분 다시 읽어 `amplitude.status`가 `"connected"`가 되면 멈춘다.

### GET /api/integrations/amplitude/callback
- 용도: Amplitude가 브라우저를 돌려보내는 OAuth 콜백. 인증 불필요. 프론트가 직접 부르지 않는다.
- 요청: 쿼리 `code`, `state` (Amplitude가 붙인다).
- 응답 200: `text/html` 한 줄 페이지. 성공 시 "Amplitude 연결 완료. 이 탭을 닫아도 됩니다.", 실패 시 "Amplitude 연결 실패: {사유}". JSON 아님.

