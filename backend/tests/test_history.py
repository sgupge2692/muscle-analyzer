"""/history エンドポイントのテスト（研究評価では未使用・商用機能）"""

VALID_ENTRY = {
    "exercise": "Squats",
    "total_reps": 5,
    "muscles": {"Rectus Femoris": 0.42, "Gluteus Maximus": 0.61},
    "evidence_levels": {"Rectus Femoris": 2},
    "note": "テスト",
}


def test_history_requires_auth(client):
    res = client.post("/history", json=VALID_ENTRY)
    assert res.status_code == 401


def test_save_and_list_history(client, register_and_login):
    headers, _ = register_and_login()
    res = client.post("/history", json=VALID_ENTRY, headers=headers)
    assert res.status_code == 201
    entry = res.json()
    assert entry["exercise"] == "Squats"
    assert entry["id"]

    listed = client.get("/history", headers=headers)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["id"] == entry["id"]


def test_history_is_per_user(client, register_and_login):
    headers_a, _ = register_and_login()
    headers_b, _ = register_and_login()
    client.post("/history", json=VALID_ENTRY, headers=headers_a)

    listed_b = client.get("/history", headers=headers_b)
    assert listed_b.json() == []


def test_delete_history_entry(client, register_and_login):
    headers, _ = register_and_login()
    entry = client.post("/history", json=VALID_ENTRY, headers=headers).json()

    res = client.delete(f"/history/{entry['id']}", headers=headers)
    assert res.status_code == 204
    assert client.get("/history", headers=headers).json() == []
    # 二重削除は404
    assert client.delete(f"/history/{entry['id']}", headers=headers).status_code == 404


def test_history_rejects_oversized_fields(client, register_and_login):
    headers, _ = register_and_login()
    bad = dict(VALID_ENTRY, exercise="x" * 65)
    res = client.post("/history", json=bad, headers=headers)
    assert res.status_code == 422


def test_history_isolated_dirs_do_not_pollute_repo(client, register_and_login):
    """HISTORY_DIR はリポジトリ外に隔離されていること（data/history を作らない）"""
    import os
    from pathlib import Path

    headers, _ = register_and_login()
    client.post("/history", json=VALID_ENTRY, headers=headers)
    repo_history = Path(os.environ["HISTORY_DIR"]).resolve()
    repo_root = Path(__file__).resolve().parent.parent.parent
    assert repo_root not in repo_history.parents
    assert not (repo_root / "data" / "history").exists()
