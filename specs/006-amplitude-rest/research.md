# Research: Amplitude 서버 고정 인증

NEEDS CLARIFICATION은 없다.

## R1. 인증 경로 (ADR-34)

- 사실(2026-10-17 운영 확인, PRD 2절):
  - MCP OAuth 토큰은 만료 24시간이고 갱신 토큰이 비어 있다. 서버에서 무인 재승인은 불가능하다.
  - Dashboard REST·Taxonomy API는 프로젝트 API 키 + 시크릿 키 Basic 인증이고 키 만료가 없다.
  - 형제 레포가 같은 프로젝트에서 운영 중이다.
- Decision: REST로 바꾸고 MCP 코드를 제거한다. 환경 변수는 다음 셋이다.

  | 이름 | 보관 | 예시 |
  |---|---|---|
  | `AMPLITUDE_API_KEY` | GitHub Secrets | (값 없음) |
  | `AMPLITUDE_SECRET_KEY` | GitHub Secrets | (값 없음) |
  | `AMPLITUDE_REST_BASE` | Variables(선택) | 기본 `https://amplitude.com`. EU는 `https://analytics.eu.amplitude.com` |

  `AMPLITUDE_MCP_URL`·`AMPLITUDE_TOOLS`는 삭제한다.
- 둘 중 하나라도 비면 "키 없음"이다. 키는 `httpx.BasicAuth(api_key, secret_key)`로만 쓰며 로그 포맷·예외 메시지에 넣지 않는다.
- Alternatives considered:
  - MCP 유지 + 매일 재승인: PRD가 없애려는 작업 그대로다.
  - MCP 서비스 계정: 존재 미확인이고 문의가 필요하다. 사용자 지시가 중간 확인 없이 진행이라 열린 질문으로 남긴다.
  - 두 경로 공존: 유지 비용이 두 배다(PRD 6.2).

## R2. 도구 인자 (ADR-35)

- 근거:
  - 운영 3일 Amplitude 호출 102건은 `query_amplitude_data` 86건과 `get_amplitude_context` 16건이었다. 실패 17건은 모두 차트 정의·프로젝트 ID 추측 오류였다.
  - 인자를 구조화하면 정의 오류를 조회 전에 잡을 수 있다.
- Decision: [contracts/amplitude-tools.md](./contracts/amplitude-tools.md) 1·2절.
  - 하나의 `kind` 인자로 REST 세 엔드포인트를 고른다. 이벤트는 `{event_type, filters[]}`이고, 기간은 90일 상한이다.
  - 세그멘테이션 `n`은 `any|active`, 퍼널 `n`은 `new|active`다. `ce:` 접두어는 그대로 통과시킨다.
  - 종류에 맞지 않는 인자는 오류다. Pydantic 모델로 검증하고, 실패하면 `인자 오류: …`를 돌려준다.
- Rationale: 종류를 한 도구에 모으면 모델이 고를 도구가 줄고 운영 호출 형태(차트 하나)와 비슷하다. 맞지 않는 인자를 무시하면 모델이 원하던 조회와 다른 결과를 근거로 쓸 수 있어 거절한다.
- 인자 표현력 가정: 운영 86건의 차트 유형이 세그멘테이션·퍼널·리텐션 안이었으므로 덮인다고 본다(PRD 6.4). 실제 키로 같은 유형 질문을 다시 해 확인한다(T015, 미검증·사람).

## R3. 결과 압축 (ADR-35)

- Decision: 형제 레포 `amp.py`의 `series_table`·`funnel_table`·`retention_table`·`_guard`·`_labels`·`_summary` 구조를 옮겨 다듬는다.
  - 빼는 것: 차트 dict(이 앱은 모델이 `chart` 블록을 쓴다), 모듈 전역 키.
  - 유지하는 것: 31행 상한, 1단계 표본 30 미만 경고, 리텐션 D0~D14 표와 combined 요약.
  - 덧붙이는 것: 전체 문자열에 기존 `clip()`.
- Rationale: 같은 프로젝트 데이터로 운영 검증된 모양이라 다시 설계하지 않는다. 복사가 아니라 옮겨 고치는 이유는 날짜 형식(`YYYY-MM-DD` 입력 → REST `YYYYMMDD`), 도구 인자 구조, 오류 분류가 다르기 때문이다.
- 캐시: `(path, params)` 키, 프로세스 메모리, 15분. 지표·맥락·사전 점검이 같은 캐시를 쓴다. `ponytail:` 주석으로 "단일 워커 전제, 여러 워커면 공유 캐시"를 남긴다.

## R4. 이벤트 맥락 병합 (ADR-35)

- Decision: Taxonomy API 이벤트 목록과 업로드 택사노미(`app_settings.taxonomy`)를 이름으로 합친다. 설명은 업로드 쪽이 우선이고, 출처를 `양쪽`·`Amplitude에만`·`택사노미에만`으로 표시한다. 속성은 Taxonomy 이벤트 속성 + 사용자 속성 이름 목록에, 업로드 쪽 속성 설명을 붙인다.
- Rationale: 이벤트 의미(택사노미)와 실제 수집 이벤트(Amplitude)의 차이가 기획 판단의 근거가 된다(상위 PRD의 세 소스 종합).

## R5. 사전 점검·건너뛰기·상태 기록 (ADR-36)

- 사전 점검: `conversations.py` 메시지 POST에서 `budget.check()` 직후, 실제 모드이고 `skipAmplitude`가 아닐 때 `amplitude.preflight()`를 부른다.
  - 실패 처리: 실패하면 `ApiError(503, "AMPLITUDE_UNAVAILABLE", 메시지)`이고 사용자 메시지를 저장하지 않는다(계약 v1.5).
  - 호출: `GET /api/2/taxonomy/event` 1회이며 캐시 적중이면 0회다.
- 건너뛰기: `skipAmplitude: true`면 Amplitude 도구를 주지 않고, 시스템 프롬프트 상태 문구를 "Amplitude 없음(사용자가 건너뜀)"으로 둔다. 기존 규칙 5("상태가 '없음'이면 content에 빠진 근거를 명시")가 그대로 적용된다.
- 상태 값:
  - `used`: 사전 점검 통과.
  - `skipped`: `skipAmplitude`.
  - `unavailable`: 실행 중 Amplitude 도구가 401·403을 받음.
  - `NULL`: 시연 모드, 사용자 메시지, 이전 행.
- 마이그레이션(ADR-29 패턴, `db.init()`):
  - `information_schema.COLUMNS`에 `messages.amplitude_status`가 없을 때만 `ALTER TABLE messages ADD COLUMN amplitude_status ENUM('used','unavailable','skipped') NULL`.
  - 새 DB는 `schema.sql`에 컬럼이 있다.
  - 이어서 `DELETE FROM app_settings WHERE k IN ('amplitude','amplitude_oauth')`(이전 토큰 제거, 멱등).
- 조회 한 줄:
  ```sql
  SELECT amplitude_status, COUNT(*) AS n FROM messages WHERE role = 'assistant' AND status = 'completed' AND amplitude_status IS NOT NULL GROUP BY amplitude_status;
  ```

## R6. 시스템 프롬프트 (ADR-36)

- 규칙 7(조회만)은 유지하고 도구 이름만 바꾼다.
- 규칙 8(MCP 전용 문구 `timeSeriesLimit`·`groupByLimit`·`includeAdditionalInfo`)은 아래 문장으로 바꾼다.
  > Amplitude 조회는 필요한 범위만 요청한다. 기간은 90일 이내로 질문에 필요한 만큼만, 31일을 넘으면 interval은 7 이상, group_by는 꼭 필요할 때만 쓴다. 이벤트 이름은 amplitude_context나 택사노미에서 확인한 실제 이름만 쓰고(커스텀 이벤트는 ce: 접두어), 세그멘테이션의 n은 any·active, new는 퍼널에서만 쓴다.
- 상태 문구(시스템 프롬프트 끝, 기존 "있음/없음" 표기 유지): `Amplitude 있음` | `Amplitude 없음(사용자가 건너뜀)` | `Amplitude 없음(키 없음)`. 마지막은 시연 모드에서만 나올 수 있다(실제 모드는 사전 점검이 막는다). 이전의 `없음(연결 실패)`·`없음(허용 목록 불일치)`는 사라진다.
