"""
文献EMGカーブとシステム推定の整合検証スクリプト

literature_emg_curves.json の非nullエントリ（文献カーブ定義済みの種目×筋群）について:
1. 膝角度を0〜180°でスイープした合成入力を estimate_activation() に与える
2. システム推定の活動強度と文献カーブ（Task2のガウス関数）を比較
3. scipy.stats.pearsonr で Pearson の相関係数 r を計算し、結果を表示・CSV出力

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/literature_validation.py

依存は requirements.txt の範囲内（pandas / scipy）のみ。
"""
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import pearsonr

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

from anatomy.muscle_activation import (  # noqa: E402
    _angle_position_modifier,
    _load_literature_curves,
    estimate_activation,
)

OUTPUT_CSV = BACKEND_DIR / "output" / "literature_validation_results.csv"

# 角度スイープ: 0〜180°（解剖学的角度・直立=180°）
ANGLE_SWEEP = list(range(0, 181, 5))


def _synthetic_features(angles: list[float]) -> pd.DataFrame:
    """膝角度スイープに対する合成 angle_features を作る。

    角速度は0（速度ベースの変調を無効化し、角度位置依存性だけを観察する）、
    股関節は膝角度から一定の位相差を付けた典型的なスクワット連動パターン。
    """
    df = pd.DataFrame(index=range(len(angles)))
    df["right_knee"] = angles
    df["left_knee"] = angles
    df["right_hip"] = [a - 40 for a in angles]
    df["left_hip"] = [a - 40 for a in angles]
    for col in ("right_knee", "left_knee", "right_hip", "left_hip"):
        df[f"{col}_vel"] = 0.0
    return df


def main() -> None:
    curves = _load_literature_curves()
    meta = curves.pop("_meta", {})
    rows = []
    skipped = []

    for exercise, muscles in curves.items():
        for muscle, entry in muscles.items():
            if not isinstance(entry, dict):
                continue
            peak, width = entry.get("peak_angle_deg"), entry.get("width_deg")
            if peak is None or width is None:
                skipped.append((exercise, muscle, entry.get("note", "")))
                continue

            # --- システム推定: 角度スイープに対する活動強度 ---
            features = _synthetic_features([float(a) for a in ANGLE_SWEEP])
            activations = estimate_activation(features, [muscle], exercise=exercise)
            if muscle not in activations.columns:
                skipped.append((exercise, muscle, "システム出力に筋群列が存在せず"))
                continue
            system_curve = activations[muscle].to_numpy(dtype=float)

            # --- 文献カーブ: Task2のガウス関数 ---
            literature_curve = [
                _angle_position_modifier(float(a), peak, width) for a in ANGLE_SWEEP
            ]

            if system_curve.std() < 1e-12:
                r, p, note = float("nan"), float("nan"), "システム出力が一定（変調が効いていない疑い）"
            else:
                r, p = pearsonr(system_curve, literature_curve)
                note = ""

            rows.append({
                "exercise": exercise,
                "muscle": muscle,
                "source": entry.get("source"),
                "peak_angle_deg": peak,
                "width_deg": width,
                "pearson_r": round(float(r), 4),
                "p_value": round(float(p), 6),
                "n_points": len(ANGLE_SWEEP),
                "note": note,
            })

    result = pd.DataFrame(rows)
    print("=== 文献EMGカーブとシステム推定の整合検証 ===")
    if not result.empty:
        print(result.to_string(index=False))
    else:
        print("非nullの文献カーブエントリがありません")

    print("\n=== スキップしたエントリ（カーブ未定義 / null）===")
    for ex, m, note in skipped:
        print(f"  {ex}/{m}: {note}")

    if not result.empty:
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"\n保存: {OUTPUT_CSV}")

    # 判定の目安: カーブ適用が正しく配線されていれば r≈1.0
    # （システム値は文献ガウスの線形変換 0.8+0.4·g に基準重みを掛けたもの）
    if not result.empty and result["pearson_r"].notna().all():
        if (result["pearson_r"] > 0.99).all():
            print("\n判定: OK — すべての文献カーブに対してシステム推定が高整合（r>0.99）")
        else:
            print("\n判定: 要確認 — r<0.99 のペアがあります（配線またはパラメータを確認）")


if __name__ == "__main__":
    main()
