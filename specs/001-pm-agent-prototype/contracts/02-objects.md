## 공통 객체

### ConversationSummary
```json
{
  "id": 7,
  "title": "스캔 퍼널 이탈 지점 개선안",
  "createdAt": "2026-10-15T09:12:03.418Z",
  "updatedAt": "2026-10-15T09:14:41.022Z",
  "messageCount": 2,
  "proposalCount": 2,
  "adoptedCount": 1
}
```
- `title`: 생성 시 지정하지 않으면 `null`. 첫 사용자 메시지가 저장될 때 앞 40자로 채운다.

### Message
```json
{
  "id": 42,
  "conversationId": 7,
  "role": "assistant",
  "status": "completed",
  "content": "지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다. 실패의 62%가 OCR 실패이고, 실패 화면에 재시도 동작이 없습니다. 아래 두 제안을 확인해 주세요.",
  "errorCode": null,
  "toolCalls": [
    {
      "id": 301,
      "seq": 1,
      "source": "amplitude",
      "name": "query_funnel",
      "input": {"events": ["scan_start", "scan_complete"], "start": "2026-09-15", "end": "2026-10-14"},
      "status": "succeeded",
      "resultSummary": "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%",
      "durationMs": 2310,
      "startedAt": "2026-10-15T09:12:05.101Z"
    },
    {
      "id": 302,
      "seq": 2,
      "source": "code",
      "name": "find_event_calls",
      "input": {"eventName": "scan_complete"},
      "status": "succeeded",
      "resultSummary": "2곳: src/app/scan.tsx:405 (실패), src/app/scan.tsx:427 (성공)",
      "durationMs": 14,
      "startedAt": "2026-10-15T09:12:08.550Z"
    }
  ],
  "proposals": [],
  "usage": {
    "model": "anthropic:claude-sonnet-5-5",
    "inputTokens": 18432,
    "outputTokens": 2210,
    "costUsd": 0.0884
  },
  "createdAt": "2026-10-15T09:12:04.002Z"
}
```
- `role`: `"user"` | `"assistant"`.
- `status`: `"running"` | `"completed"` | `"failed"`. user 메시지는 항상 `"completed"`.
- `errorCode`: `status`가 `"failed"`일 때 에러 코드 문자열, 아니면 `null`.
- user 메시지는 `toolCalls: []`, `proposals: []`, `usage: null`.
- `status`가 `"running"`인 assistant 메시지(실행 중 상세 조회)는 `content: ""`, `proposals: []`, `usage: null`이고 `toolCalls`에는 그때까지 저장된 호출이 들어간다.
- `content`: 마크다운 문자열. **제안 내용을 여기에 섞지 않는다.** 제안은 `proposals`에만 있다.
- `toolCalls`는 `seq` 오름차순. `source`: `"amplitude"` | `"code"` | `"taxonomy"`. `status`: `"running"` | `"succeeded"` | `"failed"`. `name`은 도구 이름 그대로(Amplitude MCP 도구명은 MCP 서버가 정한 이름). `resultSummary`는 최대 500자, `running`이면 `null`. `durationMs`는 `running`이면 `null`.
- 위 예시의 `proposals`는 지면상 비웠다. 실제 완료 메시지에는 아래 Proposal이 0개 이상 들어간다.

### Proposal
```json
{
  "id": 15,
  "conversationId": 7,
  "messageId": 42,
  "seq": 1,
  "type": "funnel_design",
  "title": "스캔 실패 후 재시도 퍼널 측정 설계",
  "evidence": [
    {
      "kind": "metric",
      "summary": "최근 30일 scan_start 대비 성공한 scan_complete 전환율이 41.3%다.",
      "value": "41.3%",
      "source": "Amplitude funnel: scan_start → scan_complete(success=true), 2026-09-15~2026-10-14"
    },
    {
      "kind": "code",
      "summary": "실패 시 scan_complete를 success=false로 보내고 끝나며, 재시도 버튼 핸들러에는 이벤트가 없다.",
      "file": "src/app/scan.tsx",
      "function": "onScanFailed",
      "line": 405,
      "snippet": "track(EVENTS.scan_complete, { success: false, fail_reason: reason, item_count: 0, degraded: false });"
    },
    {
      "kind": "taxonomy",
      "summary": "scan_complete는 성공·실패를 success 속성으로 구분한다.",
      "eventName": "scan_complete"
    }
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
    "baseline": null,
    "target": "35%",
    "funnel": [
      {"order": 1, "eventName": "scan_complete", "status": "existing", "condition": "success=false", "location": null, "properties": []},
      {"order": 2, "eventName": "scan_retry_tap", "status": "new", "condition": null, "location": {"file": "src/app/scan.tsx", "function": "handleRetry", "line": 398}, "properties": [{"name": "fail_reason", "type": "string"}]},
      {"order": 3, "eventName": "scan_complete", "status": "existing", "condition": "success=true", "location": null, "properties": []}
    ]
  },
  "decision": {
    "status": "adopted",
    "note": "KB-812로 이번 스프린트에 진행",
    "decidedAt": "2026-10-15T09:20:11.730Z"
  },
  "createdAt": "2026-10-15T09:14:40.990Z"
}
```

필드 규칙:
- `type`: `"improvement"`(세그먼트 A, 기획 개선) | `"funnel_design"`(세그먼트 B, 측정 설계).
- 카드 네 영역은 정확히 이 순서다: `evidence` → `proposal` → `steps` → `measurement`.
- `evidence`: 1개 이상. `kind`별 필드가 다르고, 다른 kind의 필드는 **보내지 않는다**(TS 판별 유니온).
  - `"metric"`: `summary`, `value`(문자열, 단위 포함), `source`
  - `"code"`: `summary`, `file`(저장소 루트 기준 상대 경로), `function`(감싸는 함수·컴포넌트 이름, 최상위 코드면 `null`), `line`(1부터), `snippet`(최대 10줄)
  - `"taxonomy"`: `summary`, `eventName`
- `proposal`: 문자열. `steps`: 문자열 배열, 1개 이상, 실행 순서대로.
- `measurement`:
  - `primaryMetric`: 문자열, 필수.
  - `baseline`, `target`: 문자열 또는 `null`.
  - `funnel`: 배열. `funnel_design`이면 1개 이상 필수. `improvement`면 빈 배열 가능.
  - funnel 단계: `order`(1부터 연속), `eventName`, `status`(`"existing"` | `"new"`), `condition`(문자열 또는 `null`), `location`, `properties`.
  - `status`가 `"new"`면 `location`(`file`, `function`, `line`) 필수, `"existing"`이면 `location: null`. `location.line`은 `null` 가능(함수만 특정될 때).
  - `properties`: 신규 이벤트에 붙일 속성 `[{name, type}]`. `type`은 `"string"` | `"number"` | `"boolean"`. 기존 이벤트는 빈 배열.
- `decision.status`: `"pending"` | `"adopted"` | `"on_hold"`. 생성 시 `"pending"`, `note: null`, `decidedAt: null`. `decidedAt`은 status가 바뀔 때마다 갱신되고 `"pending"`으로 돌리면 `null`.

### Settings
```json
{
  "repository": {
    "url": "https://github.com/team-skyjs/kbap-fe",
    "branch": "develop",
    "headCommit": "9f3c2a1",
    "codeMapCommit": "9f3c2a1",
    "codeMapStatus": "ready",
    "trackedEventCount": 87,
    "screenCount": 41,
    "syncedAt": "2026-10-15T08:55:02.117Z",
    "lastError": null
  },
  "taxonomy": {
    "eventCount": 64,
    "uploadedAt": "2026-10-14T12:01:44.500Z"
  },
  "amplitude": {
    "status": "connected",
    "serverUrl": "https://mcp.amplitude.com/mcp",
    "connectedAt": "2026-10-14T12:10:09.031Z"
  },
  "models": {
    "agent": "anthropic:claude-sonnet-5-5",
    "codeSummary": "anthropic:claude-haiku-5-5"
  },
  "agentMode": "real",
  "budget": {
    "limitUsd": 200.0,
    "spentUsd": 3.4172
  }
}
```
- `repository`: 미등록이면 `null`. `headCommit`, `codeMapCommit`은 7자리 짧은 SHA. `codeMapStatus`: `"none"` | `"building"` | `"ready"` | `"failed"`. 요약 생성 전 `codeMapCommit`은 `null`. `lastError`: 마지막 동기화·요약이 실패했으면 사유 문장(예: `"GitHub 인증 실패: GITHUB_TOKEN이 없거나 만료되었습니다."`), 성공하면 `null`. 토큰 값은 넣지 않는다.
- `taxonomy`: 미업로드면 `null`.
- `amplitude.status`: `"connected"` | `"disconnected"`. 끊겼으면 `connectedAt: null`.
- `agentMode`: `"real"` | `"fake"`.
- 저장소·택사노미·Amplitude가 비어 있어도 대화는 가능하다. 에이전트는 쓸 수 있는 도구만으로 답한다.

