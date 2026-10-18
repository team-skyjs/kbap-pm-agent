# Data Model: Amplitude 서버 고정 인증

## messages (변경)

| 컬럼 | 타입 | 규칙 |
|---|---|---|
| amplitude_status | ENUM('used','unavailable','skipped') NULL | assistant 메시지 하나(실행 하나)에 하나다. `used`는 사전 점검 통과, `skipped`는 사용자가 건너뜀, `unavailable`은 실행 중 Amplitude 401·403이다. 시연 모드·user 메시지·이전 행은 NULL이다. API로는 내보내지 않는다 |

마이그레이션은 research R5(기동 시 조건부 `ADD COLUMN`)다. 상태별 건수 조회 한 줄(SC-002):

```sql
SELECT amplitude_status, COUNT(*) AS n FROM messages
WHERE role = 'assistant' AND status = 'completed' AND amplitude_status IS NOT NULL GROUP BY amplitude_status;
```

## app_settings (정리)

- `amplitude`, `amplitude_oauth` 행을 기동 시 삭제한다(멱등). 이전 OAuth 클라이언트 등록과 토큰(읽기+쓰기 권한으로 발급됐던 것)이 남지 않게 한다.

## 설정 응답 (계약 v1.5)

- `settings.amplitude = {"status": "configured" | "missing"}`. env `AMPLITUDE_API_KEY`·`AMPLITUDE_SECRET_KEY`가 둘 다 비어 있지 않으면 `configured`다.

## 캐시 (비영속)

- 키 `(path, sorted params)`, 값 `(시각, JSON)`, 15분. 프로세스 메모리 dict. 지표 조회·맥락·사전 점검이 공유한다.
