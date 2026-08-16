from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    seed: int = Field(default=194028, ge=0, le=2_147_483_647)
    days: int = Field(default=30, ge=30, le=90)


class ScenarioSummary(BaseModel):
    key: str
    id: str
    version: int
    family: str
    case: str
    control_id: str
    name: str
    description: str
    expected_alert: bool


class ControlSummary(BaseModel):
    id: str
    name: str
    version: int
    enabled: bool
    owner: str
    description: str
    severity: str
    evaluator: str
    scenario_coverage: list[str]


class ControlToggle(BaseModel):
    enabled: bool


class AlertResponse(BaseModel):
    alert_id: str
    control_id: str
    account_id: str
    severity: str
    triggered_conditions: list[str]
    transaction_ids: list[str]
    disposition: str = "Human review required"


class EvidenceFinding(BaseModel):
    finding_id: str
    finding_type: str
    outcome: str
    title: str
    summary: str
    score: float | None = None
    source_record_id: str | None = None
    details: dict


class EvidenceSource(BaseModel):
    source: str
    status: str
    observed_at: datetime
    provenance: dict
    error: str | None = None
    findings: list[EvidenceFinding]


class EvidencePacket(BaseModel):
    job_id: str
    alert_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    disposition: str = "Human review required"
    sources: list[EvidenceSource]


class FlowResponse(BaseModel):
    source: str
    destination: str
    amount: float
    currency: str


class RunResponse(BaseModel):
    run_id: str
    scenario_key: str
    scenario_version: int
    control_id: str
    control_version: int
    seed: int
    executed_at: datetime
    counts: dict[str, int]
    expected: dict
    actual: dict
    result: str
    failure_reason: str | None = None
    alert: AlertResponse | None
    enrichment: EvidencePacket | None = None
    flows: list[FlowResponse]
    evidence: dict
    case_id: str | None = None


class RegressionSummary(BaseModel):
    batch_id: str
    seed: int
    days: int
    started_at: datetime
    completed_at: datetime | None
    total: int
    passed: int
    failed: int
    untested: int
    coverage: float
    mutation: dict | None
    results: list[RunResponse]


class CaseStatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|in_review|closed)$")


class AnalystNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class AnalystNote(BaseModel):
    note_id: str
    author: str
    body: str
    created_at: datetime


class CaseSummary(BaseModel):
    case_id: str
    case_number: str
    status: str
    severity: str
    customer_name: str
    control_id: str
    scenario_key: str
    created_at: datetime
    updated_at: datetime


class TransactionDetail(BaseModel):
    transaction_id: str
    source_account: str | None
    destination_account: str | None
    amount: float
    currency: str
    transaction_type: str
    timestamp: datetime
    geography: str


class CaseDetail(CaseSummary):
    alert_id: str
    run_id: str
    account: dict
    customer: dict
    related_accounts: list[dict]
    transactions: list[TransactionDetail]
    triggered_conditions: list[str]
    expected: dict
    actual: dict
    result: str
    failure_reason: str | None
    evidence: EvidencePacket | None
    notes: list[AnalystNote]


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    status: str | None = None
    metadata: dict


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str
    highlighted: bool = False
    metadata: dict


class CaseGraph(BaseModel):
    case_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class DashboardResponse(BaseModel):
    control_health: float | None
    test_coverage: float | None
    open_cases: int
    total_alerts: int
    last_test_run: datetime | None
    recent_failures: list[dict]
    source_health: list[dict]
    transaction_activity: list[dict]
