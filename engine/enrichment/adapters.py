from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from engine.enrichment.models import EnrichmentContext, Finding, SourceResult

DATA = Path(__file__).resolve().parents[2] / "data" / "enrichment"


def _load(name: str) -> dict:
    raw = (DATA / name).read_bytes()
    manifest = json.loads((DATA / "manifest.json").read_text())
    if hashlib.sha256(raw).hexdigest() != manifest["files"][name]:
        raise ValueError(f"Pinned enrichment snapshot failed integrity check: {name}")
    return json.loads(raw)


def normalize_name(value: str) -> str:
    separated = re.sub(r"[\W_]+", " ", value, flags=re.UNICODE)
    ascii_value = unicodedata.normalize("NFKD", separated).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", ascii_value).lower().split())


def name_score(candidate: str, listed_name: str) -> float:
    left, right = normalize_name(candidate), normalize_name(listed_name)
    if left == right:
        return 1.0
    return round(SequenceMatcher(None, left, right).ratio(), 4)


class InternalAdapter:
    name = "internal"

    def enrich(self, context: EnrichmentContext) -> SourceResult:
        observed = datetime.now(timezone.utc)
        total = sum(transaction.amount for transaction in context.transactions)
        finding = Finding(
            finding_type="internal_profile",
            outcome="CONTEXT COLLECTED",
            title=context.customer.synthetic_name,
            summary=(
                f"Collected {len(context.transactions)} relevant transactions and "
                f"{len(context.counterparties)} counterparties."
            ),
            details={
                "customer_id": context.customer.customer_id,
                "account_id": context.account.account_id,
                "risk_level": context.customer.risk_level,
                "expected_monthly_volume": str(context.customer.expected_monthly_volume),
                "relevant_transaction_total": str(total),
                "transaction_ids": [item.transaction_id for item in context.transactions],
                "counterparties": [item.synthetic_name for item in context.counterparties],
                "prior_alerts": context.prior_alerts,
                "prior_test_runs": context.prior_test_runs,
            },
        )
        return SourceResult(
            self.name,
            "completed",
            observed,
            {"kind": "synthetic_bank", "snapshot": "current-test-run"},
            (finding,),
        )


class OfacAdapter:
    name = "ofac"

    def __init__(self, threshold: float = 0.88) -> None:
        self.threshold = threshold

    def enrich(self, context: EnrichmentContext) -> SourceResult:
        dataset = _load("ofac.json")
        findings: list[Finding] = []
        for subject in (context.customer, *context.counterparties):
            best: tuple[float, dict, str] | None = None
            for record in dataset["records"]:
                for listed_name in (record["name"], *record.get("aliases", [])):
                    score = name_score(subject.synthetic_name, listed_name)
                    if best is None or score > best[0]:
                        best = (score, record, listed_name)
            if best and best[0] >= self.threshold:
                score, record, matched_name = best
                findings.append(
                    Finding(
                        finding_type="sanctions_screening",
                        outcome="POTENTIAL MATCH",
                        title=subject.synthetic_name,
                        summary="Name similarity requires human review; this is not a determination.",
                        score=score,
                        source_record_id=record["source_record_id"],
                        details={"matched_name": matched_name, "programs": record["programs"]},
                    )
                )
        if not findings:
            findings.append(
                Finding(
                    finding_type="sanctions_screening",
                    outcome="NO CANDIDATE",
                    title=context.customer.synthetic_name,
                    summary=f"No name candidate met the demonstration threshold of {self.threshold:.2f}.",
                    details={"threshold": self.threshold},
                )
            )
        return SourceResult(
            self.name,
            "completed",
            datetime.now(timezone.utc),
            dataset["provenance"],
            tuple(findings),
        )


class FincenAdapter:
    name = "fincen"

    def enrich(self, context: EnrichmentContext) -> SourceResult:
        dataset = _load("fincen.json")
        findings = tuple(
            Finding(
                finding_type="advisory_intelligence",
                outcome="RELEVANT GUIDANCE",
                title=item["title"],
                summary=item["summary"],
                source_record_id=item["id"],
                details={
                    "indicators": item["indicators"],
                    "mapped_scenarios": item["mapped_scenarios"],
                    "mapped_controls": item["mapped_controls"],
                    "url": item["url"],
                },
            )
            for item in dataset["advisories"]
            if context.scenario_family in item["scenario_families"]
            or context.control_id in item["mapped_controls"]
        )
        return SourceResult(
            self.name,
            "completed",
            datetime.now(timezone.utc),
            dataset["provenance"],
            findings,
        )


class MockMediaAdapter:
    name = "mock_media"

    def enrich(self, context: EnrichmentContext) -> SourceResult:
        dataset = _load("mock_media.json")
        subjects = {normalize_name(item.synthetic_name) for item in (context.customer, *context.counterparties)}
        findings = tuple(
            Finding(
                finding_type="mock_adverse_media",
                outcome="FICTIONAL REFERENCE",
                title=item["headline"],
                summary=item["summary"],
                source_record_id=item["id"],
                details={"publisher": item["publisher"], "fictional": True},
            )
            for item in dataset["articles"]
            if normalize_name(item["subject"]) in subjects
        )
        return SourceResult(
            self.name,
            "completed",
            datetime.now(timezone.utc),
            dataset["provenance"],
            findings,
        )
