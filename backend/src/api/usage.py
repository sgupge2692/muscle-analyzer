"""
月次利用枠カウンタ（S1）— ユーザーごとの当月解析実行数をファイルで管理する。

保存先: data/usage/{user_id}_{YYYYMM}.json（内容: {"count": n}）
本番（ENV=production）で /analyze の認証必須化とセットで使う。
開発環境では強制しない（記録のみ or 無効）。
プラン（free/paid）の概念は未実装 → 現状は全ユーザー free 扱い。
上限値は仮値（要確認・commercial_open_questions Q10）。
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("uvicorn")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
USAGE_DIR   = Path(os.getenv("USAGE_DIR", str(BACKEND_DIR / "data" / "usage")))

# free プランの月次上限。**仮値**（docs/tasks/S1-S5セキュリティ設計メモ Q4: 根拠データなし・要確認）
FREE_PLAN_MONTHLY_LIMIT = int(os.getenv("FREE_PLAN_MONTHLY_LIMIT", "3"))


def _month() -> str:
    return time.strftime("%Y%m")


def _path(user_id: str, month: str) -> Path:
    return USAGE_DIR / f"{user_id}_{month}.json"


def get_count(user_id: str) -> int:
    path = _path(user_id, _month())
    if not path.exists():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("count", 0))
    except Exception as e:
        logger.warning(f"利用枠カウンタ読込失敗 user={user_id}: {e}")
        return 0


def increment(user_id: str) -> int:
    """当月カウントを+1して新しい値を返す（原子的置換書き込み）"""
    month = _month()
    path = _path(user_id, month)
    new_count = get_count(user_id) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"count": new_count, "month": month}), encoding="utf-8")
    tmp.replace(path)
    return new_count


def check_and_consume(user_id: str, limit: int | None = None) -> int:
    """上限に達していれば 429 を送出し，そうでなければ1消費する（本番のみ呼び出し想定）"""
    if limit is None:
        limit = FREE_PLAN_MONTHLY_LIMIT
    current = get_count(user_id)
    if current >= limit:
        logger.warning(f"利用枠超過: user={user_id} count={current} limit={limit}")
        raise _quota_exceeded()
    return increment(user_id)


def _quota_exceeded():
    from fastapi import HTTPException
    return HTTPException(429, "今月の無料解析回数を使い切りました。翌月に再度お試しください")


def delete_user_usage(user_id: str) -> int:
    """当該ユーザーの全月次カウンタを削除する（アカウント削除時）。削除したファイル数を返す"""
    if not USAGE_DIR.exists():
        return 0
    removed = 0
    for path in USAGE_DIR.glob(f"{user_id}_*.json"):
        try:
            path.unlink()
            removed += 1
        except OSError as e:
            logger.warning(f"利用枠カウンタ削除失敗 {path.name}: {e}")
    return removed
