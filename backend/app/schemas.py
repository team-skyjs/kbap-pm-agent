"""계약서 v1.1 공통 객체(contracts/02-objects.md). camelCase 별칭, extra 금지.
라우트는 dict를 직접 만들고, 이 모델은 계약 검증(검사 스크립트)과 에이전트 최종 응답 강제(AgentAnswer)에 쓴다."""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel


class M(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


# --- Evidence: kind 판별 유니온. 다른 kind 필드는 모델에 없으므로 직렬화되지 않는다
class MetricEvidence(M):
    kind: Literal["metric"]
    summary: str
    value: str = Field(description="단위 포함 문자열, 예: 41.3%")
    source: str


class CodeEvidence(M):
    kind: Literal["code"]
    summary: str
    file: str = Field(description="저장소 루트 기준 상대 경로")
    function: str | None = Field(description="감싸는 함수·컴포넌트 이름, 최상위 코드면 null")
    line: int = Field(ge=1)
    snippet: str = Field(description="최대 10줄")

    @field_validator("snippet")
    @classmethod
    def _max_10_lines(cls, v: str) -> str:
        if len(v.splitlines()) > 10:
            raise ValueError("snippet은 최대 10줄")
        return v


class TaxonomyEvidence(M):
    kind: Literal["taxonomy"]
    summary: str
    event_name: str


Evidence = Annotated[Union[MetricEvidence, CodeEvidence, TaxonomyEvidence], Field(discriminator="kind")]


class Location(M):
    file: str
    function: str
    line: int | None = Field(ge=1)


class EventProperty(M):
    name: str
    type: Literal["string", "number", "boolean"]


class FunnelStep(M):
    order: int = Field(ge=1)
    event_name: str
    status: Literal["existing", "new"]
    condition: str | None
    location: Location | None
    properties: list[EventProperty]

    @model_validator(mode="after")
    def _location_rule(self):
        if self.status == "new" and self.location is None:
            raise ValueError(f"funnel 단계 {self.order}: status가 new면 location(file, function, line) 필수")
        if self.status == "existing" and self.location is not None:
            raise ValueError(f"funnel 단계 {self.order}: status가 existing이면 location은 null")
        return self


class Measurement(M):
    primary_metric: str
    baseline: str | None
    target: str | None
    funnel: list[FunnelStep]

    @model_validator(mode="after")
    def _order_consecutive(self):
        if [s.order for s in self.funnel] != list(range(1, len(self.funnel) + 1)):
            raise ValueError("funnel order는 1부터 연속이어야 한다")
        return self


class ProposalDraft(M):
    """에이전트가 만드는 제안 본문. 카드 네 영역 순서: evidence → proposal → steps → measurement"""
    type: Literal["improvement", "funnel_design"]
    title: str = Field(max_length=200)
    evidence: list[Evidence] = Field(min_length=1)
    proposal: str
    steps: list[str] = Field(min_length=1)
    measurement: Measurement

    @model_validator(mode="after")
    def _funnel_required(self):
        if self.type == "funnel_design" and not self.measurement.funnel:
            raise ValueError("funnel_design이면 measurement.funnel 1개 이상")
        return self


class AgentAnswer(M):
    """에이전트 최종 응답. content는 마크다운이고 제안 내용을 섞지 않는다."""
    content: str
    proposals: list[ProposalDraft]


class Decision(M):
    status: Literal["pending", "adopted", "on_hold"]
    note: str | None = Field(max_length=1000)
    decided_at: str | None


class Proposal(ProposalDraft):
    id: int
    conversation_id: int
    message_id: int
    seq: int
    decision: Decision
    created_at: str


class ToolCall(M):
    id: int
    seq: int
    source: Literal["amplitude", "code", "taxonomy"]
    name: str
    input: dict
    status: Literal["running", "succeeded", "failed"]
    result_summary: str | None = Field(max_length=500)
    duration_ms: int | None
    started_at: str


class Usage(M):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class Message(M):
    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    status: Literal["running", "completed", "failed"]
    content: str
    error_code: str | None
    tool_calls: list[ToolCall]
    proposals: list[Proposal]
    usage: Usage | None
    created_at: str


class ConversationSummary(M):
    id: int
    title: str | None
    created_at: str
    updated_at: str
    message_count: int
    proposal_count: int
    adopted_count: int


class ConversationDetail(M):
    id: int
    title: str | None
    created_at: str
    updated_at: str
    messages: list[Message]


class Repository(M):
    url: str
    branch: str
    head_commit: str
    code_map_commit: str | None
    code_map_status: Literal["none", "building", "ready", "failed"]
    tracked_event_count: int
    screen_count: int
    synced_at: str
    last_error: str | None


class Taxonomy(M):
    event_count: int
    uploaded_at: str


class Amplitude(M):
    status: Literal["connected", "disconnected"]
    server_url: str
    connected_at: str | None


class Models(M):
    agent: str
    code_summary: str


class Budget(M):
    limit_usd: float
    spent_usd: float


class Settings(M):
    repository: Repository | None
    taxonomy: Taxonomy | None
    amplitude: Amplitude
    models: Models
    agent_mode: Literal["real", "fake"]
    budget: Budget


# --- 요청 본문
class CreateConversationIn(M):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class SendMessageIn(M):
    content: str = Field(min_length=1, max_length=4000)


class PatchProposalIn(M):
    status: Literal["pending", "adopted", "on_hold"]
    note: str | None = Field(default=None, max_length=1000)
