"""
解析履歴API — ログインユーザーごとの解析結果スナップショットを保存・取得・削除する。

保存先: data/history/{user_id}.json（配列・新しい順・上限200件）
本番はSupabaseテーブルへの移行を想定（ファイルストアは現行のauthと同じ形態）。
研究評価には使用しない（商用ブランチ専用機能）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import get_current_user

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/history", tags=["history"])

MAX_ENTRIES = 200
MAX_MUSCLES = 25
MAX_EVIDENCE = 25


class HistoryEntryIn(BaseModel):
    exercise: str = Field(..., min_length=1, max_length=64)
    total_reps: int = Field(..., ge=0, le=999)
    muscles: dict[str, float] = Field(default_factory=dict)   # 筋群 -> 全レップ平均
    evidence_levels: dict[str, int] = Field(default_factory=dict)  # 筋群 -> level
    note: Optional[str] = Field(None, max_length=500)


class HistoryEntryOut(HistoryEntryIn):
    id: str
    saved_at: int


def _history_dir() -> Path:
    d = Path(os.getenv("HISTORY_DIR", "data/history"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(user_id: str) -> list[dict]:
    path = _history_dir() / f"{user_id}.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except Exception as e:
        logger.warning(f"履歴ファイル読込失敗 user={user_id}: {e}")
        return []


def _save(user_id: str, entries: list[dict]) -> None:
    path = _history_dir() / f"{user_id}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _check_rate_limit(user_id: str, limit: int = 30, window: float = 60.0) -> None:
    now = time.monotonic()
    hits = [h for h in _HITS.get(user_id, []) if now - h < window]
    if len(hits) >= limit:
        raise HTTPException(429, "保存回数が多すぎます。1分ほど待ってからお試しください")
    hits.append(now)
    _HITS[user_id] = hits


_HITS: dict[str, list[float]] = {}


@router.post("", response_model=HistoryEntryOut, status_code=201)
async def save_entry(
    body: HistoryEntryIn,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """解析結果のスナップショットを履歴に保存する"""
    _check_rate_limit(user["id"])

    muscles = {k: float(v) for k, v in list(body.muscles.items())[:MAX_MUSCLES]}
    evidence = {k: int(v) for k, v in list(body.evidence_levels.items())[:MAX_EVIDENCE]}

    entry = {
        "id":              uuid.uuid4().hex[:12],
        "saved_at":        int(time.time()),
        "exercise":        body.exercise,
        "total_reps":      body.total_reps,
        "muscles":         muscles,
        "evidence_levels": evidence,
        "note":            body.note,
    }

    def _write() -> list[dict]:
        entries = _load(user["id"])
        entries.insert(0, entry)
        entries = entries[:MAX_ENTRIES]
        _save(user["id"], entries)
        return entries

    await asyncio.to_thread(_write)
    logger.info(f"履歴保存: user={user['id']} exercise={body.exercise}")
    return entry


@router.get("", response_model=list[HistoryEntryOut])
async def list_entries(
    request: Request,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """履歴を新しい順に返す（上限 MAX_ENTRIES）"""
    limit = max(1, min(limit, MAX_ENTRIES))
    entries = await asyncio.to_thread(_load, user["id"])
    return entries[:limit]


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """指定した履歴エントリを削除する"""
    def _delete() -> bool:
        entries = _load(user["id"])
        kept = [e for e in entries if e.get("id") != entry_id]
        if len(kept) == len(entries):
            return False
        _save(user["id"], kept)
        return True

    deleted = await asyncio.to_thread(_delete)
    if not deleted:
        raise HTTPException(404, "該当する履歴が見つかりません")
    logger.info(f"履歴削除: user={user['id']} entry={entry_id}")
