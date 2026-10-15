# Research: 질문 마법사

NEEDS CLARIFICATION은 없다. 이 문서는 모델 선택과 비교 방법(R1), 비용·지연 추정(R2), 선택 기록 방식(R3), 마이그레이션(R4), 입력 조립(R5)을 다룬다.

## R1. 다듬기 모델과 비교 방법 (ADR-28)

- Decision: `REFINE_MODEL`을 쓰고, 비어 있으면 `CODE_SUMMARY_MODEL`(현재 `anthropic:claude-haiku-5-5`)을 쓴다. 접두사 규칙(ADR-20)으로 런타임을 고르며, 잘못된 접두사는 기동 실패다. 확정은 샘플 10건 비교로 한다(PRD 6.3 사용자 결정).
- **비교 방법**(T024·T025):
  - 샘플: `backend/checks/compare_refine.py`에 10건을 고정한다. 유형은 일상어 이탈 질문 2, 기간 없는 지표 질문 2, 측정 설계 요청 2, 후속 질문(직전 대화 포함) 2, 이미 구체적인 질문 1, 택사노미에 없는 대상 1이다.
  - 실행: 같은 입력(택사노미 이름·이력 포함)을 `anthropic:claude-haiku-5-5`와 `anthropic:claude-sonnet-5-5`로 다듬어 `_workspace/06_refine_model_comparison.md`에 나란히 쓴다. 각 결과의 지연(초)과 비용도 함께 쓴다.
  - 채점: QA가 네 항목(의도 보존, 실제 이벤트 이름 사용, 기간과 지표 명시, 문장 자연스러움)을 각 0~2점으로 채점한다. 한 건 최대 8점, 모델당 최대 80점이다.
- **결정 규칙**: Sonnet 합계가 Haiku보다 8점(10%) 이상 높거나, Haiku가 "의도 보존"에서 0점을 2건 이상 받으면 Sonnet이다. 아니면 Haiku다. 결정은 `REFINE_MODEL` 값으로 반영한다. 운영 Variables와 env 예시다.
- Rationale: 사람이 보는 품질 차이가 작으면 20배 싼 모델이 맞다. 의도 보존 실패는 기능 신뢰를 깨므로 별도 거부 조건으로 둔다.
- Alternatives considered: LLM 판정자 채점(사용자가 사람 채점을 지정), Sonnet 고정(근거 없음).

## R2. 비용과 지연 추정 (SC-001, SC-004)

- 입력: 시스템 규칙 약 600토큰, 택사노미 이름 45개 약 400토큰, 이력 4개 × 500자 약 800토큰, 질문 약 100토큰을 합쳐 약 1.9k 토큰이다. 출력은 구조화 JSON과 사고를 합쳐 약 300토큰(effort `low`)이다.
- 비용(2026-10-06 단가표, claude-api 스킬):

  | 모델 | 단가(입력/출력, 1M) | 1회 추정 | 질문 1회(실측 $1.60) 대비 |
  |---|---|---|---|
  | Haiku 5.5 | $0.10/$0.50 | 약 $0.0003 | 0.02% |
  | Sonnet 5.5 | $2/$10 | 약 $0.007 | 0.4% |

  둘 다 SC-004(1%)를 만족한다.
- 지연: 출력이 짧고 effort `low`라 수 초 안으로 본다. 비교표의 실측 지연으로 SC-001을 확인한다.
- 설정: Anthropic 런타임은 `output_config={"effort": "low"}`와 구조화 출력(`output_format=RefineResult`)이다. `thinking`은 생략한다(현행 모델 기본 adaptive). 강제 `tool_choice`는 쓰지 않는다(도구 없음). `stop_reason == "refusal"`이면 `UPSTREAM_ERROR`다.

## R3. 선택 기록 방식

- Decision: 별도 엔드포인트 `POST /api/questions/refine/{refinementId}/choice`(계약 v1.3)다. 프론트는 카드가 닫히는 순간 한 번 부르며 결과를 기다리지 않는다.
- Rationale: "취소"(ESC·닫기)는 메시지를 보내지 않아, 메시지 전송 본문에 `refinementId`·`choice`를 싣는 방식으로는 기록할 수 없다. "입력창에 넣기"는 클릭이 아니라 그 뒤 실제 전송 때 `refined`, 전송 없이 입력을 비우거나 대화를 떠나면 `cancelled`로 기록한다(PRD 3차). 기존 메시지 전송 계약을 건드리지 않는다.
- Alternatives considered: 메시지 전송에 동반(취소 누락, 기존 계약 변경), 다듬기 응답 후 서버가 다음 메시지와 자동 대조(추측이 들어감).

## R4. `llm_usage.purpose` ENUM 마이그레이션 (ADR-29)

- 사실: 스키마는 기동 시 `schema.sql`의 `CREATE TABLE IF NOT EXISTS`만 실행해 기존 테이블의 ENUM은 바뀌지 않는다. 운영 DB 계정은 해당 DB에 ALL 권한이 있다(`deploy/mysql-init.sql`).
- Decision: `db.init()`이 `schema.sql` 실행 뒤 `information_schema.COLUMNS`에서 `llm_usage.purpose`의 `COLUMN_TYPE`을 읽는다. `'refine'`이 없을 때만 다음을 실행한다.
  ```sql
  ALTER TABLE llm_usage MODIFY purpose ENUM('agent','code_summary','refine') NOT NULL
  ```
  새 DB는 `schema.sql`에 이미 `refine`이 있어 건너뛴다. 앱은 `init()`이 끝난 뒤에 요청을 받으므로 "앱 갱신보다 먼저"가 지켜진다. 이전 버전 앱은 `refine`을 쓰지 않아 순서 문제가 없다.
- 멱등성: 두 번 실행해도 두 번째는 조건에서 걸러진다(check_b10이 `init()` 두 번 호출로 확인).
- Alternatives considered: Alembic(테이블 6개짜리 프로토타입에 과함), 배포 스크립트의 수동 SQL(잊기 쉬움), 용도 컬럼을 VARCHAR로 변경(기존 행 의미 검증이 사라짐).

## R5. 입력 조립 (ADR-30)

- 택사노미: `app_settings`의 `taxonomy` 값에서 `events[].name`만 뽑아 쉼표로 잇는다. 없으면 "택사노미 없음"이라고 쓴다. 4,000자를 넘을 때만 고르는 순서를 바꾼다. 질문과 겹치는 이름(이름 전체가 질문에 들어 있거나, 이름을 `_`로 나눈 조각 하나가 질문의 영숫자 낱말(소문자)과 같음)을 원래 순서대로 먼저 넣는다. 남은 자리는 나머지 이름을 원래 순서대로 4,000자 안에서 채운다. 잘렸다는 표시를 돌려주면 엔드포인트가 요약 끝에 고정 문구를 붙인다(계약 v1.3). 모델은 잘림을 알 수 없으므로 서버가 붙인다. 질문과 겹치는 이름을 먼저 넣는 이유는 질문이 가리키는 이벤트가 잘려 나가지 않게 하기 위해서다.
- 이력: `messages`에서 해당 대화의 `status = 'completed'`이고 `content`가 빈 문자열이 아닌 행을 최근순으로 고른다. 사용자 2개, 에이전트 2개이고, 각 `content` 앞 500자다. 오래된 순으로 다시 정렬해 넣는다. `conversationId`가 `null`이면 이력 없음이다.
- 출력 검증: `RefineResult`(Pydantic)다. `refined` 1~4000자, `summary` 1~300자이고, 벗어나면 502 `UPSTREAM_ERROR`(자르지 않음)다. "두 문장 이내"는 프롬프트 규칙으로만 두고 검증하지 않는다(문장 분리 규칙이 불안정하다). 비교표에서 위반을 본다.
