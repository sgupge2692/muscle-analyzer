"""
form_checker.py
関節角度の基準値との比較によるフォーム診断モジュール

種目ごとに「理想角度範囲」を定義し、
フレームごとの角度がその範囲から外れているかどうかを判定する。
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np

# ──────────────────────────────────────────────
# 種目×関節ごとの理想角度範囲（度）
# 根拠: 各種目のバイオメカニクス先行研究に基づく
#   - スクワット: Escamilla 2001, Myer et al. 2014
#   - デッドリフト: Escamilla et al. 2000, Hales et al. 2009
#   - プッシュアップ: Cogley et al. 2005
# ──────────────────────────────────────────────
FORM_STANDARDS: dict[str, dict[str, tuple[float, float]]] = {
    # 膝角度: ボトムで70〜110°が推奨（膝の過屈曲・過伸展を防ぐ）
    # 股関節角度: ボトムで60〜100°
    # 体幹傾斜: 45°以下（前傾しすぎない）
    "Squats": {
        "right_knee":  (70.0, 110.0),   # ボトム時の推奨膝角度
        "left_knee":   (70.0, 110.0),
        "right_hip":   (60.0, 100.0),
        "left_hip":    (60.0, 100.0),
        "spine_tilt":  (0.0,  45.0),    # 体幹の前傾（0=直立）
    },
    "Squat_Hold": {
        "right_knee":  (70.0, 110.0),
        "left_knee":   (70.0, 110.0),
        "right_hip":   (60.0, 100.0),
        "left_hip":    (60.0, 100.0),
        "spine_tilt":  (0.0,  45.0),
    },
    "Jump_Squats": {
        "right_knee":  (70.0, 110.0),
        "left_knee":   (70.0, 110.0),
        "right_hip":   (60.0, 100.0),
        "left_hip":    (60.0, 100.0),
        "spine_tilt":  (0.0,  50.0),
    },
    # デッドリフト: 膝は135〜160°（スクワットより浅い）、ヒップヒンジが主体
    "Deadlift": {
        "right_knee":  (135.0, 160.0),
        "left_knee":   (135.0, 160.0),
        "right_hip":   (45.0,  90.0),
        "left_hip":    (45.0,  90.0),
        "spine_tilt":  (0.0,   30.0),   # デッドリフトは背中を丸めない
    },
    "Romanian_Deadlift": {
        "right_knee":  (150.0, 175.0),  # ほぼ伸展
        "left_knee":   (150.0, 175.0),
        "right_hip":   (30.0,  90.0),
        "left_hip":    (30.0,  90.0),
        "spine_tilt":  (0.0,   40.0),
    },
    # ランジ: 前脚膝90°、後ろ脚膝90°が理想
    "Lunges": {
        "right_knee":  (80.0, 100.0),
        "left_knee":   (80.0, 100.0),
        "spine_tilt":  (0.0,  15.0),    # 直立を維持
    },
    "Forward_Lunges": {
        "right_knee":  (80.0, 100.0),
        "left_knee":   (80.0, 100.0),
        "spine_tilt":  (0.0,  15.0),
    },
    # プッシュアップ: 肘90°がボトム、体幹は一直線
    "Push_ups": {
        "right_elbow": (80.0, 100.0),
        "left_elbow":  (80.0, 100.0),
        "spine_tilt":  (0.0,  10.0),    # 体幹を一直線に保つ
    },
    "Diamond_Pushups": {
        "right_elbow": (70.0, 90.0),    # より深く曲げる
        "left_elbow":  (70.0, 90.0),
        "spine_tilt":  (0.0,  10.0),
    },
}

# フォールバック（未定義種目用の汎用基準）
DEFAULT_STANDARD: dict[str, tuple[float, float]] = {
    "right_knee":   (70.0, 170.0),
    "left_knee":    (70.0, 170.0),
    "right_hip":    (45.0, 170.0),
    "left_hip":     (45.0, 170.0),
    "spine_tilt":   (0.0,  60.0),
    "right_elbow":  (70.0, 170.0),
    "left_elbow":   (70.0, 170.0),
}


@dataclass
class FormIssue:
    joint: str
    actual_mean: float
    ideal_min: float
    ideal_max: float
    deviation: float          # 理想範囲の端からのズレ（度）
    direction: str            # "too_small" | "too_large"
    severity: str             # "warning" | "error"
    message: str


def check_form(
    features: pd.DataFrame,
    exercise: str,
    rep_start: Optional[int] = None,
    rep_end: Optional[int] = None,
    target_angle: Optional[float] = None,
) -> list[dict]:
    """
    関節角度の理想範囲との比較によるフォーム診断

    Parameters
    ----------
    features : pd.DataFrame
        compute_angle_features() の出力
    exercise : str
        種目名（muscle_mapping.json のキー）
    rep_start, rep_end : int | None
        対象フレーム範囲（Noneの場合は全体）
    target_angle : float | None
        ユーザー設定の目標膝角度（スクワット系の理想範囲に反映）

    Returns
    -------
    list[dict]
        フォームの問題点リスト（問題なければ空リスト）
    """
    standards = FORM_STANDARDS.get(exercise, DEFAULT_STANDARD).copy()

    # ユーザー設定のtarget_angleで膝・股関節の理想範囲を動的に調整
    if target_angle is not None and exercise in ("Squats", "Squat_Hold", "Jump_Squats", "Lateral_Squats"):
        knee_margin = 20.0   # 目標角度±20°を理想範囲とする
        hip_margin  = 25.0
        standards = dict(standards)  # コピーして上書き
        for key in ("right_knee", "left_knee"):
            if key in standards:
                standards[key] = (target_angle - knee_margin, target_angle + knee_margin)
        for key in ("right_hip", "left_hip"):
            if key in standards:
                standards[key] = (target_angle - hip_margin - 10, target_angle - hip_margin + 20)

    # フレーム範囲でスライス
    if rep_start is not None and rep_end is not None:
        mask = (features.index >= rep_start) & (features.index <= rep_end)
        df = features[mask]
    else:
        df = features

    if df.empty:
        return []

    issues: list[FormIssue] = []

    for joint, (ideal_min, ideal_max) in standards.items():
        if joint not in df.columns:
            continue

        series = df[joint].dropna()
        if series.empty:
            continue

        # ボトムポジションの平均（最小値付近のフレームを対象）
        # スクワット・デッドリフトは最小角度が最も重要
        p10 = series.quantile(0.10)   # 下位10%の角度（ボトム付近）
        p90 = series.quantile(0.90)   # 上位90%の角度（トップ付近）

        # ボトム時の問題チェック
        bottom_mean = series[series <= p10 * 1.05].mean()
        if bottom_mean < ideal_min:
            dev = ideal_min - bottom_mean
            severity = "error" if dev > 20 else "warning"
            issues.append(FormIssue(
                joint=joint,
                actual_mean=round(float(bottom_mean), 1),
                ideal_min=ideal_min,
                ideal_max=ideal_max,
                deviation=round(dev, 1),
                direction="too_small",
                severity=severity,
                message=_make_message(joint, "too_small", dev, exercise),
            ))
        elif bottom_mean > ideal_max:
            dev = bottom_mean - ideal_max
            severity = "error" if dev > 20 else "warning"
            issues.append(FormIssue(
                joint=joint,
                actual_mean=round(float(bottom_mean), 1),
                ideal_min=ideal_min,
                ideal_max=ideal_max,
                deviation=round(dev, 1),
                direction="too_large",
                severity=severity,
                message=_make_message(joint, "too_large", dev, exercise),
            ))

    return [
        {
            "joint": issue.joint,
            "actual_deg": issue.actual_mean,
            "ideal_range": [issue.ideal_min, issue.ideal_max],
            "deviation_deg": issue.deviation,
            "direction": issue.direction,
            "severity": issue.severity,
            "message": issue.message,
        }
        for issue in issues
    ]


def _make_message(joint: str, direction: str, deviation: float, exercise: str) -> str:
    """日本語のフォームフィードバックメッセージを生成"""
    joint_jp = {
        "right_knee":   "右膝",
        "left_knee":    "左膝",
        "right_hip":    "右股関節",
        "left_hip":     "左股関節",
        "spine_tilt":   "体幹",
        "right_elbow":  "右肘",
        "left_elbow":   "左肘",
        "right_shoulder": "右肩",
        "left_shoulder":  "左肩",
    }
    jname = joint_jp.get(joint, joint)
    dev_str = f"{deviation:.0f}°"

    if joint in ("spine_tilt",):
        if direction == "too_large":
            return f"{jname}が前傾しすぎています（約{dev_str}過剰）。背筋を立てましょう。"
        else:
            return f"{jname}の角度が小さすぎます。"
    elif "knee" in joint:
        if direction == "too_small":
            return f"{jname}が曲がりすぎています（約{dev_str}過剰屈曲）。深く沈みすぎに注意しましょう。"
        else:
            return f"{jname}の屈曲が浅すぎます（約{dev_str}不足）。もう少し深くしゃがみましょう。"
    elif "hip" in joint:
        if direction == "too_small":
            return f"{jname}が過剰に屈曲しています（約{dev_str}）。上体を少し起こしましょう。"
        else:
            return f"{jname}の屈曲が浅いです（約{dev_str}不足）。もう少しヒップを落としましょう。"
    elif "elbow" in joint:
        if direction == "too_small":
            return f"{jname}が曲がりすぎています（約{dev_str}過剰屈曲）。"
        else:
            return f"{jname}の屈曲が浅すぎます（約{dev_str}不足）。"
    else:
        if direction == "too_small":
            return f"{jname}の角度が理想より約{dev_str}小さいです。"
        else:
            return f"{jname}の角度が理想より約{dev_str}大きいです。"
