"""GET /health の基本応答テスト"""
from api.main import MAPPING


def test_health_returns_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_health_lists_supported_exercises(client):
    res = client.get("/health")
    supported = res.json().get("supported_exercises")
    assert isinstance(supported, list)
    assert "Squats" in supported
    assert set(supported) == set(MAPPING["exercise_muscle_mapping"].keys())
