"""
文献較正パイプラインの可視化（研究計画書 図5用）

「推定値 vs 文献値の角度－活動度曲線の比較（折れ線グラフ）」を作成する。

対象は literature_emg_curves.json のうち角度別の定量値（data_points）が
存在する（種目, 筋群）ペア（2026年11月時点で5組み合わせ）。
data_points が null のペアは角度位置の文献較正検証が不可能（論文に定量値が
ない）のため図示しない。

各パネル:
    - 実線: システム推定値を膝角度40〜180°でスイープ（文献の基準条件で正規化）
    - 散布: 文献の角度別EMG値（論文明記値またはΔ%から導出した近似値、同じ基準条件で正規化）
    - パネル見出しに Pearson の r を注記（n=3 のため参考値）
      r の算出手順は literature_validation.py と同一（文献角度点のみで評価）。

注意（軸の規約）:
    横軸はシステムの解剖学的関節角度（直立=180°、深屈曲=小さい値）。
    文献の膝屈曲角とは 180−屈曲角 の関係
    （屈曲20°→解剖学的160°、屈曲90°→90°、屈曲140°→40°）。
    デッドリフト（Moreira et al. 2023）のロックアウト位置は解剖学的180°。

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/plot_literature_calibration.py

出力:
    docs/images/fig5_literature_calibration.png（300dpi）・.svg

依存は requirements.txt の範囲内（matplotlib / numpy / scipy / pandas）のみ。
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))

from literature_validation import _active_muscles, _synthetic_features  # noqa: E402

from anatomy.muscle_activation import _load_literature_curves, estimate_activation  # noqa: E402

OUTPUT_DIR = BACKEND_DIR.parent / "docs" / "images"
OUTPUT_STEM = "fig5_literature_calibration"

# 日本語ラベル用フォント（macOS: Hiragino、Windows/Linux 向けフォールバック）
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    "Noto Sans CJK JP", "Yu Gothic", "Meiryo",
]
plt.rcParams["axes.unicode_minus"] = False

# スイープ範囲: 解剖学的膝角度 40°（=文献の屈曲140°）〜180°（直立・ロックアウト）
SWEEP_ANGLES = np.arange(40, 181, 1)

# パネル表記用の日本語名
EXERCISE_JA = {"Squats": "スクワット", "Deadlift": "デッドリフト"}
MUSCLE_JA = {
    "Quadriceps": "大腿四頭筋",
    "Gluteus": "大臀筋",
    "Hamstring": "ハムストリング",
    "Lower_Back": "脊柱起立筋",
}
# パネルの並び順（行1: スクワット, 行2: デッドリフト）
PANEL_ORDER = [
    ("Squats", "Quadriceps"),
    ("Squats", "Gluteus"),
    ("Deadlift", "Quadriceps"),
    ("Deadlift", "Hamstring"),
    ("Deadlift", "Lower_Back"),
]


def plot_pair(ax: plt.Axes, exercise: str, muscle: str, entry: dict, mapping: dict) -> float:
    """1つの（種目, 筋群）ペアの比較曲線を ax に描画し、Pearson の r を返す。"""
    points = entry["data_points"]["points"]
    lit_angles = np.array([float(p["angle_deg"]) for p in points])
    lit_values = np.array([float(p["value"]) for p in points])

    # --- 正規化の基準: 文献の基準条件（値が最大の角度点）---
    # literature_validation.py と同じ手順で、双方を基準条件で正規化する
    ref_idx = int(np.argmax(lit_values))
    ref_value = lit_values[ref_idx]
    lit_norm = lit_values / ref_value if ref_value > 0 else lit_values

    # --- システム推定のスイープ（検証スクリプトと同じ合成特徴量）---
    features = _synthetic_features(list(SWEEP_ANGLES))
    active = _active_muscles(mapping, exercise, muscle)
    activations = estimate_activation(features, active, exercise=exercise)
    system_sweep = activations[muscle].to_numpy(dtype=float)

    # --- 文献角度点でのシステム値と Pearson の r（検証スクリプトと同じ手順）---
    feat_at_lit = _synthetic_features(list(lit_angles))
    act_at_lit = estimate_activation(feat_at_lit, active, exercise=exercise)
    sys_at_lit = act_at_lit[muscle].to_numpy(dtype=float)
    sys_ref = sys_at_lit[ref_idx]
    sweep_ref = system_sweep[SWEEP_ANGLES.searchsorted(lit_angles[ref_idx])]
    sys_ref_sweep = sweep_ref if sweep_ref > 0 else system_sweep.max()
    system_norm_sweep = system_sweep / sys_ref_sweep if sys_ref_sweep > 0 else system_sweep
    if sys_ref > 0:
        sys_at_lit_norm = sys_at_lit / sys_ref
    else:
        sys_at_lit_norm = sys_at_lit / sys_at_lit.max()

    r, _ = pearsonr(sys_at_lit_norm, lit_norm)

    ax.plot(SWEEP_ANGLES, system_norm_sweep, color="#1f77b4", lw=2,
            label="システム推定値（正規化）")
    ax.scatter(lit_angles, lit_norm, color="#d62728", zorder=5, s=45,
               label="文献EMG値（正規化）")

    panel_title = f"{EXERCISE_JA[exercise]}／{MUSCLE_JA[muscle]}（r = {r:.3f}, n={len(points)}）"
    ax.set_title(panel_title, fontsize=12)
    ax.set_xlabel("解剖学的膝関節角度（°）：大きいほど伸展（直立=180°）")
    ax.set_ylabel("正規化筋活動度")
    ax.set_xlim(30, 190)
    ax.set_ylim(0, 1.15)
    ax.grid(True, alpha=0.3)
    return float(r)


def main() -> None:
    curves = _load_literature_curves()
    curves.pop("_meta", None)

    mapping_path = BACKEND_DIR / "data" / "muscle_mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}

    # 図示可能（data_points が存在する）ペアのみ対象
    available = {
        (exercise, muscle)
        for exercise, muscles in curves.items()
        for muscle, entry in muscles.items()
        if isinstance(entry, dict)
        and isinstance(entry.get("data_points"), dict)
        and entry["data_points"].get("points")
    }
    pairs = [(ex, m) for ex, m in PANEL_ORDER if (ex, m) in available]
    if not pairs:
        raise SystemExit("data_points を持つエントリが存在しないため作図できない")

    # 2行×3列: 行1=スクワット（2パネル+全体凡例）、行2=デッドリフト（3パネル）
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.6), squeeze=False)
    r_values: dict[tuple[str, str], float] = {}
    # パネル配置: (行, 列) → (種目, 筋群)。(0,2) は全体凡例用に空ける
    positions = [(0, 0), (0, 1), (1, 0), (1, 1), (1, 2)]
    for (row, col), (exercise, muscle) in zip(positions, pairs, strict=False):
        ax = axes[row][col]
        entry = curves[exercise][muscle]
        r_values[(exercise, muscle)] = plot_pair(ax, exercise, muscle, entry, mapping)
        if r_values[(exercise, muscle)] < 0.6:
            ax.text(0.98, 0.02,
                    "低整合：深屈曲側を過大評価\n（対称ガウスの設計限界、再較正は未実施）",
                    transform=ax.transAxes, ha="right", va="bottom",
                    fontsize=8, color="#7f2704")

    # 空けた(0,2)に全体凡例を配置
    legend_ax = axes[0][2]
    legend_ax.axis("off")
    handles, labels = axes[0][0].get_legend_handles_labels()
    legend_ax.legend(handles, labels, loc="center", fontsize=13, frameon=True)

    fig.suptitle("図5：推定値と文献値の角度－活動度曲線の比較（スクワット・デッドリフト，5組み合わせ）",
                 fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.95))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        out_path = OUTPUT_DIR / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(out_path, dpi=300) if suffix == "png" else fig.savefig(out_path)
        print(f"保存: {out_path}")
    plt.close(fig)

    # 検算用: r 値を summary CSV と突き合わせて表示
    summary_path = BACKEND_DIR / "output" / "literature_validation_summary.csv"
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        print("\n=== literature_validation_summary.csv との整合確認 ===")
        for _, row in summary.iterrows():
            key = (row["exercise"], row["muscle"])
            if key in r_values:
                match = "一致" if abs(r_values[key] - row["pearson_r"]) < 5e-4 else "不一致"
                print(f"  {key[0]}/{key[1]}: 図 r={r_values[key]:.4f} / CSV r={row['pearson_r']} → {match}")


if __name__ == "__main__":
    main()
