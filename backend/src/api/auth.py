"""
auth.py — JWT認証 + bcryptパスワードハッシュ化モジュール

フロー:
  1. POST /auth/register → パスワードをbcryptでハッシュ化してDBに保存
  2. POST /auth/login    → パスワードを検証してJWTを発行
  3. GET  /auth/me       → JWTを検証してユーザー情報を返す
  4. 保護エンドポイントは Depends(get_current_user) で認証を要求

セキュリティ設計:
  - パスワード: bcrypt(cost=12) でハッシュ化（平文は保存しない）
  - JWT: HS256, 有効期限60分（リフレッシュトークンは別途実装予定）
  - JWTシークレット: 環境変数 JWT_SECRET から取得（必須）
  - レート制限: /auth/login・/auth/register は IPごとに5回/分（メモリ内の簡易実装）
"""
import os
import json
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
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET 環境変数が設定されていません")
    header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body    = _b64url_encode(json.dumps(payload).encode())
    sig_input = f"{header}.{body}".encode()
    sig     = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def _verify_jwt(token: str) -> dict:
    if not JWT_SECRET:
        raise HTTPException(500, "サーバー設定エラー")
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


# ── ユーザーDB（JSONファイル） ───────────────────────────────
def _load_users() -> dict:
    if not USERS_DB_PATH.exists():
        return {}
    with open(USERS_DB_PATH) as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_DB_PATH, "w") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)



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
    users   = _load_users()
    user    = users.get(payload["sub"])
    if not user:
        raise HTTPException(401, "ユーザーが見つかりません")
    return user


# ── ルーター ─────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request):
    """新規ユーザー登録（パスワードはbcryptでハッシュ化して保存）"""
    _check_rate_limit(request)
    users = _load_users()

    # メールアドレス重複チェック
    if any(u["email"] == body.email for u in users.values()):
        raise HTTPException(409, "このメールアドレスはすでに登録されています")

    user_id       = hashlib.sha256(f"{body.email}{time.time()}".encode()).hexdigest()[:16]
    hashed_pw     = _hash_password(body.password)

    users[user_id] = {
        "id":         user_id,
        "email":      body.email,
        "name":       body.name,
        "password":   hashed_pw,   # 平文は保存しない
        "created_at": int(time.time()),
    }
    _save_users(users)
    logger.info(f"新規ユーザー登録: {body.email}")

    token = create_access_token(user_id, body.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """ログイン（パスワード検証してJWT発行）"""
    _check_rate_limit(request)
    users = _load_users()
    user  = next((u for u in users.values() if u["email"] == body.email), None)

    # タイミング攻撃対策: ユーザー有無にかかわらず必ずbcrypt検証を1回実行する
    stored_pw   = user["password"] if user else _get_dummy_hash()
    password_ok = _verify_password(body.password, stored_pw)

    if not user or not password_ok:
        logger.warning(f"ログイン失敗: {body.email} from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(401, "メールアドレスまたはパスワードが間違っています")

    logger.info(f"ログイン成功: {body.email}")
    token = create_access_token(user["id"], user["email"])
    return TokenResponse(access_token=token)


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
    """
    アクセストークンを更新する（有効なトークンが必要）

    クライアントはトークン期限切れ前にこのエンドポイントを叩き、
    新しいトークンを取得する。
    """
    token = create_access_token(current_user["id"], current_user["email"])
    logger.info(f"トークン更新: {current_user['email']}")
    return TokenResponse(access_token=token)


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
    current_user: dict = Depends(get_current_user),
):
    """パスワードを変更する（現在のパスワード確認が必要）"""
    if not _verify_password(body.current_password, current_user["password"]):
        raise HTTPException(401, "現在のパスワードが間違っています")

    users = _load_users()
    users[current_user["id"]]["password"] = _hash_password(body.new_password)
    _save_users(users)
    logger.info(f"パスワード変更: {current_user['email']}")
    return {"message": "パスワードを変更しました"}


@router.delete("/account", status_code=200)
async def delete_account(current_user: dict = Depends(get_current_user)):
    """アカウントを削除する"""
    users = _load_users()
    if current_user["id"] in users:
        del users[current_user["id"]]
        _save_users(users)
    logger.info(f"アカウント削除: {current_user['email']}")
    return {"message": "アカウントを削除しました"}
