"""
文献EMG測定値とシステム推定の整合検証スクリプト

literature_emg_curves.json の data_points（論文に明記された角度別EMG数値、
または本文明記のΔ%から算術導出した相対値）を「正解データ」として、
システムの推定値と直接比較する。

注意（循環検証の回避）:
    ガウス関数のパラメータ（peak_angle_deg / width_deg）は比較対象に
    使わない。ガウス関数はシステム内部で data_points と独立に近似値と
    して使われているパラメータであり、これを正解とすると必ず r≈1.0 に
    なる循環検証になるため。

data_points=null の筋群は「論文に角度別の定量値がなく検証不可」として
報告する（根拠のない数値で代用しない）。

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/literature_validation.py

依存は requirements.txt の範囲内（pandas / scipy）のみ。
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

from anatomy.muscle_activation import _load_literature_curves, estimate_activation  # noqa: E402

OUTPUT_CSV = BACKEND_DIR / "output" / "literature_validation_results.csv"
OUTPUT_SUMMARY_CSV = BACKEND_DIR / "output" / "literature_validation_summary.csv"


def _synthetic_features(angles: list[float]) -> pd.DataFrame:
    """指定膝角度での合成 angle_features を作る。

    角速度は0（速度ベースの変調を無効化し、角度位置依存性だけを観察する）。
    股関節は膝角度から一定オフセットとした典型的な連動パターン。
    検証対象の Quadriceps/Gluteus の文献変調は膝角度のみで決まるため、
    股関節オフセットの選び方は検証結果に影響しない。
    """
    df = pd.DataFrame(index=range(len(angles)))
    df["right_knee"] = angles
    df["left_knee"] = angles
    df["right_hip"] = [a - 40 for a in angles]
    df["left_hip"] = [a - 40 for a in angles]
    for col in ("right_knee", "left_knee", "right_hip", "left_hip"):
        df[f"{col}_vel"] = 0.0
    return df


def _active_muscles(mapping: dict, exercise: str, fallback: str) -> list[str]:
    """muscle_mapping.json から対象種目の筋群リストを取得（正規化を実際のシステムと一致させる）"""
    ids = mapping.get("exercise_muscle_mapping", {}).get(exercise, [])
    groups = mapping.get("muscle_groups", {})
    muscles = [groups[str(i)] for i in ids if str(i) in groups]
    return muscles or [fallback]


def main() -> None:
    curves = _load_literature_curves()
    curves.pop("_meta", None)

    mapping_path = BACKEND_DIR / "data" / "muscle_mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}

    detail_rows = []
    summary_rows = []
    impossible = []

    for exercise, muscles in curves.items():
        for muscle, entry in muscles.items():
            if not isinstance(entry, dict):
                continue
            dp = entry.get("data_points")
            points = dp.get("points") if isinstance(dp, dict) else None

            # --- 検証不可の報告（論文に角度別の定量値がない等）---
            if not points:
                reason = (dp.get("validation_note") if isinstance(dp, dict) else None) \
                    or entry.get("validation_note") or entry.get("note", "")
                impossible.append({"exercise": exercise, "muscle": muscle, "reason": reason})
                continue

            angles = [float(p["angle_deg"]) for p in points]
            literature = np.array([float(p["value"]) for p in points])

            # --- システム推定: 正解データと同じ角度のみで評価 ---
            features = _synthetic_features(angles)
            active = _active_muscles(mapping, exercise, muscle)
            activations = estimate_activation(features, active, exercise=exercise)
            if muscle not in activations.columns:
                impossible.append({"exercise": exercise, "muscle": muscle,
                                   "reason": "システム出力に筋群列が存在せず"})
                continue
            system_raw = activations[muscle].to_numpy(dtype=float)

            # --- 正規化: 文献の基準条件（相対値が最大の点）で双方を正規化 ---
            # 文献値が %MVC 等の絶対スケールでも基準条件で除算することで同一スケールに揃える
            # （Pearson r はアフィン変換に不変だが、誤差列の比較には単位統一が必須）
            ref_idx = int(np.argmax(literature))
            ref_value = literature[ref_idx]
            lit_norm = literature / ref_value if ref_value > 0 else literature
            system_norm = system_raw / system_raw[ref_idx] if system_raw[ref_idx] > 0 else system_raw

            # --- Pearson の r（正解データ vs システム推定）---
            if system_raw.std() < 1e-12:
                r, p_val, note = float("nan"), float("nan"), "システム出力が一定（変調が効いていない疑い）"
            else:
                r, p_val = pearsonr(system_norm, lit_norm)
                note = "n=3 の相関は参考値（角度別定量点が3点しかないため）" if len(points) == 3 else ""

            max_abs_err = float(np.nanmax(np.abs(system_norm - lit_norm)))
            summary_rows.append({
                "exercise": exercise,
                "muscle": muscle,
                "source": entry.get("source"),
                "n_points": len(points),
                "pearson_r": round(float(r), 4) if r == r else r,
                "p_value": round(float(p_val), 6) if p_val == p_val else p_val,
                "max_abs_error_norm": round(max_abs_err, 4),
                "note": note,
            })

            for i, p in enumerate(points):
                detail_rows.append({
                    "exercise": exercise,
                    "muscle": muscle,
                    "angle_deg": p["angle_deg"],
                    "knee_flexion_deg": p.get("knee_flexion_deg"),
                    "system_activation_raw": round(float(system_raw[i]), 4),
                    "system_norm": round(float(system_norm[i]), 4),
                    "literature_raw": float(p["value"]),
                    "literature_norm": round(float(lit_norm[i]), 4),
                    "error_norm": round(float(system_norm[i] - float(lit_norm[i])), 4),
                    "source": entry.get("source"),
                    "data_point_note": p.get("note", ""),
                })

    # --- 結果表示 ---
    print("=== 文献EMG測定値（data_points）とシステム推定の整合検証 ===")
    print("（ガウス関数の peak/width は比較対象外 — 循環検証防止）\n")
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        print(summary.to_string(index=False))
    else:
        print("角度別の定量値（data_points）が存在するエントリはありません")

    print("\n=== 検証不可のエントリ（論文に角度別の定量値がない）===")
    for row in impossible:
        print(f"  {row['exercise']}/{row['muscle']}: {row['reason']}")

    detail = pd.DataFrame(detail_rows)
    if not detail.empty:
        print("\n=== 角度ごとの比較詳細 ===")
        print(detail.to_string(index=False))

    if not detail.empty:
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        detail.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"\n保存: {OUTPUT_CSV}")
    if not summary.empty:
        OUTPUT_SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(OUTPUT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
        print(f"保存: {OUTPUT_SUMMARY_CSV}")

    # --- 判定の目安 ---
    if not summary.empty:
        valid = summary[summary["pearson_r"].notna()]
        for _, row in valid.iterrows():
            label = "高整合" if row["pearson_r"] >= 0.9 else \
                "部分整合" if row["pearson_r"] >= 0.7 else "低整合（ガウス近似パラメータの見直し候補）"
            print(f"\n判定 [{row['exercise']}/{row['muscle']}]: "
                  f"r={row['pearson_r']} → {label}")


if __name__ == "__main__":
    main()
