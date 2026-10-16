"""계약서 예시 JSON 원문 복사본. 계약이 바뀌면 함께 갱신."""
import json

TOOL_CALL_301 = json.loads('''{"id": 301, "seq": 1, "source": "amplitude", "name": "query_funnel", "input": {"events": ["scan_start", "scan_complete"], "start": "2026-09-15", "end": "2026-10-14"}, "status": "succeeded", "resultSummary": "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%", "durationMs": 2310, "startedAt": "2026-10-15T09:12:05.101Z"}''')

MESSAGE_42 = json.loads('''{
  "id": 42, "conversationId": 7, "role": "assistant", "status": "completed",
  "content": "지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다. 실패의 62%가 OCR 실패이고, 실패 화면에 재시도 동작이 없습니다. 아래 두 제안을 확인해 주세요.",
  "errorCode": null,
  "toolCalls": [
    {"id": 301, "seq": 1, "source": "amplitude", "name": "query_funnel", "input": {"events": ["scan_start", "scan_complete"], "start": "2026-09-15", "end": "2026-10-14"}, "status": "succeeded", "resultSummary": "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%", "durationMs": 2310, "startedAt": "2026-10-15T09:12:05.101Z"},
    {"id": 302, "seq": 2, "source": "code", "name": "find_event_calls", "input": {"eventName": "scan_complete"}, "status": "succeeded", "resultSummary": "2곳: src/app/scan.tsx:405 (실패), src/app/scan.tsx:427 (성공)", "durationMs": 14, "startedAt": "2026-10-15T09:12:08.550Z"}
  ],
  "proposals": [],
  "usage": {"model": "anthropic:claude-sonnet-5-5", "inputTokens": 18432, "outputTokens": 2210, "costUsd": 0.0884},
  "createdAt": "2026-10-15T09:12:04.002Z"
}''')

PROPOSAL_15 = json.loads('''{
  "id": 15, "conversationId": 7, "messageId": 42, "seq": 1, "type": "funnel_design",
  "title": "스캔 실패 후 재시도 퍼널 측정 설계",
  "evidence": [
    {"kind": "metric", "summary": "최근 30일 scan_start 대비 성공한 scan_complete 전환율이 41.3%다.", "value": "41.3%", "source": "Amplitude funnel: scan_start → scan_complete(success=true), 2026-09-15~2026-10-14"},
    {"kind": "code", "summary": "실패 시 scan_complete를 success=false로 보내고 끝나며, 재시도 버튼 핸들러에는 이벤트가 없다.", "file": "src/app/scan.tsx", "function": "onScanFailed", "line": 405, "snippet": "track(EVENTS.scan_complete, { success: false, fail_reason: reason, item_count: 0, degraded: false });"},
    {"kind": "taxonomy", "summary": "scan_complete는 성공·실패를 success 속성으로 구분한다.", "eventName": "scan_complete"}
  ],
  "proposal": "실패 화면의 재시도 동작에 신규 이벤트 scan_retry_tap을 심어, 실패 후 재시도로 회복되는 비율을 측정한다.",
  "steps": [
    "EVENTS 상수에 scan_retry_tap을 추가한다.",
    "src/app/scan.tsx의 handleRetry 첫 줄에서 track(EVENTS.scan_retry_tap, { fail_reason })를 호출한다.",
    "택사노미 문서에 scan_retry_tap 정의와 fail_reason 속성을 추가한다.",
    "배포 후 7일간 아래 퍼널을 Amplitude에 저장해 확인한다."
  ],
  "measurement": {
    "primaryMetric": "scan_complete(success=false) 이후 24시간 내 scan_complete(success=true) 도달 비율",
    "baseline": null, "target": "35%",
    "funnel": [
      {"order": 1, "eventName": "scan_complete", "status": "existing", "condition": "success=false", "location": null, "properties": []},
      {"order": 2, "eventName": "scan_retry_tap", "status": "new", "condition": null, "location": {"file": "src/app/scan.tsx", "function": "handleRetry", "line": 398}, "properties": [{"name": "fail_reason", "type": "string"}]},
      {"order": 3, "eventName": "scan_complete", "status": "existing", "condition": "success=true", "location": null, "properties": []}
    ]
  },
  "decision": {"status": "adopted", "note": "KB-812로 이번 스프린트에 진행", "decidedAt": "2026-10-15T09:20:11.730Z"},
  "createdAt": "2026-10-15T09:14:40.990Z"
}''')

CONV_LIST = json.loads('''{
  "items": [
    {"id": 7, "title": "스캔 퍼널 이탈 지점 개선안", "createdAt": "2026-10-15T09:12:03.418Z", "updatedAt": "2026-10-15T09:14:41.022Z", "messageCount": 2, "proposalCount": 2, "adoptedCount": 1},
    {"id": 6, "title": null, "createdAt": "2026-10-14T05:40:00.000Z", "updatedAt": "2026-10-14T05:40:00.000Z", "messageCount": 0, "proposalCount": 0, "adoptedCount": 0}
  ]
}''')

CONV_DETAIL = json.loads('''{
  "id": 7, "title": "스캔 퍼널 이탈 지점 개선안", "createdAt": "2026-10-15T09:12:03.418Z", "updatedAt": "2026-10-15T09:14:41.022Z",
  "messages": [
    {"id": 41, "conversationId": 7, "role": "user", "status": "completed", "content": "스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘", "errorCode": null, "toolCalls": [], "proposals": [], "usage": null, "createdAt": "2026-10-15T09:12:03.990Z"},
    {"id": 42, "conversationId": 7, "role": "assistant", "status": "completed", "content": "지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다.", "errorCode": null, "toolCalls": [{"id": 301, "seq": 1, "source": "amplitude", "name": "query_funnel", "input": {"events": ["scan_start", "scan_complete"], "start": "2026-09-15", "end": "2026-10-14"}, "status": "succeeded", "resultSummary": "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%", "durationMs": 2310, "startedAt": "2026-10-15T09:12:05.101Z"}], "proposals": [{"id": 14, "conversationId": 7, "messageId": 42, "seq": 1, "type": "improvement", "title": "OCR 실패 화면에 재시도·직접 입력 동선 추가", "evidence": [{"kind": "metric", "summary": "실패한 scan_complete 중 fail_reason=ocr_empty가 62%다.", "value": "62%", "source": "Amplitude segmentation: scan_complete(success=false) by fail_reason, 2026-09-15~2026-10-14"}], "proposal": "OCR 실패 화면에 '다시 찍기'와 '메뉴 이름 직접 입력' 버튼을 둔다.", "steps": ["src/app/scan.tsx 실패 상태 UI에 버튼 2개를 추가한다.", "직접 입력은 기존 search 화면으로 이동시킨다."], "measurement": {"primaryMetric": "scan_start 대비 scan_complete(success=true) 전환율", "baseline": "41.3%", "target": "48%", "funnel": []}, "decision": {"status": "pending", "note": null, "decidedAt": null}, "createdAt": "2026-10-15T09:14:40.980Z"}], "usage": {"model": "anthropic:claude-sonnet-5-5", "inputTokens": 18432, "outputTokens": 2210, "costUsd": 0.0884}, "createdAt": "2026-10-15T09:12:04.002Z"}
  ]
}''')

CREATED_8 = json.loads('''{"id": 8, "title": "장바구니 개선 측정 설계", "createdAt": "2026-10-15T10:00:00.000Z", "updatedAt": "2026-10-15T10:00:00.000Z", "messageCount": 0, "proposalCount": 0, "adoptedCount": 0}''')

SETTINGS = json.loads('''{
  "repository": {"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop", "headCommit": "9f3c2a1", "codeMapCommit": "9f3c2a1", "codeMapStatus": "ready", "trackedEventCount": 87, "screenCount": 41, "syncedAt": "2026-10-15T08:55:02.117Z", "lastError": null},
  "taxonomy": {"eventCount": 64, "uploadedAt": "2026-10-14T12:01:44.500Z"},
  "amplitude": {"status": "configured"},
  "models": {"agent": "anthropic:claude-sonnet-5-5", "codeSummary": "anthropic:claude-haiku-5-5"},
  "agentMode": "real",
  "budget": {"limitUsd": 200.0, "spentUsd": 3.4172}
}''')

TAXONOMY_BODY = json.loads('''{
  "events": [
    {"name": "scan_complete", "description": "메뉴판 스캔이 끝나 결과 화면에 도달했거나 실패했을 때", "category": "scan",
     "properties": [
       {"name": "success", "type": "boolean", "description": "스캔 성공 여부"},
       {"name": "fail_reason", "type": "string", "description": "실패 사유 코드. 성공이면 없음"},
       {"name": "item_count", "type": "number", "description": "인식된 메뉴 수"}
     ]},
    {"name": "scan_start", "description": "카메라 촬영 또는 갤러리 선택으로 스캔을 시작했을 때", "category": "scan",
     "properties": [{"name": "source", "type": "string", "description": "camera 또는 gallery"}]}
  ]
}''')


REFINE = json.loads('''{"refinementId": 31, "refined": "최근 7일 scan_start → scan_complete(success=true) 퍼널에서 이탈이 가장 큰 단계를 찾고, 그 원인이 되는 화면 동작과 개선안을 제안해줘.", "summary": "기간을 최근 7일로 정하고(원문에 없음), 이벤트 이름과 원하는 산출물(개선안)을 명시했다."}''')

REFINE_CHOICE = json.loads('''{"refinementId": 31, "choice": "refined", "chosenAt": "2026-10-15T10:02:11.204Z"}''')
