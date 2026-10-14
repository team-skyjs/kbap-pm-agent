# Data Model: 질문 마법사

기존 스키마(001 data-model.md)에 테이블 하나와 ENUM 값 하나를 더한다. 시각은 UTC `DATETIME(3)`, 문자셋 `utf8mb4`이고 API는 camelCase다.

## question_refinements (신규)

| 컬럼 | 타입 | 제약 | API 필드 |
|---|---|---|---|
| id | BIGINT PK AUTO_INCREMENT | | `refinementId` |
| conversation_id | BIGINT NULL FK → conversations ON DELETE SET NULL | 요청의 `conversationId`(null 허용) | — |
| original_question | TEXT | 1~4000자, 요청 `question` 그대로 | — |
| refined_question | TEXT | 1~4000자 | `refined` |
| summary | VARCHAR(300) | 1~300자 | `summary` |
| model | VARCHAR(100) | 실제 쓴 모델 문자열(`provider:model`, fake면 `fake`) | — |
| choice | ENUM('refined','original','cancelled') NULL | 선택 전 NULL | `choice` |
| created_at | DATETIME(3) | | — |
| chosen_at | DATETIME(3) NULL | choice 기록 시각, 덮어쓰면 갱신 | `chosenAt` |

- 모델 호출이 실패하면 행을 만들지 않는다(계약: `UPSTREAM_ERROR`).
- 상태 전이: `NULL → refined|original|cancelled`이고, 다시 부르면 마지막 값으로 덮어쓴다.

채택 비율(SC-002) 조회 한 줄:

```sql
SELECT ROUND(100 * SUM(choice = 'refined') / COUNT(*), 1) AS adopted_pct, COUNT(*) AS shown
FROM question_refinements WHERE choice IS NOT NULL;
```

## llm_usage (변경)

| 컬럼 | 변경 |
|---|---|
| purpose | `ENUM('agent','code_summary','refine')`. `refine` = 질문 다듬기 1회. `message_id`는 NULL이다(대화 메시지가 아님) |

마이그레이션은 research R4, ADR-29다. 비용은 기존대로 예산 합계(`settings.budget.spentUsd`)에 포함된다.

## RefineResult (구조화 출력, `backend/app/schemas.py`)

```python
class RefineResult(BaseModel):
    refined: str   # 1~4000자, 한국어 두 문장 이내(프롬프트 규칙)
    summary: str   # 1~300자
```
