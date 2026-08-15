import asyncio

from httpx import ASGITransport, AsyncClient

from apps.api.app.database import Base, engine
from apps.api.app.main import app


async def milestone_one_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).json()["status"] == "ok"
        scenarios = await client.get("/api/v1/scenarios")
        assert scenarios.status_code == 200
        keys = {item["key"] for item in scenarios.json()}
        assert {"normal", "rapid-movement"} <= keys
        assert len(keys) == 16
        response = await client.post(
            "/api/v1/scenarios/rapid-movement/runs", json={"seed": 194028, "days": 30}
        )
        assert response.status_code == 200
        run = response.json()
        assert run["result"] == "PASS"
        assert run["expected"] == {"alert": True, "severity": "high"}
        assert run["actual"] == {"alert": True, "severity": "high"}
        assert len(run["flows"]) == 4
        retrieved = await client.get(f"/api/v1/test-runs/{run['run_id']}")
        assert retrieved.status_code == 200
        assert retrieved.json()["evidence"]["dataset_seed"] == 194028


def test_milestone_one_rapid_movement_proof():
    asyncio.run(milestone_one_proof())


async def normal_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/scenarios/normal/runs", json={"seed": 9, "days": 30})
        assert response.status_code == 200
        assert response.json()["result"] == "PASS"
        assert response.json()["alert"] is None


def test_normal_scenario_passes_without_alert():
    asyncio.run(normal_proof())


async def unknown_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/scenarios/unknown/runs", json={})
        assert response.status_code == 404


def test_unknown_scenario_is_404():
    asyncio.run(unknown_proof())
