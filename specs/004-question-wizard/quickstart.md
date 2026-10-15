# Quickstart: 질문 마법사

```bash
docker compose up -d --build                  # 레포 루트: backend(fake 모드) + mysql. 기동 시 llm_usage ENUM 마이그레이션 자동 적용
cd frontend && npm run dev                    # http://localhost:5173
```

계약은 [contracts/README.md](./contracts/README.md)가 가리키는 정본 v1.3을 본다. 저장 구조는 [data-model.md](./data-model.md)다.

## 시연 모드 시나리오

| # | 하는 일 | 기대 결과 | 관련 |
|---|---|---|---|
| 1 | 입력창 비운 채 버튼 확인 | "질문 다듬기" 비활성 | US1-1 |
| 2 | "스캔 이탈 왜 많아?" 입력 → 다듬기 | 진행 표시 후 비교 카드(계약 예시 개선안·요약) | US1-2 |
| 3 | 개선안으로 보내기 | 카드 닫힘, 개선안이 메시지로 전송, 기록 `choice='refined'` | US1-3, US3-1 |
| 4 | 다시 다듬기 → 원문으로 보내기 | 원문 전송, `choice='original'` | US1-4 |
| 5 | 다시 다듬기 → 입력창에 넣기 → 조금 고쳐 Enter | 넣은 직후엔 기록 없음(NULL), 전송하면 `choice='refined'` | US1-5, US3-2 |
| 5b | 다시 다듬기 → 입력창에 넣기 → 입력을 비움 | `choice='cancelled'` | US3-3 |
| 6 | 다시 다듬기 → ESC | 원문 유지, `choice='cancelled'` | US1-6, US3-4 |
| 7 | 채택 비율 조회(data-model.md SQL) | 5행(3·4·5·5b·6) 중 refined 2 → 40.0, shown 5 | SC-002 |
| 8 | `SELECT purpose, cost_usd FROM llm_usage WHERE purpose='refine'` | 다듬기마다 0원 행 | US3-4 |

## 검사

```bash
cd backend && uv run python checks/check_b10.py      # 백엔드 다듬기·기록·마이그레이션 멱등
cd frontend && npm run check && npx playwright test checks/ui/us12.spec.ts
```

## 모델 비교 (실제 키, 로컬 `.env`)

```bash
cd backend && AGENT_MODE=real uv run python checks/compare_refine.py   # → _workspace/06_refine_model_comparison.md
```
