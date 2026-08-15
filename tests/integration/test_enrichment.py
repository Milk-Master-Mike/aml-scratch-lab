import asyncio
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from apps.api.app.database import Base, engine
from apps.api.app.main import app
from engine.enrichment.models import SourceResult


async def enrichment_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/scenarios/rapid-movement/runs", json={"seed": 194028, "days": 30}
        )
        assert response.status_code == 200
        run = response.json()
        packet = run["enrichment"]
        assert packet["status"] == "completed"
        assert packet["alert_id"] == run["alert"]["alert_id"]
        assert {item["source"] for item in packet["sources"]} == {
            "internal",
            "ofac",
            "fincen",
            "mock_media",
        }
        assert next(item for item in packet["sources"] if item["source"] == "ofac")[
            "findings"
        ][0]["outcome"] == "NO CANDIDATE"
        assert next(item for item in packet["sources"] if item["source"] == "fincen")[
            "findings"
        ][0]["source_record_id"] == "FIN-2024-A002"

        retrieved = await client.get(f"/api/v1/alerts/{packet['alert_id']}/evidence")
        assert retrieved.status_code == 200
        assert retrieved.json() == packet

        stored = await client.get(f"/api/v1/test-runs/{run['run_id']}")
        assert stored.json()["enrichment"] == packet


def test_alert_creates_retrievable_normalized_evidence():
    asyncio.run(enrichment_proof())


async def no_alert_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/scenarios/normal/runs", json={"seed": 194028, "days": 30}
        )
        assert response.json()["enrichment"] is None
        assert (await client.get("/api/v1/alerts/unknown/evidence")).status_code == 404


def test_no_alert_creates_no_evidence_job():
    asyncio.run(no_alert_proof())


def test_source_failure_persists_partial_packet(monkeypatch):
    from apps.api.app import service

    original = service.run_adapters

    def with_failure(context):
        successful = original(context)
        failed = SourceResult(
            "ofac",
            "failed",
            datetime.now(timezone.utc),
            {},
            (),
            "ConnectionError: source execution failed",
        )
        return tuple(failed if item.source == "ofac" else item for item in successful)

    monkeypatch.setattr(service, "run_adapters", with_failure)

    async def proof():
        Base.metadata.create_all(engine)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/scenarios/rapid-movement/runs", json={"seed": 8844, "days": 30}
            )
            packet = response.json()["enrichment"]
            assert packet["status"] == "partial"
            assert any(item["status"] == "completed" for item in packet["sources"])
            failed_source = next(item for item in packet["sources"] if item["source"] == "ofac")
            assert failed_source["status"] == "failed"
            assert failed_source["error"] == "ConnectionError: source execution failed"

    asyncio.run(proof())
