### GET /api/settings
- 용도: 연결된 저장소·택사노미·Amplitude·모델·예산 상태 조회.
- 응답 200: Settings 객체(위 예시 그대로).

### PUT /api/settings/repository
- 용도: 분석할 FE 저장소 등록(교체). 얕은 클론을 마치고 응답한다. 무료 인덱스(이벤트 호출 목록)는 응답 전에 만들고, 화면 요약은 백그라운드로 시작한다.
- 요청:
```json
{"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop"}
```
  `url`은 `https://github.com/`로 시작해야 한다(시험용으로 `file://` 허용). `branch` 생략 시 저장소 기본 브랜치.
- 응답 200: Settings의 `repository` 객체.
```json
{"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop", "headCommit": "9f3c2a1", "codeMapCommit": null, "codeMapStatus": "building", "trackedEventCount": 87, "screenCount": 41, "syncedAt": "2026-10-15T08:55:02.117Z", "lastError": null}
```
- 에러: `VALIDATION_ERROR`, `UPSTREAM_ERROR`(클론 실패. 메시지에 토큰을 노출하지 않는다).

### POST /api/settings/repository/sync
- 용도: 등록된 저장소를 pull하고 커밋이 바뀌었으면 인덱스를 다시 만들고 바뀐 파일만 요약을 갱신한다.
- 요청: 본문 없음.
- 응답 200: `repository` 객체. 커밋이 바뀌었으면 `codeMapStatus: "building"`, 같으면 기존 상태 그대로.
```json
{"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop", "headCommit": "b71e04d", "codeMapCommit": "9f3c2a1", "codeMapStatus": "building", "trackedEventCount": 89, "screenCount": 41, "syncedAt": "2026-10-15T11:30:12.660Z", "lastError": null}
```
- 에러: `REPOSITORY_NOT_CONFIGURED`, `UPSTREAM_ERROR`. `UPSTREAM_ERROR`일 때도 같은 사유를 `repository.lastError`에 저장하고 기존 클론·인덱스는 유지한다.

### PUT /api/settings/taxonomy
- 용도: 택사노미 전체 교체 업로드. 프론트는 사용자가 고른 `.json` 파일 내용을 그대로 본문으로 보낸다.
- 요청:
```json
{
  "events": [
    {
      "name": "scan_complete",
      "description": "메뉴판 스캔이 끝나 결과 화면에 도달했거나 실패했을 때",
      "category": "scan",
      "properties": [
        {"name": "success", "type": "boolean", "description": "스캔 성공 여부"},
        {"name": "fail_reason", "type": "string", "description": "실패 사유 코드. 성공이면 없음"},
        {"name": "item_count", "type": "number", "description": "인식된 메뉴 수"}
      ]
    },
    {
      "name": "scan_start",
      "description": "카메라 촬영 또는 갤러리 선택으로 스캔을 시작했을 때",
      "category": "scan",
      "properties": [
        {"name": "source", "type": "string", "description": "camera 또는 gallery"}
      ]
    }
  ]
}
```
  - `events` 1개 이상. `name` 필수·중복 불가. `description`, `category`는 문자열 또는 `null`. `properties`는 빈 배열 가능, 속성 `type`은 `"string"` | `"number"` | `"boolean"`.
- 응답 200:
```json
{"eventCount": 2, "uploadedAt": "2026-10-15T11:40:00.000Z"}
```
- 에러: `VALIDATION_ERROR`. 검증은 전부 통과해야 반영하며, 실패하면 기존 택사노미를 그대로 둔다. `message`는 첫 번째 잘못된 항목의 위치와 사유를 담는다.
```json
{"error": {"code": "VALIDATION_ERROR", "message": "events[3].properties[0].type: \"date\"는 허용되지 않습니다. string, number, boolean 중 하나여야 합니다."}}
```

