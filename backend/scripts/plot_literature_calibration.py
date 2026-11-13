"""
文献較正パイプラインの可視化（研究計画書 図5用）

「推定値 vs 文献値の角度－活動度曲線の比較（折れ線グラフ）」を作成する。

対象は literature_emg_curves.json のうち角度別の定量値（data_points）が
存在する（種目, 筋群）ペアのみ。data_points が null のペアは角度位置の
文献較正検証が不可能（論文に定量値がない）のため図示しない。

各パネル:
    - 実線: システム推定値を膝角度40〜160°でスイープし、ピーク=1.0で正規化
    - 散布: 文献の角度別EMG値（論文Δ%から導出した近似値、ピーク=1.0で正規化）
    - パネル見出しに Pearson の r を注記（n=3 のため参考値）

注意（軸の規約）:
    横軸はシステムの解剖学的関節角度（直立=180°、深屈曲=小さい値）。
    文献（Marchetti et al. 2016）の膝屈曲角とは 180−屈曲角 の関係
    （屈曲20°→解剖学的160°、屈曲90°→90°、屈曲140°→40°）。

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/plot_literature_calibration.py

出力:
    output/literature_calibration_fig5.png（300dpi）

依存は requirements.txt の範囲内（matplotlib / numpy / scipy / pandas）のみ。
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))

from anatomy.muscle_activation import _load_literature_curves, estimate_activation  # noqa: E402
from literature_validation import _active_muscles, _synthetic_features  # noqa: E402

OUTPUT_PNG = BACKEND_DIR / "output" / "literature_calibration_fig5.png"

# 日本語ラベル用フォント（macOS: Hiragino、Windows/Linux 向けフォールバック）
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    "Noto Sans CJK JP", "Yu Gothic", "Meiryo",
]
plt.rcParams["axes.unicode_minus"] = False

# スイープ範囲: 解剖学的膝角度 40°（=文献の屈曲140°）〜160°（=屈曲20°）
SWEEP_ANGLES = np.arange(40, 161, 1)


def plot_pair(ax: plt.Axes, exercise: str, muscle: str, entry: dict, mapping: dict) -> float:
    """1つの（種目, 筋群）ペアの比較曲線を ax に描画し、Pearson の r を返す。"""
    points = entry["data_points"]["points"]
    angles_lit = [float(p["angle_deg"]) for p in points]
    lit_values = np.array([float(p["value"]) for p in points])
    lit_norm = lit_values / lit_values.max()

    # --- システム推定のスイープ（検証スクリプトと同じ合成特徴量）---
    features = _synthetic_features(list(SWEEP_ANGLES))
    active = _active_muscles(mapping, exercise, muscle)
    activations = estimate_activation(features, active, exercise=exercise)
    system_sweep = activations[muscle].to_numpy(dtype=float)
    system_norm = system_sweep / system_sweep.max()

    # --- 文献値と同じ角度での Pearson の r（検証スクリプトと同じ手順）---
    lit_angles = np.array(angles_lit)
    sys_at_lit = system_norm[SWEEP_ANGLES.searchsorted(lit_angles)]
    r, _ = pearsonr(sys_at_lit, lit_norm)

    ax.plot(SWEEP_ANGLES, system_norm, color="#1f77b4", lw=2,
            label="システム推定値（正規化）")
    ax.scatter(lit_angles, lit_norm, color="#d62728", zorder=5, s=45,
               label="文献EMG値（Δ%から導出・正規化）")

    ax.set_title(f"{exercise} / {muscle}（Pearson r = {r:.3f}, n={len(points)}）")
    ax.set_xlabel("解剖学的膝関節角度（°）：大きいほど伸展（直立=180°）")
    ax.set_ylabel("正規化筋活動度")
    ax.set_xlim(30, 170)
    ax.set_ylim(0, 1.15)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)
    return float(r)


def main() -> None:
    curves = _load_literature_curves()
    curves.pop("_meta", None)

    mapping_path = BACKEND_DIR / "data" / "muscle_mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}

    # 図示可能（data_points が存在する）ペアのみ対象
    pairs = [
        (exercise, muscle, entry)
        for exercise, muscles in curves.items()
        for muscle, entry in muscles.items()
        if isinstance(entry, dict)
        and isinstance(entry.get("data_points"), dict)
        and entry["data_points"].get("points")
    ]
    if not pairs:
        raise SystemExit("data_points を持つエントリが存在しないため作図できない")

    fig, axes = plt.subplots(1, len(pairs), figsize=(6.2 * len(pairs), 4.8), squeeze=False)
    for ax, (exercise, muscle, entry) in zip(axes[0], pairs):
        r = plot_pair(ax, exercise, muscle, entry, mapping)
        if r < 0.6:
            ax.text(0.98, 0.02,
                    "低整合：深屈曲側を過大評価\n（対称ガウスの設計限界、再較正は未実施）",
                    transform=ax.transAxes, ha="right", va="bottom",
                    fontsize=8, color="#7f2704")

    fig.suptitle("図5：推定値と文献値の角度－活動度曲線の比較（スクワット）", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=300)
    plt.close(fig)
    print(f"保存: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
