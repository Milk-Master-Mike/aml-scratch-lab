from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.app.database import get_session
from apps.api.app.db_models import ControlRow, RegressionBatchRow, TestRunRow
from apps.api.app.schemas import (
    ControlSummary,
    ControlToggle,
    RegressionSummary,
    RunRequest,
    RunResponse,
    ScenarioSummary,
)
from apps.api.app.service import (
    batch_response,
    definitions,
    execute,
    register_control,
    run_regression,
    stored_run_response,
)

SessionDependency = Annotated[Session, Depends(get_session)]

app = FastAPI(title="AML ScratchLab API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(session: SessionDependency) -> dict:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "service": "scratchlab-api"}


@app.get("/api/v1/scenarios", response_model=list[ScenarioSummary])
async def scenarios() -> list[ScenarioSummary]:
    items, _ = definitions()
    return [
        ScenarioSummary(
            key=item.key,
            id=item.id,
            version=item.version,
            family=item.family,
            case=item.case,
            control_id=item.control_id,
            name=item.name,
            description=item.description,
            expected_alert=item.expected.alert,
        )
        for item in items.values()
    ]


@app.get("/api/v1/controls", response_model=list[ControlSummary])
async def controls(session: SessionDependency) -> list[ControlSummary]:
    _, items = definitions()
    resolved = [register_control(session, item) for item in items.values()]
    session.commit()
    return [
        ControlSummary(
            id=item.id,
            name=item.name,
            version=item.version,
            enabled=item.enabled,
            owner=item.owner,
            description=item.description,
            severity=item.severity,
            evaluator=item.evaluator,
            scenario_coverage=item.scenario_coverage,
        )
        for item in resolved
    ]


@app.patch("/api/v1/controls/{control_id}", response_model=ControlSummary)
async def toggle_control(
    control_id: str, request: ControlToggle, session: SessionDependency
) -> ControlSummary:
    _, items = definitions()
    if control_id not in items:
        raise HTTPException(status_code=404, detail="Unknown control")
    control = register_control(session, items[control_id])
    state = session.get(ControlRow, control_id)
    state.enabled = request.enabled
    session.commit()
    control = control.model_copy(update={"enabled": request.enabled})
    return ControlSummary(
        id=control.id,
        name=control.name,
        version=control.version,
        enabled=control.enabled,
        owner=control.owner,
        description=control.description,
        severity=control.severity,
        evaluator=control.evaluator,
        scenario_coverage=control.scenario_coverage,
    )


@app.post("/api/v1/scenarios/{scenario_key}/runs", response_model=RunResponse)
async def run_scenario(
    scenario_key: str, request: RunRequest, session: SessionDependency
) -> RunResponse:
    items, controls_by_id = definitions()
    if scenario_key not in items:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    scenario = items[scenario_key]
    return execute(
        session, scenario, controls_by_id[scenario.control_id], request.seed, request.days
    )


@app.get("/api/v1/test-runs/{run_id}", response_model=RunResponse)
async def test_run(run_id: str, session: SessionDependency) -> RunResponse:
    row = session.get(TestRunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown test run")
    return stored_run_response(session, row)


@app.post("/api/v1/regression-runs", response_model=RegressionSummary)
async def run_all(request: RunRequest, session: SessionDependency) -> RegressionSummary:
    return run_regression(session, request.seed, request.days)


@app.post("/api/v1/regression-runs/intentional-regression", response_model=RegressionSummary)
async def intentional_regression(
    request: RunRequest, session: SessionDependency
) -> RegressionSummary:
    mutation = {
        "control_id": "AML-RMF-001",
        "conditions": {"minimum_incoming": 50000},
        "description": "Ephemeral demo: raise minimum incoming from 10,000 to 50,000.",
    }
    return run_regression(session, request.seed, request.days, mutation)


@app.get("/api/v1/regression-runs/{batch_id}", response_model=RegressionSummary)
async def regression_result(batch_id: str, session: SessionDependency) -> RegressionSummary:
    batch = session.get(RegressionBatchRow, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Unknown regression run")
    return batch_response(session, batch)
