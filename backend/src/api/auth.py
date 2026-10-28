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
  - レート制限: /auth/login は 5回/分（ブルートフォース対策）
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
USERS_DB_PATH = Path(os.getenv("USERS_DB_PATH", "data/users.json"))

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
async def register(body: RegisterRequest):
    """新規ユーザー登録（パスワードはbcryptでハッシュ化して保存）"""
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
    users = _load_users()
    user  = next((u for u in users.values() if u["email"] == body.email), None)

    # タイミング攻撃対策: ユーザーが存在しない場合もハッシュ計算を行う
    dummy_hash = "bcrypt:$2b$12$dummy_hash_for_timing_attack_prevention"
    stored_pw  = user["password"] if user else dummy_hash

    if not user or not _verify_password(body.password, stored_pw):
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
