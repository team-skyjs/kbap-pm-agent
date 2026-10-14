### POST /api/questions/refine
- 용도: 사용자가 보내기 전에 질문을 다듬는다. 서버가 택사노미 이벤트 이름과 그 대화의 최근 메시지를 붙여 모델을 한 번 호출하고(도구 없음), 개선된 질문 하나와 변경 요약을 돌려준다. 호출마다 기록 행을 만든다.
- 요청:
```json
{"conversationId": 7, "question": "스캔 이탈 왜 많아?"}
```
  - `question`: 1~4000자(메시지 전송과 같은 규칙). 앞뒤 공백만 있으면 `VALIDATION_ERROR`.
  - `conversationId`: 대화 ID 또는 `null`. `null`이면 대화 이력 없이 다듬는다. 없는 ID면 404 `CONVERSATION_NOT_FOUND`.
- 응답 200:
```json
{"refinementId": 31, "refined": "최근 7일 scan_start → scan_complete(success=true) 퍼널에서 이탈이 가장 큰 단계를 찾고, 그 원인이 되는 화면 동작과 개선안을 제안해줘.", "summary": "기간을 최근 7일로 정하고(원문에 없음), 이벤트 이름과 원하는 산출물(개선안)을 명시했다."}
```
  - `refinementId`: 기록 행 ID. 선택 기록(아래)에 쓴다.
  - `refined`: 개선된 질문. 한국어 두 문장 이내, 1~4000자.
  - `summary`: 무엇이 달라졌는지 한 줄, 1~300자. 원문에 없던 기본값(기간 등)을 넣었으면 그 사실을 적는다. 택사노미 이름 목록이 4,000자를 넘어 서버가 앞부분만 넘겼으면, 서버가 요약 끝에 `(택사노미 이름이 많아 앞부분만 참고)`을 붙인다(합쳐서 300자 이내로 앞을 줄인다).
- 에러: `VALIDATION_ERROR`, `CONVERSATION_NOT_FOUND`, 403 `BUDGET_EXCEEDED`(호출 전 예산 검사), 502 `UPSTREAM_ERROR`(모델 호출 실패나 구조화 출력 검증 실패, 기록 행은 만들지 않는다). 공통 인증 규칙(`ACCESS_TOKEN`)은 다른 `/api` 요청과 같다.
- 비고: 사용량은 `llm_usage`에 용도 `refine`으로 남고 예산에 합산된다. 대화 메시지가 아니라 `messages`·`usage` 응답에는 나타나지 않는다. 모델은 `REFINE_MODEL`, 비어 있으면 `CODE_SUMMARY_MODEL`이다.

### POST /api/questions/refine/{refinementId}/choice
- 용도: 다듬기 결과를 사용자가 어떻게 골랐는지 기록한다. 채택 비율 집계용이며 화면에는 보이지 않는다.
- 요청:
```json
{"choice": "refined"}
```
  - `choice`: `"refined"`(개선안으로 보내기, 또는 개선안을 입력창에 넣기. 편집 후 전송도 채택으로 센다) | `"original"`(원문으로 보내기) | `"cancelled"`(ESC·닫기).
- 응답 200:
```json
{"refinementId": 31, "choice": "refined", "chosenAt": "2026-10-15T10:02:11.204Z"}
```
- 에러: `VALIDATION_ERROR`, `REFINEMENT_NOT_FOUND`.
- 비고: 다시 부르면 마지막 값으로 덮어쓰고 `chosenAt`을 갱신한다(프론트는 카드가 닫힐 때 한 번만 부른다). 기록 실패는 전송을 막지 않는다. 프론트는 실패를 무시하고 메시지 전송을 이어 간다.

