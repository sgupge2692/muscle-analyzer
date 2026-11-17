"""/auth/* エンドポイントのテスト（JWT_SECRETはconftestで注入済み）"""

REGISTER_URL = "/auth/register"


def test_register_creates_user_and_returns_token(client):
    res = client.post(
        REGISTER_URL,
        json={"email": "new@example.com", "password": "password1", "name": "Taro"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    # リフレッシュトークンCookieが発行されていること
    assert "ma_refresh" in res.cookies


def test_register_rejects_weak_passwords(client):
    for weak in ["short1", "onlyletters", "12345678"]:
        res = client.post(
            REGISTER_URL,
            json={"email": f"weak-{weak}@example.com", "password": weak},
        )
        assert res.status_code == 422, f"password={weak} は弾かれるべき"


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "password1"}
    assert client.post(REGISTER_URL, json=payload).status_code == 201
    assert client.post(REGISTER_URL, json=payload).status_code == 409


def test_register_normalizes_email_case(client):
    assert client.post(REGISTER_URL, json={"email": "Case@example.com", "password": "password1"}).status_code == 201
    res = client.post(REGISTER_URL, json={"email": "case@EXAMPLE.com", "password": "password1"})
    assert res.status_code == 409


def test_login_success_and_me(client):
    client.post(REGISTER_URL, json={"email": "login@example.com", "password": "password1"})
    res = client.post("/auth/login", json={"email": "login@example.com", "password": "password1"})
    assert res.status_code == 200
    token = res.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "login@example.com"


def test_login_wrong_password(client):
    client.post(REGISTER_URL, json={"email": "badpw@example.com", "password": "password1"})
    res = client.post("/auth/login", json={"email": "badpw@example.com", "password": "password2"})
    assert res.status_code == 401


def test_me_requires_token(client):
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_rejects_tampered_token(client):
    client.post(REGISTER_URL, json={"email": "tamper@example.com", "password": "password1"})
    res = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401


def test_refresh_rotates_token(client):
    client.post(REGISTER_URL, json={"email": "refresh@example.com", "password": "password1"})
    # 登録時に払い出されたリフレッシュCookieを使って更新
    res = client.post("/auth/refresh")
    assert res.status_code == 200
    assert res.json()["access_token"]
    # 旧Cookieはローテーションで失効済み → 再使用すると401（盗難検知）
    client.cookies.clear()
    assert client.post("/auth/refresh").status_code == 401


def test_logout_revokes_refresh_token(client):
    client.post(REGISTER_URL, json={"email": "logout@example.com", "password": "password1"})
    assert client.post("/auth/logout").status_code == 200
    client.cookies.clear()
    assert client.post("/auth/refresh").status_code == 401


def test_change_password_then_login_with_new(client):
    client.post(REGISTER_URL, json={"email": "chpw@example.com", "password": "password1"})
    login = client.post("/auth/login", json={"email": "chpw@example.com", "password": "password1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = client.post(
        "/auth/change-password",
        json={"current_password": "password1", "new_password": "password2"},
        headers=headers,
    )
    assert res.status_code == 200

    new_login = client.post("/auth/login", json={"email": "chpw@example.com", "password": "password2"})
    assert new_login.status_code == 200


def test_delete_account_cleans_up_session(client):
    reg = client.post(REGISTER_URL, json={"email": "delete@example.com", "password": "password1"})
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    res = client.delete("/auth/account", headers=headers)
    assert res.status_code == 200
    # 削除後は同一トークンでもう使えない
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_require_secret_blocks_insecure_config(monkeypatch):
    """JWT_SECRETが未設定/脆弱な場合は _require_secret が503を送出する"""
    import pytest
    from fastapi import HTTPException

    import api.auth as auth_mod

    for bad in ["", "your-super-secret-key-change-this-in-production", "short"]:
        monkeypatch.setattr(auth_mod, "JWT_SECRET", bad)
        with pytest.raises(HTTPException) as exc_info:
            auth_mod._require_secret()
        assert exc_info.value.status_code == 503

    monkeypatch.setattr(auth_mod, "JWT_SECRET", "a" * 32)
    auth_mod._require_secret()  # 例外が出ないこと
