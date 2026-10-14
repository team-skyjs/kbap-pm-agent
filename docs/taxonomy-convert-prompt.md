# 택사노미 변환 프롬프트

아래 프롬프트를 LLM에 붙여 넣고, 그 뒤에 원본 택사노미(스프레드시트 복사본, Amplitude export, 노션 표 등)를 붙인다. 결과 JSON을 `.json` 파일로 저장해 설정 화면 → 택사노미에 올린다.

---

너는 이벤트 택사노미를 정해진 JSON 형식으로 정리하는 변환기다. 아래 원본을 읽고 **JSON 하나만** 출력한다. 설명, 마크다운 코드펜스, 주석, 앞뒤 문장을 붙이지 않는다.

## 출력 형식

```
{
  "events": [
    {
      "name": "scan_complete",
      "description": "메뉴판 스캔이 끝나 결과 화면에 도달했거나 실패했을 때",
      "category": "scan",
      "properties": [
        {"name": "success", "type": "boolean", "description": "스캔 성공 여부"},
        {"name": "fail_reason", "type": "string", "description": "실패 사유 코드. 성공이면 없음"}
      ]
    }
  ]
}
```

## 규칙

1. `events`는 1개 이상. 각 이벤트는 `name`, `description`, `category`, `properties` 네 키를 모두 가진다.
2. `name`은 원본의 이벤트 이름을 **글자 그대로** 쓴다. 대소문자·언더스코어·공백을 바꾸지 않는다. 코드의 `track(EVENTS.xxx)`와 대조하는 키이기 때문이다. 같은 이름이 두 번 나오면 하나로 합치고 속성을 병합한다.
3. `description`은 "언제 발생하는가"를 한국어 한 문장으로. 원본에 설명이 없으면 `null`. 지어내지 않는다.
4. `category`는 원본의 카테고리·그룹·화면명 열이 있으면 그 값(소문자 영문 권장), 없으면 `null`.
5. `properties`는 빈 배열 `[]`일 수 있다. 각 속성은 `name`, `type`, `description` 세 키.
6. 속성 `type`은 **`"string"`, `"number"`, `"boolean"` 셋 중 하나만** 허용한다. 원본 타입을 이렇게 바꾼다:
   - 정수, 실수, int, float, double, count, 금액, 개수 → `"number"`
   - true/false, bool, 여부, flag → `"boolean"`
   - 날짜, 시각, date, datetime, timestamp, enum, 선택값, id, url, 그 외 전부 → `"string"`
   - 원본에 타입이 없으면 값 예시나 이름으로 추정하되, 애매하면 `"string"`
7. 속성 `description`은 원본 설명을 옮기고, enum이면 허용값을 "camera 또는 gallery"처럼 나열한다. 없으면 `null`.
8. 원본에 있는 이벤트를 빠뜨리지 않는다. 원본에 없는 이벤트나 속성을 추가하지 않는다.
9. 출력 전에 스스로 검사한다: 유효한 JSON인가, `name` 중복이 없는가, 모든 `type`이 세 값 중 하나인가, `description`·`category`가 문자열 또는 `null`인가.

## 원본

(여기에 원본 택사노미를 붙인다)
