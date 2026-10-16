# Data Model: 대화 전체 내보내기

## conversation_exports (신규)

| 컬럼 | 타입 | 제약 | API 필드 |
|---|---|---|---|
| id | BIGINT PK AUTO_INCREMENT | | `exportId` |
| conversation_id | BIGINT NOT NULL FK → conversations ON DELETE CASCADE | 경로의 `conversationId` | `conversationId` |
| format | ENUM('pdf','markdown') NOT NULL | | `format` |
| created_at | DATETIME(3) | UTC | `createdAt` |

- `CREATE TABLE IF NOT EXISTS`로 만든다. 기존 테이블 변경이 없어 마이그레이션이 필요 없다.
- 형식별 건수 조회 한 줄(SC-003):

```sql
SELECT format, COUNT(*) AS n FROM conversation_exports GROUP BY format;
```

## Markdown 파일

형식은 [contracts/export-markdown.md](./contracts/export-markdown.md)다. 입력은 계약 `GET /api/conversations/{conversationId}` 응답 하나와 내보낸 시각(`now`)이다.
