"""
evidence_level.py
文献較正パイプラインの正式な成果物：筋群ごとのエビデンスレベル表示

literature_emg_curves.json の較正データに基づき，筋群ごとに以下を返す:
  literature_validated : 文献の角度別定量値で検証済み
  literature_derived   : 文献パラメータのみ（角度別定量値なし）
  literature_referenced: 文献が参照先として記録されている（角度別定量値なし）
  model_estimate       : モデル推定のみ
"""

import json
from pathlib import Path

_CURVES_CACHE: dict | None = None
_CURVES_PATH = Path(__file__).with_name("literature_emg_curves.json")


def _load_curves() -> dict:
    global _CURVES_CACHE
    if _CURVES_CACHE is None:
        try:
            _CURVES_CACHE = json.loads(_CURVES_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _CURVES_CACHE = {}
    return _CURVES_CACHE


def evidence_level(exercise: str, muscle: str) -> dict:
    """筋群のエビデンスレベルを返す

    level:
      2 = literature_validated（文献の角度別定量値で検証済み）
      1 = literature_derived（文献由来のパラメータのみ・角度別定量値なし）
      0 = model_estimate（モデル推定のみ。文献が参照先として記録されている
          場合は label が literature_referenced になる）
    """
    entry = _load_curves().get(exercise, {}).get(muscle)
    if not isinstance(entry, dict):
        return {"level": 0, "label": "model_estimate", "source": None, "note": None}
    dp = entry.get("data_points")
    has_points = isinstance(dp, dict) and bool(dp.get("points"))
    if has_points:
        label = "literature_validated"
    elif entry.get("peak_angle_deg") is not None:
        label = "literature_derived"
    elif entry.get("source"):
        label = "literature_referenced"
    else:
        label = "model_estimate"
    return {
        "level": 2 if label == "literature_validated" else (1 if label == "literature_derived" else 0),
        "label": label,
        "source": entry.get("source"),
        "note": entry.get("note"),
    }
