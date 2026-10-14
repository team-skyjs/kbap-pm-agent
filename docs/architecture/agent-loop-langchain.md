# 에이전트 루프 구성도 — LangChain 기반 (ADR-20 전환 전 기준선)

기준 커밋: `feat/anthropic-sdk-direct` 브랜치의 B9 착수 직전 `backend/app/agent.py`.
ADR-20(공식 SDK 전환) 이후 노란색 노드가 모두 바뀐다. 전환 전 구조를 남겨 두는 기록이다.

- 노란색: LangChain 계열 (제거 대상)
- 파란색: 프론트로 나가는 SSE 이벤트 (계약 v1.1, 변경 없음)
- 회색: 외부 시스템

![agent loop](./agent-loop-langchain.png)

소스: [`agent-loop-langchain.mmd`](./agent-loop-langchain.mmd)

```mermaid
flowchart TD
    subgraph API["FastAPI · POST /api/conversations/:id/messages"]
        R["라우트<br/>budget 상한 검사 → 403<br/>message_created 이벤트"] --> RA["run_agent()"]
    end

    RA --> MODE{"AGENT_MODE?"}
    MODE -- fake --> FAKE["_fake()<br/>계약서 예시 값으로<br/>tool_call · tool_result · final<br/>이벤트 재생"]
    MODE -- real --> TOOLS["_tools()<br/>쓸 수 있는 소스만 모은다"]

    subgraph SRC["도구 소스 (조건부)"]
        CODE["code_tools.CODE_TOOLS<br/>find_event_calls · search_code<br/>get_screen_summary · read_code"]
        TAX["code_tools.TAXONOMY_TOOLS<br/>search_taxonomy · get_event_definition"]
        AMP["amplitude.tools()<br/>MultiServerMCPClient<br/>(langchain-mcp-adapters)"]
        AMP --> MCP["Amplitude 원격 MCP<br/>mcp.amplitude.com<br/>OAuthClientProvider"]
    end
    TOOLS -. 저장소 클론 있으면 .-> CODE
    TOOLS -. 택사노미 있으면 .-> TAX
    TOOLS -. 연결됐으면<br/>실패해도 계속 .-> AMP

    TOOLS --> MODEL["_model()<br/>init_chat_model(AGENT_MODEL)"]
    MODEL --> LCA["langchain-anthropic"] --> SDKA["anthropic SDK"]
    MODEL --> LCO["langchain-openai"] --> SDKO["openai SDK"]

    MODEL --> GRAPH
    subgraph GRAPH["create_agent() · LangGraph"]
        direction LR
        M["model 노드<br/>system_prompt + 소스 상태"] -- tool_calls --> T["tools 노드<br/>ToolErrorMiddleware<br/>(오류 → 문자열 결과)"]
        T -- ToolMessage --> M
        M -- 도구 호출 없음 --> SR["structured_response<br/>ProviderStrategy(AgentAnswer)"]
    end

    GRAPH -- "astream(stream_mode=updates)" --> LOOP["이벤트 변환 루프"]
    LOOP -- "AIMessage" --> U["budget.record(usage)"]
    LOOP -- "AIMessage.tool_calls" --> TC(["SSE tool_call"])
    LOOP -- "ToolMessage" --> TR(["SSE tool_result<br/>succeeded | failed"])
    LOOP -- "structured_response" --> FIN(["SSE final<br/>content + proposals"])

    LOOP -- "calls ≥ AGENT_MAX_TOOL_CALLS(5)" --> PART(["SSE final (부분)<br/>조회 결과 요약"])
    LOOP -- "asyncio.timeout(170s)" --> PART
    LOOP -- "예외 · 규칙 위반" --> ERR(["SSE error<br/>UPSTREAM_ERROR"])

    SUM["summarize()<br/>init_chat_model(CODE_SUMMARY_MODEL)<br/>코드 맵 캐시(B5)에서 호출"] -.-> LCA

    classDef lc fill:#fde68a,stroke:#92400e,color:#111
    classDef out fill:#dbeafe,stroke:#1e40af,color:#111
    classDef ext fill:#e5e7eb,stroke:#374151,color:#111
    class MODEL,LCA,LCO,GRAPH,M,T,SR,AMP,SUM lc
    class TC,TR,FIN,PART,ERR out
    class SDKA,SDKO,MCP ext
```

## 읽는 법

1. 라우트가 예산 상한을 먼저 검사하고 `message_created`를 보낸 뒤 `run_agent()`를 호출한다.
2. `_tools()`는 세 소스 중 **쓸 수 있는 것만** 도구로 모은다. Amplitude가 실패해도 나머지로 답한다(FR-010).
3. `create_agent()`가 만든 LangGraph는 model 노드와 tools 노드를 오가며, 도구 호출이 없는 턴에서 `ProviderStrategy(AgentAnswer)`로 구조화 응답을 낸다. 강제 tool_choice는 쓰지 않는다(현행 Claude 모델이 400).
4. 이벤트 변환 루프가 LangGraph 메시지를 계약서의 SSE 이벤트로 바꾼다. 이 경계면이 ADR-20 전환에서 QA가 글자 단위로 대조하는 지점이다.
5. 도구 호출 20회·170초 상한에 닿으면 조회 결과 요약으로 부분 `final`을, 예외나 스키마 교차 규칙 위반은 `UPSTREAM_ERROR`를 낸다(재시도 없음).
6. `summarize()`는 별도 모델(CODE_SUMMARY_MODEL)로 코드 맵 캐시(B5)에서만 호출된다.

## ADR-20 이후 바뀌는 것

| 노드 | 전환 후 |
|------|--------|
| `init_chat_model` + langchain-anthropic/openai | 모델 접두사로 분기: `anthropic` SDK tool runner / `openai-agents` Agent |
| `create_agent()` LangGraph | 각 SDK의 네이티브 루프 (model↔tools 왕복은 SDK가 수행) |
| `ProviderStrategy(AgentAnswer)` | anthropic: `output_format=AgentAnswer` / openai: `output_type=AgentAnswer` |
| `MultiServerMCPClient` | `mcp` SDK 직접 세션, 두 런타임이 OAuthClientProvider 하나를 공유 |
| 이벤트 변환 루프 | SDK 이벤트를 같은 SSE 이벤트로 매핑. 출력 형식은 그대로 |
