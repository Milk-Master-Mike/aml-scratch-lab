import asyncio

from httpx import ASGITransport, AsyncClient

from apps.api.app.database import Base, engine
from apps.api.app.main import app


async def investigator_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/scenarios/rapid-movement/runs", json={"seed": 44004, "days": 60}
        )
        assert response.status_code == 200
        run = response.json()
        assert run["case_id"]

        cases = await client.get("/api/v1/cases", params={"status": "open"})
        assert cases.status_code == 200
        assert run["case_id"] in {item["case_id"] for item in cases.json()}

        case_id = run["case_id"]
        detail = (await client.get(f"/api/v1/cases/{case_id}")).json()
        assert detail["case_number"].startswith("AML-2026-")
        assert detail["customer"]["synthetic_name"] == detail["customer_name"]
        assert detail["triggered_conditions"]
        assert detail["transactions"]
        assert detail["evidence"]["status"] == "completed"

        note = await client.post(
            f"/api/v1/cases/{case_id}/notes", json={"body": "  Reviewed flow direction.  "}
        )
        assert note.status_code == 201
        assert note.json()["body"] == "Reviewed flow direction."
        assert note.json()["author"] == "Demo Analyst"
        assert (
            await client.post(f"/api/v1/cases/{case_id}/notes", json={"body": "   "})
        ).status_code == 422

        updated = await client.patch(
            f"/api/v1/cases/{case_id}", json={"status": "in_review"}
        )
        assert updated.json()["status"] == "in_review"
        assert updated.json()["notes"][0]["body"] == "Reviewed flow direction."

        graph = (await client.get(f"/api/v1/cases/{case_id}/graph")).json()
        assert {item["type"] for item in graph["nodes"]} >= {"customer", "account"}
        assert any(item["type"] == "transaction" and item["highlighted"] for item in graph["edges"])

        dashboard = (await client.get("/api/v1/dashboard")).json()
        assert dashboard["total_alerts"] >= 1
        assert len(dashboard["transaction_activity"]) == 14
        assert {item["source"] for item in dashboard["source_health"]} >= {
            "internal",
            "ofac",
            "fincen",
            "mock_media",
        }


def test_milestone_four_investigation_flow():
    asyncio.run(investigator_proof())


async def no_alert_case_proof():
    Base.metadata.create_all(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run = (
            await client.post(
                "/api/v1/scenarios/normal/runs", json={"seed": 44005, "days": 30}
            )
        ).json()
        assert run["case_id"] is None
        assert (await client.get("/api/v1/cases/unknown")).status_code == 404
        assert (await client.get("/api/v1/cases", params={"status": "invalid"})).status_code == 422


def test_no_alert_does_not_create_case():
    asyncio.run(no_alert_case_proof())
