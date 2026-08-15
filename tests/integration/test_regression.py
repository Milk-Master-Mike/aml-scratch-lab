import asyncio

from httpx import ASGITransport, AsyncClient

from apps.api.app.database import Base, engine
from apps.api.app.main import app


async def regression_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        controls = await client.get("/api/v1/controls")
        assert controls.status_code == 200
        assert len(controls.json()) == 7

        response = await client.post("/api/v1/regression-runs", json={"seed": 194028, "days": 30})
        assert response.status_code == 200
        summary = response.json()
        assert summary["total"] == 16
        assert summary["passed"] == 16
        assert summary["failed"] == 0
        assert summary["coverage"] == 100

        retrieved = await client.get(f"/api/v1/regression-runs/{summary['batch_id']}")
        assert retrieved.status_code == 200
        assert len(retrieved.json()["results"]) == 16


def test_run_all_regression_suite_passes():
    asyncio.run(regression_proof())


async def intentional_regression_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/regression-runs/intentional-regression", json={"seed": 194028, "days": 30}
        )
        assert response.status_code == 200
        summary = response.json()
        assert summary["failed"] == 1
        failure = next(item for item in summary["results"] if item["result"] == "FAIL")
        assert failure["scenario_key"] == "rapid-movement"
        assert failure["failure_reason"] == "Expected an alert; control produced no alert."
        assert failure["evidence"]["ephemeral_mutation"]

        rerun = await client.post(
            "/api/v1/scenarios/rapid-movement/runs", json={"seed": 194028, "days": 30}
        )
        assert rerun.json()["result"] == "PASS"


def test_intentional_regression_is_detected_and_ephemeral():
    asyncio.run(intentional_regression_proof())


async def toggle_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        disabled = await client.patch("/api/v1/controls/AML-VEL-001", json={"enabled": False})
        assert disabled.status_code == 200
        assert disabled.json()["enabled"] is False
        run = await client.post(
            "/api/v1/scenarios/abnormal-velocity-alert/runs", json={"seed": 7, "days": 30}
        )
        assert run.json()["result"] == "UNTESTED"
        enabled = await client.patch("/api/v1/controls/AML-VEL-001", json={"enabled": True})
        assert enabled.json()["enabled"] is True


def test_control_toggle_marks_mapped_test_untested():
    asyncio.run(toggle_proof())
