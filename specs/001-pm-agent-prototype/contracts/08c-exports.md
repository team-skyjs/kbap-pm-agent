### POST /api/conversations/{conversationId}/exports
- 용도: 사용자가 대화를 내보냈다는 사실(형식)을 기록한다. 내보내기 건수·형식 집계용이며 화면에는 보이지 않는다. 내보내기 자체(PDF 인쇄, Markdown 파일 생성)는 프론트가 하고 서버는 파일을 만들지 않는다.
- 요청:
```json
{"format": "markdown"}
```
  - `format`: `"pdf"`(인쇄 대화상자를 열었을 때. 실제 저장 여부는 알 수 없다) | `"markdown"`(파일 내려받기를 시작했을 때).
- 응답 201:
```json
{"exportId": 12, "conversationId": 7, "format": "markdown", "createdAt": "2026-10-17T03:20:45.118Z"}
```
- 에러: `VALIDATION_ERROR`(형식 밖 값, 본문 오류), `CONVERSATION_NOT_FOUND`. 공통 인증 규칙(`ACCESS_TOKEN`)은 다른 `/api` 요청과 같다.
- 비고: 프론트는 내보내기를 시작하면서 한 번 부르고 결과를 기다리지 않는다. 기록 실패는 내보내기를 막지 않는다. 시연 모드도 실제로 기록한다(외부 호출이 없다).

