### GET /api/conversations
- 용도: 대화 목록. `updatedAt` 내림차순.
- 응답 200:
```json
{
  "items": [
    {"id": 7, "title": "스캔 퍼널 이탈 지점 개선안", "createdAt": "2026-10-15T09:12:03.418Z", "updatedAt": "2026-10-15T09:14:41.022Z", "messageCount": 2, "proposalCount": 2, "adoptedCount": 1},
    {"id": 6, "title": null, "createdAt": "2026-10-14T05:40:00.000Z", "updatedAt": "2026-10-14T05:40:00.000Z", "messageCount": 0, "proposalCount": 0, "adoptedCount": 0}
  ]
}
```

### POST /api/conversations
- 용도: 빈 대화 생성.
- 요청: 본문 `{}` 또는 `{"title": "장바구니 개선 측정 설계"}`. `title`은 1~200자.
- 응답 201: ConversationSummary
```json
{"id": 8, "title": "장바구니 개선 측정 설계", "createdAt": "2026-10-15T10:00:00.000Z", "updatedAt": "2026-10-15T10:00:00.000Z", "messageCount": 0, "proposalCount": 0, "adoptedCount": 0}
```
- 에러: `VALIDATION_ERROR`.

### GET /api/conversations/{conversationId}
- 용도: 대화 상세. 메시지는 `createdAt` 오름차순, 각 메시지에 toolCalls·proposals·usage 포함.
- 응답 200:
```json
{
  "id": 7,
  "title": "스캔 퍼널 이탈 지점 개선안",
  "createdAt": "2026-10-15T09:12:03.418Z",
  "updatedAt": "2026-10-15T09:14:41.022Z",
  "messages": [
    {"id": 41, "conversationId": 7, "role": "user", "status": "completed", "content": "스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘", "errorCode": null, "toolCalls": [], "proposals": [], "usage": null, "createdAt": "2026-10-15T09:12:03.990Z"},
    {"id": 42, "conversationId": 7, "role": "assistant", "status": "completed", "content": "지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다.", "errorCode": null, "toolCalls": [{"id": 301, "seq": 1, "source": "amplitude", "name": "query_funnel", "input": {"events": ["scan_start", "scan_complete"], "start": "2026-09-15", "end": "2026-10-14"}, "status": "succeeded", "resultSummary": "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%", "durationMs": 2310, "startedAt": "2026-10-15T09:12:05.101Z"}], "proposals": [{"id": 14, "conversationId": 7, "messageId": 42, "seq": 1, "type": "improvement", "title": "OCR 실패 화면에 재시도·직접 입력 동선 추가", "evidence": [{"kind": "metric", "summary": "실패한 scan_complete 중 fail_reason=ocr_empty가 62%다.", "value": "62%", "source": "Amplitude segmentation: scan_complete(success=false) by fail_reason, 2026-09-15~2026-10-14"}], "proposal": "OCR 실패 화면에 '다시 찍기'와 '메뉴 이름 직접 입력' 버튼을 둔다.", "steps": ["src/app/scan.tsx 실패 상태 UI에 버튼 2개를 추가한다.", "직접 입력은 기존 search 화면으로 이동시킨다."], "measurement": {"primaryMetric": "scan_start 대비 scan_complete(success=true) 전환율", "baseline": "41.3%", "target": "48%", "funnel": []}, "decision": {"status": "pending", "note": null, "decidedAt": null}, "createdAt": "2026-10-15T09:14:40.980Z"}], "usage": {"model": "anthropic:claude-sonnet-5-5", "inputTokens": 18432, "outputTokens": 2210, "costUsd": 0.0884}, "createdAt": "2026-10-15T09:12:04.002Z"}
  ]
}
```
- 에러: `CONVERSATION_NOT_FOUND`.

