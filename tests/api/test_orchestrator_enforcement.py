import pytest

pytestmark = pytest.mark.unit_fast


def test_orchestrator_requires_execution_plan(api_client):
    response = api_client.post("/api/v1/orchestrator/goals", json={"goal": "Run agent"})
    assert response.status_code == 422


def test_orchestrator_accepts_goal_with_plan(api_client):
    response = api_client.post(
        "/api/v1/orchestrator/goals",
        json={"goal": "Run agent", "execution_plan": {"steps": [{"order": 1, "action": "plan"}]}},
    )
    assert response.status_code == 200
    execution_id = response.json()["id"]
    followup = api_client.get(f"/api/v1/orchestrator/executions/{execution_id}")
    assert followup.status_code == 200


def test_agents_router_has_no_direct_start(api_client):
    response = api_client.post("/api/v1/agents/ag-test/start", json={})
    assert response.status_code in {404, 405}

