"""
auth.py — JWT認証 + bcryptパスワードハッシュ化モジュール

フロー:
  1. POST /auth/register → パスワードをbcryptでハッシュ化してDBに保存
  2. POST /auth/login    → パスワードを検証してJWTを発行
  3. GET  /auth/me       → JWTを検証してユーザー情報を返す
  4. 保護エンドポイントは Depends(get_current_user) で認証を要求

ユーザー保存先: SUPABASE_URL / SUPABASE_SERVICE_KEY があればSupabase、なければJSONファイル（ローカル開発用）

セキュリティ設計:
  - パスワード: bcrypt(cost=12) でハッシュ化（平文は保存しない）
  - JWT: HS256, 有効期限60分（リフレッシュトークンは別途実装予定）
  - JWTシークレット: 環境変数 JWT_SECRET から取得（必須）
  - レート制限: /auth/login・/auth/register は IPごとに5回/分（メモリ内の簡易実装）
"""
import asyncio
import os
import json
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import hashlib
import hmac
import base64 as _b64
import time
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger("muscle_analyzer.auth")

# ── 設定 ────────────────────────────────────────────────────
JWT_SECRET      = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_MIN  = int(os.getenv("JWT_EXPIRE_MIN", "60"))
BCRYPT_COST     = 12  # 2^12 = 4096回ハッシュ（十分な計算コスト）

# ユーザーDBのパス（本番はPostgreSQL等に移行予定、現在はJSONファイル）
BACKEND_DIR   = Path(__file__).resolve().parent.parent.parent
USERS_DB_PATH = Path(os.getenv("USERS_DB_PATH", str(BACKEND_DIR / "data" / "users.json")))

_INSECURE_SECRETS = {"", "your-super-secret-key-change-this-in-production"}


def _require_secret() -> None:
    """JWT_SECRET が未設定・サンプル値・短すぎる場合は認証機能を無効化する（トークン偽造を防ぐ）"""
    if JWT_SECRET in _INSECURE_SECRETS or len(JWT_SECRET) < 32:
        raise HTTPException(503, "認証機能が正しく設定されていません（JWT_SECRET）")


if JWT_SECRET in _INSECURE_SECRETS or len(JWT_SECRET) < 32:
    logger.error("JWT_SECRET が未設定または脆弱です。認証API（/auth/*）は無効化されます")

security = HTTPBearer(auto_error=False)
router   = APIRouter(prefix="/auth", tags=["auth"])


# ── Pydanticモデル ───────────────────────────────────────────
class RegisterRequest(BaseModel):
    email:    EmailStr
    password: str
    name:     str = ""

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上にしてください")
        if not any(c.isdigit() for c in v):
            raise ValueError("パスワードに数字を1文字以上含めてください")
        if not any(c.isalpha() for c in v):
            raise ValueError("パスワードに英字を1文字以上含めてください")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int = JWT_EXPIRE_MIN * 60


class UserResponse(BaseModel):
    id:    str
    email: str
    name:  str


# ── bcryptパスワードハッシュ ─────────────────────────────────
def _hash_password(password: str) -> str:
    """
    bcryptでパスワードをハッシュ化する。

    bcryptは標準ライブラリにないため、
    まずbcryptパッケージを試みて、なければPBKDF2-SHA256(標準)にフォールバックする。

    bcrypt推奨理由: GPU並列攻撃に耐性がある（PBKDF2はGPUで並列化可能）
    """
    try:
        import bcrypt
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_COST))
        return "bcrypt:" + hashed.decode()
    except ImportError:
        # フォールバック: PBKDF2-SHA256（bcrypt未インストール時）
        salt = os.urandom(16).hex()
        dk   = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return f"pbkdf2:{salt}:{dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """ハッシュ化済みパスワードと平文パスワードを照合する"""
    if stored.startswith("bcrypt:"):
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode(), stored[7:].encode())
        except ImportError:
            return False
    elif stored.startswith("pbkdf2:"):
        _, salt, dk_stored = stored.split(":", 2)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        # タイミング攻撃対策: hmac.compare_digestで定数時間比較
        return hmac.compare_digest(dk.hex(), dk_stored)
    return False


# ── JWT（標準ライブラリのみ、PyJWT不要） ──────────────────────
def _b64url_encode(data: bytes) -> str:
    return _b64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return _b64.urlsafe_b64decode(s + "=" * (pad % 4))


def _create_jwt(payload: dict) -> str:
    _require_secret()
    header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body    = _b64url_encode(json.dumps(payload).encode())
    sig_input = f"{header}.{body}".encode()
    sig     = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def _verify_jwt(token: str) -> dict:
    _require_secret()
    try:
        header, body, sig = token.split(".")
        sig_input = f"{header}.{body}".encode()
        expected  = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(sig), expected):
            raise HTTPException(401, "トークンが無効です")
        payload = json.loads(_b64url_decode(body))
        if payload.get("exp", 0) < time.time():
            raise HTTPException(401, "トークンの有効期限が切れています")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "トークンが無効です")


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRE_MIN * 60,
    }
    return _create_jwt(payload)


# ── ユーザーストア ───────────────────────────────────────────
# SUPABASE_URL と SUPABASE_SERVICE_KEY があればSupabase(PostgREST)、
# なければJSONファイル（ローカル開発用）に保存する。
_FILE_LOCK = threading.Lock()


def _load_users() -> dict:
    if not USERS_DB_PATH.exists():
        return {}
    with open(USERS_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_DB_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    os.replace(tmp, USERS_DB_PATH)  # 書き込み途中で落ちてもファイルが壊れないよう原子的に置換


def _norm_email(email: str) -> str:
    """メールは小文字に正規化（A@x.com と a@x.com を別ユーザーにしない）"""
    return email.strip().lower()


class _FileUserStore:
    """JSONファイル保存。ローカル開発用（Railway等ではデプロイのたびに消える）"""

    def find_by_email(self, email: str) -> Optional[dict]:
        with _FILE_LOCK:
            return next((u for u in _load_users().values() if u["email"].lower() == email), None)

    def get(self, user_id: str) -> Optional[dict]:
        with _FILE_LOCK:
            return _load_users().get(user_id)

    def create(self, user: dict) -> bool:
        """作成できたらTrue、メール重複ならFalse"""
        with _FILE_LOCK:
            users = _load_users()
            if any(u["email"].lower() == user["email"] for u in users.values()):
                return False
            users[user["id"]] = user
            _save_users(users)
            return True

    def update_password(self, user_id: str, hashed: str) -> None:
        with _FILE_LOCK:
            users = _load_users()
            if user_id in users:
                users[user_id]["password"] = hashed
                _save_users(users)

    def delete(self, user_id: str) -> None:
        with _FILE_LOCK:
            users = _load_users()
            if users.pop(user_id, None) is not None:
                _save_users(users)


class _SupabaseUserStore:
    """Supabase(PostgREST)保存。標準ライブラリのみで実装（追加依存なし）。
    service_roleキーを使うため、必ずサーバー側の環境変数でのみ扱い、フロントに渡さないこと。"""

    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1/users"
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, query: str = "", body: Optional[dict] = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + query, data=data, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                raw = res.read()
                return res.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw) if raw else None
            except ValueError:
                payload = None
            return e.code, payload
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.error(f"Supabase接続エラー: {e}")
            raise HTTPException(503, "ユーザーDBに接続できません。しばらくしてからお試しください")

    @staticmethod
    def _fail(status: int, payload) -> None:
        # ログにはエラーコードとメッセージのみ（行の中身＝個人情報・ハッシュは出さない）
        code = payload.get("code") if isinstance(payload, dict) else None
        msg  = payload.get("message") if isinstance(payload, dict) else None
        logger.error(f"Supabaseエラー status={status} code={code} message={msg}")
        raise HTTPException(503, "ユーザーDBでエラーが発生しました")

    def _select(self, column: str, value: str) -> Optional[dict]:
        q = f"?{column}=eq.{urllib.parse.quote(value, safe='')}&select=*&limit=1"
        status, rows = self._request("GET", q)
        if status != 200:
            self._fail(status, rows)
        return rows[0] if rows else None

    def find_by_email(self, email: str) -> Optional[dict]:
        return self._select("email", email)

    def get(self, user_id: str) -> Optional[dict]:
        return self._select("id", user_id)

    def create(self, user: dict) -> bool:
        status, payload = self._request("POST", "", user)
        if status in (200, 201, 204):
            return True
        if status == 409:  # 一意制約違反（メール重複）
            return False
        self._fail(status, payload)

    def update_password(self, user_id: str, hashed: str) -> None:
        q = f"?id=eq.{urllib.parse.quote(user_id, safe='')}"
        status, payload = self._request("PATCH", q, {"password": hashed})
        if status not in (200, 204):
            self._fail(status, payload)

    def delete(self, user_id: str) -> None:
        q = f"?id=eq.{urllib.parse.quote(user_id, safe='')}"
        status, payload = self._request("DELETE", q)
        if status not in (200, 204):
            self._fail(status, payload)


_WARNED_FILE_STORE = False


def _get_store():
    global _WARNED_FILE_STORE
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if url and key:
        return _SupabaseUserStore(url, key)
    if os.getenv("ENV", "development") == "production" and not _WARNED_FILE_STORE:
        logger.warning("本番環境で SUPABASE_URL / SUPABASE_SERVICE_KEY が未設定です。"
                       "ユーザー情報はデプロイのたびに消えます")
        _WARNED_FILE_STORE = True
    return _FileUserStore()


# ── タイミング攻撃対策用ダミーハッシュ ──────────────────────
# 存在しないメールでもbcrypt検証を1回走らせ、応答時間の差でユーザー有無を推測させない
_DUMMY_HASH: Optional[str] = None


def _get_dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = _hash_password(os.urandom(16).hex())
    return _DUMMY_HASH


# ── 簡易レート制限（IPごと・メモリ内） ──────────────────────
# 制限: 単一プロセス内のみ有効（再起動でリセット／複数インスタンス間では共有されない）。
# login・register・change-password の合計で数える。
# X-Forwarded-For は偽装可能なので、本格運用ではRedis等＋プロキシ側制限に移行すること。
_ATTEMPTS: dict[str, list[float]] = {}


def _check_rate_limit(request: Request, limit: int = 5, window: int = 60) -> None:
    fwd = request.headers.get("x-forwarded-for", "")
    ip  = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    now = time.time()
    hits = [t for t in _ATTEMPTS.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        logger.warning(f"レート制限: {ip}")
        raise HTTPException(429, "試行回数が多すぎます。1分ほど待ってからお試しください")
    hits.append(now)
    _ATTEMPTS[ip] = hits


# ── 認証依存関係 ─────────────────────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """JWTを検証して現在のユーザーを返す（Depends で使用）"""
    if not credentials:
        raise HTTPException(401, "認証が必要です")
    payload = _verify_jwt(credentials.credentials)
    user = await asyncio.to_thread(_get_store().get, payload["sub"])
    if not user:
        raise HTTPException(401, "ユーザーが見つかりません")
    return user


# ── ルーター ─────────────────────────────────────────────────
# bcrypt・DBアクセスはブロッキング処理なので asyncio.to_thread で別スレッドに逃がす
# （同じサーバーで動くWebSocketのリアルタイム解析をログイン処理で止めないため）
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request):
    """新規ユーザー登録（パスワードはbcryptでハッシュ化して保存）"""
    _require_secret()
    _check_rate_limit(request)
    email = _norm_email(body.email)
    store = _get_store()

    if await asyncio.to_thread(store.find_by_email, email):
        raise HTTPException(409, "このメールアドレスはすでに登録されています")

    hashed  = await asyncio.to_thread(_hash_password, body.password)
    user_id = secrets.token_hex(8)
    user = {
        "id":         user_id,
        "email":      email,
        "name":       body.name,
        "password":   hashed,   # 平文は保存しない
        "created_at": int(time.time()),
    }
    if not await asyncio.to_thread(store.create, user):
        raise HTTPException(409, "このメールアドレスはすでに登録されています")

    logger.info(f"新規ユーザー登録: id={user_id}")
    return TokenResponse(access_token=create_access_token(user_id, email))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """ログイン（パスワード検証してJWT発行）"""
    _require_secret()
    _check_rate_limit(request)
    email = _norm_email(body.email)
    user  = await asyncio.to_thread(_get_store().find_by_email, email)

    # タイミング攻撃対策: ユーザー有無にかかわらず必ずbcrypt検証を1回実行する
    stored_pw   = user["password"] if user else await asyncio.to_thread(_get_dummy_hash)
    password_ok = await asyncio.to_thread(_verify_password, body.password, stored_pw)

    if not user or not password_ok:
        ip = request.client.host if request.client else "unknown"
        logger.warning(f"ログイン失敗 from {ip}")
        raise HTTPException(401, "メールアドレスまたはパスワードが間違っています")

    logger.info(f"ログイン成功: id={user['id']}")
    return TokenResponse(access_token=create_access_token(user["id"], user["email"]))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """現在のユーザー情報を返す"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user.get("name", ""),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """アクセストークンを更新する（有効なトークンが必要）"""
    logger.info(f"トークン更新: id={current_user['id']}")
    return TokenResponse(access_token=create_access_token(current_user["id"], current_user["email"]))


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上にしてください")
        if not any(c.isdigit() for c in v):
            raise ValueError("パスワードに数字を1文字以上含めてください")
        if not any(c.isalpha() for c in v):
            raise ValueError("パスワードに英字を1文字以上含めてください")
        return v


@router.post("/change-password", status_code=200)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """パスワードを変更する（現在のパスワード確認が必要）"""
    _check_rate_limit(request)
    ok = await asyncio.to_thread(_verify_password, body.current_password, current_user["password"])
    if not ok:
        raise HTTPException(401, "現在のパスワードが間違っています")
    hashed = await asyncio.to_thread(_hash_password, body.new_password)
    await asyncio.to_thread(_get_store().update_password, current_user["id"], hashed)
    logger.info(f"パスワード変更: id={current_user['id']}")
    return {"message": "パスワードを変更しました"}


@router.delete("/account", status_code=200)
async def delete_account(current_user: dict = Depends(get_current_user)):
    """アカウントを削除する"""
    await asyncio.to_thread(_get_store().delete, current_user["id"])
    logger.info(f"アカウント削除: id={current_user['id']}")
    return {"message": "アカウントを削除しました"}
