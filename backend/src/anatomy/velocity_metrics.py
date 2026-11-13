"""
velocity_metrics.py
動画ベース疲労指標（velocity loss）とフォーム妥当性フィルタ

研究計画書（課題D）の実装:
  - velocity loss: Sánchez-Medina & González-Badillo (2011) の定義に沿い，
    セット内の初回レップの平均同心収縮速度を基準に，以降のレップの
    速度低下率を算出する
  - フォーム妥当性フィルタ: check_form で逸脱が指摘されたレップを
    疲労指標・1RM推定の対象から除外する（研究計画書の条件比較用）

重要な測定上の限界（論文で明記すること）:
  - 本システムが動画から直接得られるのは「関節角速度」であり，
    バーベル速度（m/s）ではない。velocity loss は無次元の低下率なので
    角速度プロキシでも方向性は保たれるが，絶対速度を要求する1RM推定には
    角速度→線形速度の変換が必要で，これは本モジュールでは行わない
    （# TODO: 要文献確認。体幹長・脚長からの変換の妥当性検証が未着手）
  - したがって 1RM 推定は，利用者が負荷とバーベル速度を入力した場合のみ
    二点法（V1T）で実行する設計とする
"""

import pandas as pd


def rep_angular_velocities(angles: pd.Series, reps: list[dict]) -> list[dict]:
    """レップごとの同心収縮相の平均角速度（deg/frame）を計算する

    同心収縮相 = ボトム（最小角度）→ 立位側（end）の持ち上げ区間。
    角速度が正（伸展方向）になることを前提とする。
    """
    out = []
    for r in reps:
        bottom, end = r["bottom"], r["end"]
        if end <= bottom:
            continue
        n_frames = end - bottom
        if n_frames <= 0:
            continue
        delta = float(angles.iloc[end] - angles.iloc[bottom])
        out.append({
            "rep": r["rep"],
            "mean_concentric_velocity_deg_per_frame": round(delta / n_frames, 4),
            "frames": n_frames,
        })
    return out


def velocity_loss(velocities: list[dict]) -> dict | None:
    """初回レップを基準とした速度低下率（%）

    定義: loss_rep_i = (1 - v_i / v_1) × 100
    文献: Sánchez-Medina & González-Badillo 2011; Pareja-Blanco et al. 2017
    """
    if len(velocities) < 2:
        return None
    v1 = velocities[0]["mean_concentric_velocity_deg_per_frame"]
    if v1 <= 0:
        return None
    per_rep = []
    for v in velocities[1:]:
        loss = (1 - v["mean_concentric_velocity_deg_per_frame"] / v1) * 100
        per_rep.append({"rep": v["rep"], "velocity_loss_pct": round(loss, 1)})
    return {
        "reference_rep": velocities[0]["rep"],
        "per_rep": per_rep,
        "final_loss_pct": per_rep[-1]["velocity_loss_pct"],
        "definition": "1 - v_i / v_1（初回レップ基準）",
        "literature": "Sánchez-Medina & González-Badillo 2011; Pareja-Blanco et al. 2017",
        "note": "動画から得た関節角速度のプロキシ値（バーベル速度ではない）",
    }


def filter_form_valid_reps(reps: list[dict], form_feedback: dict) -> tuple[list[dict], list[int]]:
    """フォーム逸脱レップを除外する（フォーム妥当性フィルタ）

    form_feedback のキーは rep_N 形式。逸脱が指摘されたレップを除外し，
    除外されたレップ番号を返す。
    """
    excluded = []
    for r in reps:
        if f"rep_{r['rep']}" in form_feedback:
            excluded.append(r["rep"])
    if not excluded:
        return list(reps), []
    valid = [r for r in reps if f"rep_{r['rep']}" not in form_feedback]
    return valid, excluded


def estimate_1rm_two_point(load_velocity_pairs: list[tuple[float, float]],
                           v1rm: float | None = None,
                           exercise: str = "") -> dict | None:
    """負荷-速度関係の線形外挿による1RM推定（二点法）

    Args:
        load_velocity_pairs: [(負荷kg, 平均同心収縮速度 m/s), ...] 2点以上
        v1rm: 1RM挙上時の推定速度（m/s）。種目別の文献値が確定していないため
              # TODO: 要文献確認（確定するまで None 指定時は推定不可で返す）

    Returns:
        {"load_velocity_relationship": 線形回帰係数, "estimated_1rm_kg": 推定値}
    """
    if v1rm is None:
        return {
            "estimated_1rm_kg": None,
            "note": "1RM挙上時の基準速度（v1RM）の種目別文献値が未確定のため推定不可。# TODO: 要文献確認",
        }
    if len(load_velocity_pairs) < 2:
        return {
            "estimated_1rm_kg": None,
            "note": "負荷-速度関係の外挿には異なる負荷のデータが2点以上必要",
        }
    xs = [float(x) for x, _ in load_velocity_pairs]
    ys = [float(y) for _, y in load_velocity_pairs]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom <= 0:
        return None
    b = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom
    a = y_mean - b * x_mean
    if b >= 0:
        return None  # 負荷が増えて速度が上がる関係は負荷-速度関係として不成立
    est_1rm = (v1rm - a) / b
    return {
        "estimated_1rm_kg": round(est_1rm, 1),
        "intercept_v0": round(a, 3),
        "slope": round(b, 5),
        "v1rm_used": v1rm,
        "n_points": len(xs),
        "literature": "負荷-速度関係の線形性: González-Badillo & Sánchez-Medina 2010",
        "note": "速度は利用者入力のバーベル速度（m/s）。動画由来の角速度ではない",
    }
