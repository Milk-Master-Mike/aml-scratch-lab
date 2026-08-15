from datetime import datetime, timezone
from decimal import Decimal

from engine.enrichment.adapters import OfacAdapter, name_score, normalize_name
from engine.enrichment.models import EnrichmentContext
from engine.enrichment.runner import run_adapters
from engine.models import Account, Customer


def context() -> EnrichmentContext:
    customer = Customer(
        "customer-1",
        "Cubana Airlines",
        "company",
        "demo services",
        "medium",
        "US",
        Decimal(10000),
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        7,
    )
    account = Account(
        "account-1", customer.customer_id, "checking", customer.opened_at, "active", Decimal(0)
    )
    return EnrichmentContext("rapid-movement", "rapid-movement", "AML-RMF-001", account, customer, (), ())


def test_name_normalization_and_scores_are_deterministic():
    assert normalize_name("  AÉRO—Caribbean, Airlines! ") == "aero caribbean airlines"
    assert name_score("Cubana Airlines", "CUBANA AIRLINES") == 1
    assert name_score("Aero Caribbean Airline", "Aero Caribbean Airlines") >= 0.88
    assert name_score("Unrelated Name", "Cubana Airlines") < 0.88


def test_source_failure_is_isolated_as_partial_input():
    class BrokenAdapter:
        name = "broken"

        def enrich(self, _context):
            raise ConnectionError("private upstream detail")

    results = run_adapters(context(), (BrokenAdapter(),))
    assert results[0].status == "failed"
    assert results[0].error == "ConnectionError: source execution failed"
    assert "private upstream detail" not in results[0].error


def test_ofac_adapter_returns_review_language_for_exact_alias_candidate():
    result = OfacAdapter().enrich(context())
    assert result.findings[0].outcome == "POTENTIAL MATCH"
    assert result.findings[0].score == 1
    assert "human review" in result.findings[0].summary.lower()
