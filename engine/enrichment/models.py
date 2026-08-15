from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from engine.models import Account, Customer, Transaction


@dataclass(frozen=True)
class EnrichmentContext:
    scenario_key: str
    scenario_family: str
    control_id: str
    account: Account
    customer: Customer
    counterparties: tuple[Customer, ...]
    transactions: tuple[Transaction, ...]
    prior_alerts: int = 0
    prior_test_runs: int = 0


@dataclass(frozen=True)
class Finding:
    finding_type: str
    outcome: str
    title: str
    summary: str
    score: float | None = None
    source_record_id: str | None = None
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SourceResult:
    source: str
    status: str
    observed_at: datetime
    provenance: dict
    findings: tuple[Finding, ...]
    error: str | None = None


class SourceAdapter(Protocol):
    name: str

    def enrich(self, context: EnrichmentContext) -> SourceResult: ...
