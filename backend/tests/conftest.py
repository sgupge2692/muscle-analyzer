"""
テスト用共通フィクスチャ。

重要: 環境変数の隔離は「fixture ではなくモジュールimport時」に行う。
pytestはテストモジュールのimport（例: test_health.py の `from api.main import MAPPING`）
をフィクスチャ実行より先に行うため、import時に .env が読み込まれて本物の
data/users.json にテストユーザーが書き込まれる事故を防ぐ。
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BACKEND_DIR, "src")

_TEST_SECRET = "test-secret-key-for-pytest-0123456789abcdef0123456789abcdef"

# ── モジュールimport時に隔離環境を構築（どのテストモジュールより先に実行される）──
_TMP = Path(tempfile.mkdtemp(prefix="ma-backend-test-"))
# .env の Supabase 設定を無効化して必ずファイルストアにする
# （空文字を先に設定しておけば _load_dotenv の setdefault は上書きしない）
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_KEY"] = ""
os.environ.setdefault("JWT_SECRET", _TEST_SECRET)
os.environ.setdefault("ENV", "development")
os.environ["USERS_DB_PATH"] = str(_TMP / "users.json")
os.environ["REFRESH_DB_PATH"] = str(_TMP / "refresh_tokens.json")
os.environ["HISTORY_DIR"] = str(_TMP / "history")
os.environ["USAGE_DIR"] = str(_TMP / "usage")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


@pytest.fixture(scope="session", autouse=True)
def _isolated_env():
    """セッション終了時に隔離ディレクトリを掃除する"""
    yield
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture()
def client(_isolated_env):
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """各テスト間で認証系のメモリ内レート制限カウンタをリセットする"""
    yield
    try:
        from api.auth import _ATTEMPTS

        _ATTEMPTS.clear()
    except Exception:
        pass


@pytest.fixture()
def register_and_login(client):
    """ユーザーを登録してAuthorizationヘッダーを返すヘルパー"""
    import uuid

    counter = {"n": 0}

    def _make(name_suffix: str = ""):
        counter["n"] += 1
        i = counter["n"]
        email = f"user{i}-{uuid.uuid4().hex[:8]}{name_suffix}@example.com"
        res = client.post(
            "/auth/register",
            json={"email": email, "password": "password1", "name": f"User{i}"},
        )
        assert res.status_code == 201, res.text
        return {"Authorization": f"Bearer {res.json()['access_token']}"}, email

    return _make
