# Data Model: PM Agent 프로토타입

출처: ADR-8(스키마 뼈대), 계약서 v1.1 `contracts/02-objects.md`(API shape). 이 문서는 둘을 잇는 매핑이다. 컬럼 타입의 세부(길이·인덱스)는 `backend/schema.sql`에서 확정하되, 아래 제약은 바꾸지 않는다.

공통: 문자셋 `utf8mb4`. 시각은 UTC `DATETIME(3)`이고 API에서 `...Z` ISO 8601로 직렬화한다. PK는 `BIGINT AUTO_INCREMENT`이고 API에서 number다. DB는 snake_case, API는 camelCase다.

## 엔터티와 테이블

### Conversation → `conversations`
| 컬럼 | 타입 | 제약 | API 필드 |
|---|---|---|---|
| id | BIGINT PK | | `id` |
| title | VARCHAR(200) | NULL 허용. 첫 user 메시지 저장 시 null이면 앞 40자로 채움 | `title` |
| created_at, updated_at | DATETIME(3) | updated_at은 메시지 추가·제안 결정 시 갱신 | `createdAt`, `updatedAt` |

파생 필드(`messageCount`, `proposalCount`, `adoptedCount`)는 저장하지 않고 조회 시 집계한다.

### Message → `messages`
| 컬럼 | 타입 | 제약 | API 필드 |
|---|---|---|---|
| conversation_id | BIGINT FK → conversations ON DELETE CASCADE | | `conversationId` |
| role | ENUM('user','assistant') | | `role` |
| status | ENUM('running','completed','failed') | user는 항상 completed | `status` |
| content | MEDIUMTEXT | 제안 내용을 섞지 않는다(FR-002). running 동안 빈 문자열 | `content` |
| error_code | VARCHAR(50) NULL | status=failed일 때만 값 | `errorCode` |
| created_at | DATETIME(3) | 대화 내 정렬 기준 | `createdAt` |

`usage`는 `llm_usage`에서 `message_id`로 합산한다(조사·종합 두 단계의 토큰·비용 합). `model`은 그 메시지에 종합 단계(`purpose=synthesis`)가 있으면 종합 모델, 없으면 조사 모델(`purpose=agent`)이다(ADR-21). user 메시지는 `null`이다.

상태 전이: `running → completed`(final 이벤트) 또는 `running → failed`(error 이벤트, 클라이언트 끊김). 역전이는 없다. 한 대화에 running은 최대 1개다(`RUN_IN_PROGRESS`).

### ToolCall → `tool_calls`
| 컬럼 | 타입 | 제약 | API 필드 |
|---|---|---|---|
| message_id | BIGINT FK → messages CASCADE | | (중첩) |
| seq | INT | 메시지 내 1부터 연속 | `seq` |
| source | ENUM('amplitude','code','taxonomy') | | `source` |
| name | VARCHAR(100) | 도구 이름 그대로 | `name` |
| input_json | JSON | | `input` |
| status | ENUM('running','succeeded','failed') | | `status` |
| result_summary | VARCHAR(1000) | API로는 최대 500자, running이면 NULL | `resultSummary` |
| result_text | MEDIUMTEXT | 원문(LLM에 준 결과). API로 내보내지 않음 | — |
| duration_ms | INT NULL | running이면 NULL | `durationMs` |
| started_at | DATETIME(3) | | `startedAt` |

명세 Key Entity의 "비용"은 도구 단위가 아니라 메시지 단위 `usage`로 집계한다. grep·인덱스 도구는 0원이고, LLM 비용은 에이전트 호출 단위로 생기기 때문이다.

### Proposal → `proposals`
| 컬럼 | 타입 | 제약 | API 필드 |
|---|---|---|---|
| message_id, conversation_id | BIGINT FK CASCADE | | `messageId`, `conversationId` |
| seq | INT | 메시지 내 1부터 | `seq` |
| type | ENUM('improvement','funnel_design') | | `type` |
| title | VARCHAR(200) | | `title` |
| evidence_json | JSON | 1개 이상. Evidence 판별 유니온 | `evidence` |
| proposal_text | TEXT | | `proposal` |
| steps_json | JSON | 문자열 배열, 1개 이상 | `steps` |
| measurement_json | JSON | Measurement 객체 | `measurement` |
| decision_status | ENUM('pending','adopted','on_hold') DEFAULT 'pending' | | `decision.status` |
| decision_note | TEXT NULL | 최대 1000자 | `decision.note` |
| decided_at | DATETIME(3) NULL | status 변경마다 갱신, pending이면 NULL | `decision.decidedAt` |
| created_at | DATETIME(3) | | `createdAt` |

JSON 컬럼 내부 구조(계약서 Proposal 규칙과 동일):
- **Evidence** `kind`별 필드:
  - `metric`: `{summary, value, source}`
  - `code`: `{summary, file, function, line, snippet}`. `function`은 null 가능, snippet은 최대 10줄.
  - `taxonomy`: `{summary, eventName}`
  - 다른 kind의 키는 저장하지 않는다.
- **Measurement**: `{primaryMetric, baseline|null, target|null, funnel[]}`. `funnel_design`이면 funnel이 1개 이상이다.
- **FunnelStep**: `{order, eventName, status, condition|null, location|null, properties[]}`.
  - `order`는 1부터 연속이다.
  - `status`가 `"new"`면 `location{file, function, line|null}`이 필수다. `"existing"`이면 `location`은 null이다.
  - `properties`의 원소는 `{name, type}`이고 `type`은 `"string"` | `"number"` | `"boolean"`이다.

검증 위치: 에이전트 최종 응답의 Pydantic 모델(`AgentAnswer`)에서 강제한다. 위반하면 저장하지 않고 모델에 재시도를 시키거나 실패 처리한다.

상태 전이: `pending ⇄ adopted ⇄ on_hold`. 어느 방향이든 PATCH로 바꿀 수 있다.

### LlmUsage → `llm_usage`
| 컬럼 | 타입 | 제약 |
|---|---|---|
| message_id | BIGINT NULL FK → messages ON DELETE SET NULL | 코드 요약은 NULL |
| purpose | ENUM('agent','synthesis','code_summary') | `agent`=조사 단계(도구 루프), `synthesis`=종합 단계(ADR-21), `code_summary`=코드 요약. 기존 값은 그대로라 이관이 없다. `schema.sql`은 `ALTER TABLE llm_usage MODIFY purpose ENUM('agent','synthesis','code_summary') NOT NULL`을 추가한다 |
| model | VARCHAR(100) | `AGENT_MODEL`·`CODE_SUMMARY_MODEL` 문자열 그대로(`provider:model`, ADR-20) |
| input_tokens, output_tokens | INT | |
| cost_usd | DECIMAL(10,4) | 설정 단가표로 계산. fake 모드도 행을 남기되 토큰 0·`cost_usd` 0(계약: fake `usage.costUsd`는 `0`, usage는 이 테이블 합산) |
| created_at | DATETIME(3) | |

`SUM(cost_usd)`가 `settings.budget.spentUsd`다. 이 값이 `LLM_BUDGET_USD` 이상이면 새 메시지와 코드 요약을 거절한다.

### Settings·Taxonomy·OAuth → `app_settings` (k/v JSON)
| k | v 구조 | API 노출 |
|---|---|---|
| `repository` | `{url, branch, headCommit, codeMapCommit, codeMapStatus, trackedEventCount, screenCount, syncedAt, lastError}` | `settings.repository` 그대로 |
| `taxonomy` | `{events: [...], uploadedAt}` (업로드 본문 그대로) | `settings.taxonomy = {eventCount, uploadedAt}` |
| `amplitude_oauth` | MCP SDK 토큰·클라이언트 정보 | `settings.amplitude.status/connectedAt`만. 토큰은 노출 금지 |

`models`, `agentMode`, `budget.limitUsd`는 환경변수에서 읽고 저장하지 않는다.

택사노미 검증 규칙(US4-4):
- `events`가 1개 이상이고 `name`이 필수이며 중복되지 않는다.
- 속성 `type`은 3종 중 하나다.
- 하나라도 실패하면 기존 값을 유지하고 `VALIDATION_ERROR`를 낸다. `message`에 첫 위반 위치(`events[3].properties[0].type`)를 적는다.

## 비영속 데이터

- **코드 인덱스**: 이벤트명 → `[{file, line, function}]`. 동기화마다 rg로 재생성한다(0원). 저장 매체는 위임.
- **화면 요약 캐시**: 키는 `(file path, git blob SHA)`이고 값은 150단어 요약이다. 저장 매체는 위임하되 컨테이너 재시작 후에도 남아야 한다(DB 또는 `/data` 볼륨).
