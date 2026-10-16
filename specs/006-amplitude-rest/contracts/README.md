# contracts/ — 006 Amplitude 서버 고정 인증

- API: 계약 정본 `_workspace/01_cto_api-contract.md` v1.5다. 분할본 `specs/001-pm-agent-prototype/contracts/`에서 바뀐 곳은 다음과 같다. 사본은 두지 않는다.
  - `01-common.md`: 이력, 인증 예외에서 콜백 제외, `AMPLITUDE_UNAVAILABLE`, 시연 모드 표.
  - `02-objects.md`: Settings `amplitude` → `{status: configured|missing}`.
  - `05-messages.md`: `skipAmplitude`, 사전 점검·거절 규칙.
  - `09-summary.md`: 요약표에서 두 행 삭제.
  - `08-amplitude.md`: OAuth 엔드포인트 두 개와 함께 파일 삭제.
- 내부 도구 형식: [amplitude-tools.md](./amplitude-tools.md). 모델 ↔ 백엔드이며 API가 아니다.
