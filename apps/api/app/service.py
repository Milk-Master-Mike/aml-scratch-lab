from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.db_models import (
    AccountRow,
    AlertRow,
    ControlRow,
    ControlVersionRow,
    CustomerRow,
    EnrichmentJobRow,
    EnrichmentSourceRow,
    EvidenceFindingRow,
    RegressionBatchRow,
    ScenarioRow,
    TestRunRow,
    TransactionRow,
)
from apps.api.app.schemas import (
    AlertResponse,
    EvidenceFinding,
    EvidencePacket,
    EvidenceSource,
    FlowResponse,
    RegressionSummary,
    RunResponse,
)
from engine.aml.controls import ControlDefinition, load_controls
from engine.aml.evaluator import evaluate
from engine.enrichment.models import EnrichmentContext
from engine.enrichment.runner import run_adapters
from engine.scenarios.generator import generate_scenario
from engine.scenarios.loader import ScenarioDefinition, load_scenarios

ROOT = Path(__file__).resolve().parents[3]


def definitions() -> tuple[dict[str, ScenarioDefinition], dict[str, ControlDefinition]]:
    scenarios = load_scenarios(ROOT / "scenarios")
    controls = load_controls(ROOT / "controls")
    unknown = {item.control_id for item in scenarios.values()} - controls.keys()
    if unknown:
        raise ValueError(f"Scenarios reference unknown controls: {', '.join(sorted(unknown))}")
    for control in controls.values():
        missing = set(control.scenario_coverage) - scenarios.keys()
        if missing:
            raise ValueError(
                f"{control.id} references unknown scenarios: {', '.join(sorted(missing))}"
            )
    return scenarios, controls


def register_control(session: Session, source: ControlDefinition) -> ControlDefinition:
    version = session.get(ControlVersionRow, (source.id, source.version))
    if version and version.fingerprint != source.fingerprint:
        raise ValueError(f"{source.id}@{source.version} changed; increment its version")
    if version is None:
        session.add(
            ControlVersionRow(
                control_id=source.id,
                version=source.version,
                fingerprint=source.fingerprint,
                definition=source.model_dump(),
                loaded_at=datetime.now(timezone.utc),
            )
        )
    state = session.get(ControlRow, source.id)
    if state is None:
        state = ControlRow(
            control_id=source.id,
            name=source.name,
            version=source.version,
            enabled=source.enabled,
            definition=source.model_dump(),
        )
        session.add(state)
    elif source.version > state.version:
        state.name = source.name
        state.version = source.version
        state.definition = source.model_dump()
    session.flush()
    return source.model_copy(update={"enabled": state.enabled})


def failure_reason(
    scenario: ScenarioDefinition, actual_alert: bool, actual_severity: str | None
) -> str | None:
    if scenario.expected.alert != actual_alert:
        expected = "an alert" if scenario.expected.alert else "no alert"
        actual = "an alert" if actual_alert else "no alert"
        return f"Expected {expected}; control produced {actual}."
    if actual_alert and scenario.expected.severity != actual_severity:
        return f"Expected severity {scenario.expected.severity}; got {actual_severity}."
    return None


def execute(
    session: Session,
    scenario: ScenarioDefinition,
    source_control: ControlDefinition,
    seed: int,
    days: int,
    batch_id: str | None = None,
    mutation: dict | None = None,
) -> RunResponse:
    control = register_control(session, source_control)
    dataset = generate_scenario(scenario, seed, days)
    executed_at = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())

    if not control.enabled:
        alert = None
        result = "UNTESTED"
        reason = "Mapped control is disabled."
        actual_alert: bool | None = None
        actual_severity = None
    else:
        effective = control
        if mutation and mutation.get("control_id") == control.id:
            changes = mutation.get("conditions", {})
            effective = control.model_copy(
                update={"conditions": control.conditions.model_copy(update=changes)}
            )
        alert = evaluate(effective, dataset)
        actual_alert = alert is not None
        actual_severity = alert.severity if alert else None
        reason = failure_reason(scenario, actual_alert, actual_severity)
        result = "FAIL" if reason else "PASS"

    session.merge(
        ScenarioRow(
            scenario_id=scenario.id,
            key=scenario.key,
            name=scenario.name,
            version=scenario.version,
            definition=scenario.model_dump(),
        )
    )
    for customer in dataset.customers:
        session.merge(CustomerRow(**customer.__dict__))
    for account in dataset.accounts:
        session.merge(AccountRow(**account.__dict__))
    for transaction in dataset.transactions:
        session.merge(TransactionRow(**transaction.__dict__))

    evidence = {
        "dataset_seed": seed,
        "scenario": f"{scenario.id}@{scenario.version}",
        "control": f"{control.id}@{control.version}",
        "control_fingerprint": source_control.fingerprint,
        "triggered_conditions": list(alert.triggered_conditions) if alert else [],
        "relevant_transactions": list(alert.transaction_ids) if alert else [],
        "ephemeral_mutation": mutation,
    }
    session.add(
        TestRunRow(
            run_id=run_id,
            scenario_id=scenario.id,
            control_id=control.id,
            seed=seed,
            expected_alert=dataset.expected_alert,
            actual_alert=actual_alert,
            result=result,
            executed_at=executed_at,
            evidence=evidence,
            batch_id=batch_id,
            failure_reason=reason,
        )
    )
    session.flush()
    alert_id = None
    enrichment = None
    if alert:
        alert_id = str(uuid.uuid4())
        alert_row = AlertRow(
            alert_id=alert_id,
            run_id=run_id,
            control_id=alert.control_id,
            account_id=alert.account_id,
            severity=alert.severity,
            triggered_conditions=list(alert.triggered_conditions),
            transaction_ids=list(alert.transaction_ids),
        )
        session.add(alert_row)
        session.flush()
        context = enrichment_context(session, scenario, dataset, alert)
        enrichment = persist_enrichment(session, alert_row, context)
    session.commit()

    customer_names = {
        account.account_id: next(
            customer.synthetic_name
            for customer in dataset.customers
            if customer.customer_id == account.customer_id
        )
        for account in dataset.accounts
    }
    relevant = set(alert.transaction_ids) if alert else set()
    flows = [
        FlowResponse(
            source=customer_names.get(tx.source_account, "External source"),
            destination=customer_names.get(tx.destination_account, "External destination"),
            amount=float(tx.amount),
            currency=tx.currency,
        )
        for tx in dataset.transactions
        if tx.transaction_id in relevant
    ]
    alert_response = (
        AlertResponse(
            alert_id=alert_id,
            control_id=alert.control_id,
            account_id=alert.account_id,
            severity=alert.severity,
            triggered_conditions=list(alert.triggered_conditions),
            transaction_ids=list(alert.transaction_ids),
        )
        if alert
        else None
    )
    return RunResponse(
        run_id=run_id,
        scenario_key=scenario.key,
        scenario_version=scenario.version,
        control_id=control.id,
        control_version=control.version,
        seed=seed,
        executed_at=executed_at,
        counts={
            "customers": len(dataset.customers),
            "accounts": len(dataset.accounts),
            "transactions": len(dataset.transactions),
        },
        expected={"alert": dataset.expected_alert, "severity": dataset.expected_severity},
        actual={"alert": actual_alert, "severity": actual_severity},
        result=result,
        failure_reason=reason,
        alert=alert_response,
        enrichment=enrichment,
        flows=flows,
        evidence=evidence,
    )


def run_regression(
    session: Session, seed: int, days: int, mutation: dict | None = None
) -> RegressionSummary:
    scenarios, controls = definitions()
    batch = RegressionBatchRow(
        batch_id=str(uuid.uuid4()),
        seed=seed,
        days=days,
        started_at=datetime.now(timezone.utc),
        mutation=mutation,
    )
    session.add(batch)
    session.commit()
    results = [
        execute(
            session, scenario, controls[scenario.control_id], seed, days, batch.batch_id, mutation
        )
        for scenario in scenarios.values()
    ]
    batch.total = len(results)
    batch.passed = sum(item.result == "PASS" for item in results)
    batch.failed = sum(item.result == "FAIL" for item in results)
    batch.untested = sum(item.result == "UNTESTED" for item in results)
    batch.coverage = Decimal(str(round((batch.passed + batch.failed) / batch.total * 100, 2)))
    batch.completed_at = datetime.now(timezone.utc)
    session.commit()
    return batch_response(session, batch, results)


def batch_response(
    session: Session, batch: RegressionBatchRow, results: list[RunResponse] | None = None
) -> RegressionSummary:
    if results is None:
        rows = session.scalars(
            select(TestRunRow)
            .where(TestRunRow.batch_id == batch.batch_id)
            .order_by(TestRunRow.executed_at)
        ).all()
        results = [stored_run_response(session, row) for row in rows]
    return RegressionSummary(
        batch_id=batch.batch_id,
        seed=batch.seed,
        days=batch.days,
        started_at=batch.started_at,
        completed_at=batch.completed_at,
        total=batch.total,
        passed=batch.passed,
        failed=batch.failed,
        untested=batch.untested,
        coverage=float(batch.coverage),
        mutation=batch.mutation,
        results=results,
    )


def stored_run_response(session: Session, row: TestRunRow) -> RunResponse:
    scenarios, controls = definitions()
    scenario = next(item for item in scenarios.values() if item.id == row.scenario_id)
    control = controls[row.control_id]
    alert_row = session.scalar(select(AlertRow).where(AlertRow.run_id == row.run_id))
    alert = (
        AlertResponse(
            alert_id=alert_row.alert_id,
            control_id=alert_row.control_id,
            account_id=alert_row.account_id,
            severity=alert_row.severity,
            triggered_conditions=alert_row.triggered_conditions,
            transaction_ids=alert_row.transaction_ids,
            disposition=alert_row.disposition,
        )
        if alert_row
        else None
    )
    return RunResponse(
        run_id=row.run_id,
        scenario_key=scenario.key,
        scenario_version=scenario.version,
        control_id=control.id,
        control_version=control.version,
        seed=row.seed,
        executed_at=row.executed_at,
        counts={},
        expected={"alert": row.expected_alert, "severity": scenario.expected.severity},
        actual={"alert": row.actual_alert, "severity": alert.severity if alert else None},
        result=row.result,
        failure_reason=row.failure_reason,
        alert=alert,
        enrichment=evidence_packet(session, alert_row.alert_id) if alert_row else None,
        flows=[],
        evidence=row.evidence,
    )


def enrichment_context(
    session: Session, scenario: ScenarioDefinition, dataset, alert
) -> EnrichmentContext:
    accounts = {item.account_id: item for item in dataset.accounts}
    customers = {item.customer_id: item for item in dataset.customers}
    account = accounts[alert.account_id]
    customer = customers[account.customer_id]
    relevant_ids = set(alert.transaction_ids)
    transactions = tuple(
        item for item in dataset.transactions if item.transaction_id in relevant_ids
    )
    counterparty_account_ids = {
        account_id
        for item in transactions
        for account_id in (item.source_account, item.destination_account)
        if account_id and account_id != account.account_id and account_id in accounts
    }
    counterparties = tuple(
        customers[accounts[account_id].customer_id]
        for account_id in sorted(counterparty_account_ids)
    )
    prior_alerts = session.scalar(
        select(func.count()).select_from(AlertRow).where(AlertRow.account_id == account.account_id)
    )
    prior_runs = session.scalar(
        select(func.count()).select_from(TestRunRow).where(TestRunRow.scenario_id == scenario.id)
    )
    return EnrichmentContext(
        scenario_key=scenario.key,
        scenario_family=scenario.family,
        control_id=alert.control_id,
        account=account,
        customer=customer,
        counterparties=counterparties,
        transactions=transactions,
        prior_alerts=max((prior_alerts or 0) - 1, 0),
        prior_test_runs=max((prior_runs or 0) - 1, 0),
    )


def persist_enrichment(
    session: Session, alert: AlertRow, context: EnrichmentContext
) -> EvidencePacket:
    started_at = datetime.now(timezone.utc)
    job = EnrichmentJobRow(
        job_id=str(uuid.uuid4()),
        alert_id=alert.alert_id,
        status="running",
        started_at=started_at,
    )
    session.add(job)
    session.flush()
    results = run_adapters(context)
    for result in results:
        execution = EnrichmentSourceRow(
            execution_id=str(uuid.uuid4()),
            job_id=job.job_id,
            source=result.source,
            status=result.status,
            observed_at=result.observed_at,
            provenance=result.provenance,
            error=result.error,
        )
        session.add(execution)
        for finding in result.findings:
            session.add(
                EvidenceFindingRow(
                    finding_id=str(uuid.uuid4()),
                    execution_id=execution.execution_id,
                    finding_type=finding.finding_type,
                    outcome=finding.outcome,
                    title=finding.title,
                    summary=finding.summary,
                    score=Decimal(str(finding.score)) if finding.score is not None else None,
                    source_record_id=finding.source_record_id,
                    details=finding.details,
                )
            )
    failures = sum(item.status == "failed" for item in results)
    job.status = "failed" if failures == len(results) else "partial" if failures else "completed"
    job.completed_at = datetime.now(timezone.utc)
    session.flush()
    return evidence_packet(session, alert.alert_id)


def evidence_packet(session: Session, alert_id: str) -> EvidencePacket | None:
    job = session.scalar(select(EnrichmentJobRow).where(EnrichmentJobRow.alert_id == alert_id))
    if job is None:
        return None
    executions = session.scalars(
        select(EnrichmentSourceRow)
        .where(EnrichmentSourceRow.job_id == job.job_id)
        .order_by(EnrichmentSourceRow.source)
    ).all()
    sources = []
    for execution in executions:
        findings = session.scalars(
            select(EvidenceFindingRow)
            .where(EvidenceFindingRow.execution_id == execution.execution_id)
            .order_by(EvidenceFindingRow.finding_id)
        ).all()
        sources.append(
            EvidenceSource(
                source=execution.source,
                status=execution.status,
                observed_at=as_utc(execution.observed_at),
                provenance=execution.provenance,
                error=execution.error,
                findings=[
                    EvidenceFinding(
                        finding_id=item.finding_id,
                        finding_type=item.finding_type,
                        outcome=item.outcome,
                        title=item.title,
                        summary=item.summary,
                        score=float(item.score) if item.score is not None else None,
                        source_record_id=item.source_record_id,
                        details=item.details,
                    )
                    for item in findings
                ],
            )
        )
    return EvidencePacket(
        job_id=job.job_id,
        alert_id=job.alert_id,
        status=job.status,
        started_at=as_utc(job.started_at),
        completed_at=as_utc(job.completed_at) if job.completed_at else None,
        sources=sources,
    )


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
