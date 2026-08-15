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
    control_id: str
    account_id: str
    severity: str
    triggered_conditions: list[str]
    transaction_ids: list[str]
    disposition: str = "Human review required"


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
    flows: list[FlowResponse]
    evidence: dict


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
