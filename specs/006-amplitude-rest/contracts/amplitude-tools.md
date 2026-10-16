# Amplitude 도구 형식 (에이전트 ↔ 백엔드 내부)

API 계약이 아니다. 에이전트(모델)가 부르는 내부 도구 두 개의 인자와 결과 형식이다. 구현(`backend/app/amplitude.py`)과 검사(`backend/checks/check_b12.py`), 시스템 프롬프트 규칙 8이 이 파일 하나를 기준으로 한다. 도구 호출은 기존처럼 `tool_calls`에 `source: "amplitude"`로 남는다.

## 1. `amplitude_query` — 지표 조회

### 인자

```json
{
  "kind": "funnel",
  "events": [
    {"event_type": "scan_start", "filters": []},
    {"event_type": "scan_complete", "filters": [{"subprop_type": "event", "subprop_key": "success", "subprop_op": "is", "subprop_value": ["true"]}]}
  ],
  "start": "2026-10-01",
  "end": "2026-10-14",
  "n": "active",
  "conversion_window_seconds": 86400
}
```

| 인자 | 타입 | 적용 | 규칙 |
|---|---|---|---|
| `kind` | `"segmentation"` \| `"funnel"` \| `"retention"` | 전부 | 필수 |
| `events` | `[{event_type, filters}]` | 전부 | 세그멘테이션 1~2개, 퍼널 2~10개, 리텐션 정확히 2개(시작 이벤트, 복귀 이벤트). `event_type`은 실제 이벤트 이름이고, 커스텀 이벤트는 `ce:이름`을 그대로 쓴다. `filters`는 생략하면 `[]`다 |
| `events[].filters[]` | `{subprop_type, subprop_key, subprop_op, subprop_value}` | 전부 | `subprop_type`: `"event"` \| `"user"`. `subprop_op`: `"is"`, `"is not"`, `"contains"`, `"does not contain"`, `"less"`, `"less or equal"`, `"greater"`, `"greater or equal"`. `subprop_value`: 문자열 배열, 1개 이상 |
| `start`, `end` | `"YYYY-MM-DD"` | 전부 | 필수, `start ≤ end`, 기간(양 끝 포함) 1~90일 |
| `metric` | `"uniques"` \| `"totals"` \| `"avg"` \| `"pct_dau"` \| `"formula"` | 세그멘테이션 | 기본 `"uniques"` |
| `formula` | string | 세그멘테이션 + `metric: "formula"` | 그때만 필수(예: `"UNIQUES(A)/UNIQUES(B)"`, A·B는 `events` 순서) |
| `interval` | `1` \| `7` \| `30` | 세그멘테이션, 리텐션 | 기본 `1`. 기간이 31일을 넘으면 7 이상을 권장(행 상한) |
| `group_by` | string | 세그멘테이션, 퍼널 | 속성 이름 하나(사용자 속성 그대로, 커스텀 사용자 속성은 `gp:이름`). 생략 가능 |
| `n` | `"any"` \| `"active"` \| `"new"` | 세그멘테이션: `any`·`active`(기본 `any`), 퍼널: `new`·`active`(기본 `active`) | 리텐션에는 주지 않는다 |
| `conversion_window_seconds` | int | 퍼널 | 1~7,776,000(90일), 기본 2,592,000(30일) |

종류에 맞지 않는 인자(예: 퍼널에 `metric`, 세그멘테이션에 `n: "new"`)는 **무시하지 않고 인자 오류**다. 모델 실수를 조용히 넘기지 않기 위해서다.

### REST 대응 (조회 전용)

| `kind` | 경로 | 주요 매개변수 |
|---|---|---|
| segmentation | `GET /api/2/events/segmentation` | `e`(첫 이벤트 JSON), `e2`(둘째), `m`, `formula`, `start`·`end`(`YYYYMMDD`), `i`, `g`, `n` |
| funnel | `GET /api/2/funnels` | `e`(이벤트마다 반복), `start`·`end`, `n`, `cs`, `g` |
| retention | `GET /api/2/retention` | `se`(시작), `re`(복귀), `start`·`end`, `i` |

`event_type`과 `filters`는 이벤트 JSON에 그대로 들어간다.

### 결과 (모델에게 주는 문자열)

성공하면 도구 결과는 아래 형식의 표 하나다. 전체 문자열에는 기존 `clip()` 상한이 적용된다.

- **세그멘테이션**: 제목 줄 `**{kind} {이벤트들} {start}~{end} ({행 수} rows × {시리즈 수} series)**`, `| date | 시리즈... |` 표(최대 31행, 넘으면 "… N rows 생략" 한 줄), 끝에 `요약:` 줄(시리즈별 합·평균·최대(날짜)·최소·마지막·0인 날 수, 최대 6개 시리즈).
- **퍼널**: `| step | event | users | conv% | step conv% |` 표다. `group_by`가 있으면 `| segment | 단계별 users (conv%) |` 표(최대 31행)다. 1단계 사용자가 30 미만이면 `⚠ 1단계 표본 {n}명 (<30) — 비율 해석 불가, 절대수로 보고` 한 줄을 붙인다.
- **리텐션**: `| cohort (n) | D0 … D14 |` 표(최근 코호트부터, 표본 0 코호트 생략, 최대 31행)와 `합산(combined):` 줄(D0, D1, D2, D3, D7, D14, D30 중 있는 칸)이다.

### 실패 (도구 실패로 반환, 실행은 계속)

| 상황 | 결과 문자열 앞부분 | 실행 상태 영향 |
|---|---|---|
| 인자 규칙 위반 | `인자 오류: {이유}` (Amplitude 호출 없음) | 없음 |
| Amplitude 400 | `Amplitude 인자 오류: {본문 앞 300자}` | 없음 |
| 401·403 | `Amplitude 인증 실패` | 그 실행의 상태가 `unavailable` |
| 429 | `Amplitude 요청 한도 초과(잠시 후 다시)` | 없음 |
| 네트워크·5xx | `Amplitude 연결 실패` | 없음 |

## 2. `amplitude_context` — 이벤트 맥락

### 인자

```json
{"event_type": "scan_complete"}
```

- `event_type`: 생략하면 이벤트 목록, 주면 그 이벤트의 속성 목록이다.

### 결과

- **목록** (`GET /api/2/taxonomy/event`): `| event | category | 설명 | 출처 |` 표다.
  - 설명은 업로드한 택사노미(`app_settings.taxonomy`)의 `description`이 있으면 그것을, 없으면 Amplitude의 설명을 쓴다.
  - 출처는 `양쪽`·`Amplitude에만`·`택사노미에만`이다.
  - 커스텀 이벤트는 이름 앞에 `ce:`를 붙여 보여 준다.
- **속성** (`GET /api/2/taxonomy/event-property?event_type=…`, `GET /api/2/taxonomy/user-property`): 이벤트 속성 표 `| property | type | 설명 |`와 사용자 속성 이름 목록 한 줄이다. 설명은 택사노미 우선이다.
- 두 결과 모두 15분 캐시를 쓰고 `clip()`을 적용한다. 실패 형식은 1절 표와 같다.

## 3. 사전 점검

메시지 전송 사전 점검은 `GET /api/2/taxonomy/event` 1회다(15분 캐시를 공유해 맥락 도구가 같은 결과를 다시 쓴다). 결과와 거절 메시지 대응은 다음과 같다.

| 상황 | 거절 메시지(계약 v1.5 `AMPLITUDE_UNAVAILABLE`) |
|---|---|
| 키 하나라도 없음 | Amplitude 조회 불가: 서버에 Amplitude 키가 설정되어 있지 않습니다 |
| 401·403 | Amplitude 조회 불가: 인증에 실패했습니다(키 확인 필요) |
| 429 | Amplitude 조회 불가: 요청 한도를 넘었습니다(잠시 후 다시) |
| 그 밖의 실패 | Amplitude 조회 불가: 연결에 실패했습니다 |

## 4. 허용 경로

코드는 아래 GET 경로만 부른다. 그 밖의 경로나 GET 아닌 메서드는 호출 전에 예외다.

`/api/2/events/segmentation`, `/api/2/funnels`, `/api/2/retention`, `/api/2/taxonomy/event`, `/api/2/taxonomy/event-property`, `/api/2/taxonomy/user-property`
