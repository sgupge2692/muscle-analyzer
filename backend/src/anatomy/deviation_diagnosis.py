"""
deviation_diagnosis.py
文献理想曲線に対する活動曲線逸脱診断とエビデンスレベル表示

研究計画書（課題C）の実装:
  - 活動曲線逸脱診断: 文献で報告された「活動ピーク角度」と、レップ内で
    システムが推定した活動ピーク時の関節角度を比較し、ずれを報告する
    （例: 大腿四頭筋の活動ピークは膝屈曲90°付近だが、浅い角度のまま
     活動が最大になった場合は可動域不足の疑い）
  - エビデンスレベル表示: 筋群ごとに、文献の角度別定量値で検証済みか
    （literature_validated），文献パラメータのみか（literature_derived），
    モデル推定のみか（model_estimate）を区別する

根拠文献:
  - Squats/Quadriceps, Squats/Gluteus: Marchetti et al. 2016
    （等尺性バックスクワット，膝屈曲20°/90°/140°のEMG比較）
  - 検知閾値（normal/watch/fix の角度帯）はヒューリスティックであり、
    研究計画書でも「検知閾値はヒューリスティック」と明記している
"""

import json
from pathlib import Path

_CURVES_CACHE: dict | None = None
_CURVES_PATH = Path(__file__).with_name("literature_emg_curves.json")

# 検知閾値（ヒューリスティック・文献値ではない。要検証）
DEVIATION_BANDS = {
    "normal": 15.0,   # |ずれ| ≤ 15°
    "watch": 30.0,    # 15° < |ずれ| ≤ 30°
    # それ以上は fix
}

# 矯正提案の文面（文献の知見に紐づく）
PROPOSALS = {
    "Squats": {
        "Quadriceps": "可動域を確保するための動作調整（しゃがみ深さを膝屈曲90°付近まで確保すると，文献上の大腿四頭筋活動ピークに近づく）",
        "Gluteus": "大臀筋は深い屈曲で活動が上がるパターンが文献で報告されている。深すぎる場合は膝角度を浅めに，浅すぎる場合は可動域を広げる調整を検討",
    },
}


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


def diagnose_peak_angle_deviation(
    activations,
    angle_series,
    exercise: str,
) -> list[dict]:
    """活動ピーク時の関節角度と文献ピーク角度のずれを診断する

    Args:
        activations: estimate_activation の出力（フレーム×筋群 DataFrame）
        angle_series: フレームごとの膝角度（解剖学的角度，直立=180°）pd.Series
        exercise: 種目名

    Returns:
        診断リスト。文献ピーク角度が定義されている筋のみ対象。
    """
    curves = _load_curves().get(exercise, {})
    if not curves or len(activations) == 0:
        return []

    # 角度系列を activations のインデックスに合わせる（欠損は前後で埋める）
    angle_aligned = angle_series.reindex(activations.index).ffill().bfill()
    if angle_aligned.isna().all():
        return []

    results = []
    for muscle, entry in curves.items():
        if not isinstance(entry, dict):
            continue
        peak = entry.get("peak_angle_deg")
        if peak is None:
            continue  # 非単調補正なし・ピーク角度未定義の筋は診断対象外

        if muscle not in activations.columns:
            continue
        series = activations[muscle]
        if series.isna().all() or float(series.max()) <= 0:
            continue

        peak_frame = int(series.to_numpy().argmax())
        observed = float(angle_aligned.iloc[peak_frame] - 180) * -1  # 膝屈曲角（0=伸展）
        # 文献の peak_angle_deg は「解剖学的角度」規約（直立=180°）。
        # 報告は直感的な「膝屈曲角」で行う（180−解剖学的角度）
        lit_flexion = 180 - peak
        dev = observed - lit_flexion

        if abs(dev) <= DEVIATION_BANDS["normal"]:
            severity = "normal"
        elif abs(dev) <= DEVIATION_BANDS["watch"]:
            severity = "watch"
        else:
            severity = "fix"

        results.append({
            "muscle": muscle,
            "observed_flexion_deg": round(observed, 1),
            "literature_flexion_deg": round(lit_flexion, 1),
            "deviation_deg": round(dev, 1),
            "severity": severity,
            "proposal": PROPOSALS.get(exercise, {}).get(muscle),
            "source": entry.get("source"),
            "evidence": evidence_level(exercise, muscle)["label"],
        })
    return results
