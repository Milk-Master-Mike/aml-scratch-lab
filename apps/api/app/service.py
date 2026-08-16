from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.db_models import (
    AccountRow,
    AlertRow,
    AnalystNoteRow,
    CaseRow,
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
    AnalystNote,
    CaseDetail,
    CaseGraph,
    CaseSummary,
    DashboardResponse,
    EvidenceFinding,
    EvidencePacket,
    EvidenceSource,
    FlowResponse,
    GraphEdge,
    GraphNode,
    RegressionSummary,
    RunResponse,
    TransactionDetail,
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
    case_id = None
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
        case_id = str(uuid.uuid4())
        session.add(
            CaseRow(
                case_id=case_id,
                case_number=f"AML-{executed_at.year}-{case_id[:8].upper()}",
                alert_id=alert_id,
                status="open",
                created_at=executed_at,
                updated_at=executed_at,
            )
        )
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
        case_id=case_id,
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
    case_row = (
        session.scalar(select(CaseRow).where(CaseRow.alert_id == alert_row.alert_id))
        if alert_row
        else None
    )
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
        case_id=case_row.case_id if case_row else None,
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


def case_summary(session: Session, case: CaseRow) -> CaseSummary:
    alert = session.get(AlertRow, case.alert_id)
    run = session.get(TestRunRow, alert.run_id)
    scenario = session.get(ScenarioRow, run.scenario_id)
    account = session.get(AccountRow, alert.account_id)
    customer = session.get(CustomerRow, account.customer_id)
    return CaseSummary(
        case_id=case.case_id,
        case_number=case.case_number,
        status=case.status,
        severity=alert.severity,
        customer_name=customer.synthetic_name,
        control_id=alert.control_id,
        scenario_key=scenario.key,
        created_at=as_utc(case.created_at),
        updated_at=as_utc(case.updated_at),
    )


def list_cases(session: Session, status: str | None = None) -> list[CaseSummary]:
    query = select(CaseRow).order_by(CaseRow.created_at.desc())
    if status:
        query = query.where(CaseRow.status == status)
    return [case_summary(session, item) for item in session.scalars(query).all()]


def case_detail(session: Session, case: CaseRow) -> CaseDetail:
    summary = case_summary(session, case)
    alert = session.get(AlertRow, case.alert_id)
    run = session.get(TestRunRow, alert.run_id)
    scenario = session.get(ScenarioRow, run.scenario_id)
    account = session.get(AccountRow, alert.account_id)
    customer = session.get(CustomerRow, account.customer_id)
    related = session.scalars(
        select(AccountRow).where(AccountRow.customer_id == customer.customer_id)
    ).all()
    transactions = session.scalars(
        select(TransactionRow)
        .where(TransactionRow.transaction_id.in_(alert.transaction_ids))
        .order_by(TransactionRow.timestamp)
    ).all()
    notes = session.scalars(
        select(AnalystNoteRow)
        .where(AnalystNoteRow.case_id == case.case_id)
        .order_by(AnalystNoteRow.created_at)
    ).all()
    return CaseDetail(
        **summary.model_dump(),
        alert_id=alert.alert_id,
        run_id=run.run_id,
        account={
            "account_id": account.account_id,
            "account_type": account.account_type,
            "status": account.status,
            "balance": float(account.balance),
            "opened_at": as_utc(account.opened_at),
        },
        customer={
            "customer_id": customer.customer_id,
            "synthetic_name": customer.synthetic_name,
            "customer_type": customer.customer_type,
            "occupation_business_type": customer.occupation_business_type,
            "risk_level": customer.risk_level,
            "country": customer.country,
            "expected_monthly_volume": float(customer.expected_monthly_volume),
            "opened_at": as_utc(customer.opened_at),
        },
        related_accounts=[
            {
                "account_id": item.account_id,
                "account_type": item.account_type,
                "status": item.status,
                "balance": float(item.balance),
            }
            for item in related
        ],
        transactions=[
            TransactionDetail(
                transaction_id=item.transaction_id,
                source_account=item.source_account,
                destination_account=item.destination_account,
                amount=float(item.amount),
                currency=item.currency,
                transaction_type=item.transaction_type,
                timestamp=as_utc(item.timestamp),
                geography=item.geography,
            )
            for item in transactions
        ],
        triggered_conditions=alert.triggered_conditions,
        expected={"alert": run.expected_alert, "severity": scenario.definition["expected"].get("severity")},
        actual={"alert": run.actual_alert, "severity": alert.severity},
        result=run.result,
        failure_reason=run.failure_reason,
        evidence=evidence_packet(session, alert.alert_id),
        notes=[
            AnalystNote(
                note_id=item.note_id,
                author=item.author,
                body=item.body,
                created_at=as_utc(item.created_at),
            )
            for item in notes
        ],
    )


def case_graph(session: Session, case: CaseRow) -> CaseGraph:
    detail = case_detail(session, case)
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    customer_id = detail.customer["customer_id"]
    nodes[customer_id] = GraphNode(
        id=customer_id,
        type="customer",
        label=detail.customer_name,
        status=detail.customer["risk_level"],
        metadata=detail.customer,
    )
    account_ids = {
        value
        for tx in detail.transactions
        for value in (tx.source_account, tx.destination_account)
        if value
    }
    account_ids.add(detail.account["account_id"])
    accounts = session.scalars(select(AccountRow).where(AccountRow.account_id.in_(account_ids))).all()
    customers = {
        item.customer_id: item
        for item in session.scalars(
            select(CustomerRow).where(
                CustomerRow.customer_id.in_({item.customer_id for item in accounts})
            )
        ).all()
    }
    for account in accounts:
        owner = customers[account.customer_id]
        if owner.customer_id not in nodes:
            nodes[owner.customer_id] = GraphNode(
                id=owner.customer_id,
                type="customer",
                label=owner.synthetic_name,
                status=owner.risk_level,
                metadata={"customer_type": owner.customer_type, "country": owner.country},
            )
        nodes[account.account_id] = GraphNode(
            id=account.account_id,
            type="account",
            label=f"Account {account.account_id[:8].upper()}",
            status=account.status,
            metadata={"account_type": account.account_type, "balance": float(account.balance)},
        )
        edges.append(GraphEdge(
            id=f"owns-{owner.customer_id}-{account.account_id}",
            source=owner.customer_id,
            target=account.account_id,
            type="owns",
            label="owns",
            metadata={},
        ))
    for tx in detail.transactions:
        if tx.source_account and tx.destination_account:
            edges.append(GraphEdge(
                id=tx.transaction_id,
                source=tx.source_account,
                target=tx.destination_account,
                type="transaction",
                label=f"${tx.amount:,.2f}",
                highlighted=True,
                metadata=tx.model_dump(mode="json"),
            ))
    packet = detail.evidence
    if packet:
        for source in packet.sources:
            for finding in source.findings:
                if finding.outcome != "POTENTIAL MATCH":
                    continue
                node_id = f"candidate-{finding.finding_id}"
                nodes[node_id] = GraphNode(
                    id=node_id,
                    type="sanctions_candidate",
                    label=finding.title,
                    status=finding.outcome,
                    metadata=finding.model_dump(),
                )
                edges.append(GraphEdge(
                    id=f"match-{finding.finding_id}",
                    source=customer_id,
                    target=node_id,
                    type="possible_match",
                    label="possible match",
                    highlighted=True,
                    metadata={"score": finding.score, "source": source.source},
                ))
    return CaseGraph(case_id=case.case_id, nodes=list(nodes.values()), edges=edges)


def dashboard(session: Session) -> DashboardResponse:
    batch = session.scalar(
        select(RegressionBatchRow)
        .where(RegressionBatchRow.completed_at.is_not(None))
        .order_by(RegressionBatchRow.completed_at.desc())
    )
    control_health = None
    coverage = None
    if batch:
        tested = batch.passed + batch.failed
        control_health = round(batch.passed / tested * 100, 2) if tested else None
        coverage = float(batch.coverage)
    open_cases = session.scalar(
        select(func.count()).select_from(CaseRow).where(CaseRow.status != "closed")
    ) or 0
    total_alerts = session.scalar(select(func.count()).select_from(AlertRow)) or 0
    last_test_run = session.scalar(select(func.max(TestRunRow.executed_at)))
    failures = session.scalars(
        select(TestRunRow)
        .where(TestRunRow.result == "FAIL")
        .order_by(TestRunRow.executed_at.desc())
        .limit(5)
    ).all()
    scenarios, _ = definitions()
    scenario_keys = {item.id: item.key for item in scenarios.values()}
    executions = session.scalars(
        select(EnrichmentSourceRow).order_by(EnrichmentSourceRow.observed_at.desc())
    ).all()
    latest_sources = {}
    for item in executions:
        latest_sources.setdefault(item.source, item)
    max_timestamp = session.scalar(select(func.max(TransactionRow.timestamp)))
    activity = []
    if max_timestamp:
        max_timestamp = as_utc(max_timestamp)
        start = (max_timestamp - timedelta(days=13)).date()
        rows = session.scalars(
            select(TransactionRow).where(TransactionRow.timestamp >= datetime.combine(
                start, datetime.min.time(), tzinfo=timezone.utc
            ))
        ).all()
        for offset in range(14):
            day = start + timedelta(days=offset)
            matching = [item for item in rows if as_utc(item.timestamp).date() == day]
            activity.append({
                "date": day.isoformat(),
                "count": len(matching),
                "volume": float(sum((item.amount for item in matching), Decimal(0))),
            })
    return DashboardResponse(
        control_health=control_health,
        test_coverage=coverage,
        open_cases=open_cases,
        total_alerts=total_alerts,
        last_test_run=as_utc(last_test_run) if last_test_run else None,
        recent_failures=[
            {
                "run_id": item.run_id,
                "scenario_key": scenario_keys.get(item.scenario_id, item.scenario_id),
                "control_id": item.control_id,
                "reason": item.failure_reason,
                "executed_at": as_utc(item.executed_at),
            }
            for item in failures
        ],
        source_health=[
            {
                "source": source,
                "status": item.status,
                "observed_at": as_utc(item.observed_at),
                "error": item.error,
            }
            for source, item in sorted(latest_sources.items())
        ],
        transaction_activity=activity,
    )
