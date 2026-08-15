from __future__ import annotations

from datetime import datetime, timezone

from engine.enrichment.adapters import FincenAdapter, InternalAdapter, MockMediaAdapter, OfacAdapter
from engine.enrichment.models import EnrichmentContext, SourceAdapter, SourceResult


def default_adapters() -> tuple[SourceAdapter, ...]:
    return (InternalAdapter(), OfacAdapter(), FincenAdapter(), MockMediaAdapter())


def run_adapters(
    context: EnrichmentContext, adapters: tuple[SourceAdapter, ...] | None = None
) -> tuple[SourceResult, ...]:
    results: list[SourceResult] = []
    for adapter in adapters or default_adapters():
        try:
            results.append(adapter.enrich(context))
        except Exception as exc:  # noqa: BLE001 - adapters are an isolation boundary
            results.append(
                SourceResult(
                    source=adapter.name,
                    status="failed",
                    observed_at=datetime.now(timezone.utc),
                    provenance={},
                    findings=(),
                    error=f"{type(exc).__name__}: source execution failed",
                )
            )
    return tuple(results)
