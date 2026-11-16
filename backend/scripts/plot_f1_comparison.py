"""
F1比較実験の可視化（研究計画書 図4用）

「各条件のF1 micro値比較（棒グラフ）」を作成する。
データは f1_comparison_test.csv（evaluate_f1_comparison.py の出力）。
計画書の表と同じ3条件（ルールベースのみ／1D-CNNのみ／ハイブリッド）を
F1 micro・F1 macro の2指標で比較し、成功基準（F1 micro ≥ 0.93）を
破線で示す。

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/plot_f1_comparison.py

出力:
    docs/images/fig4_f1_comparison.png（300dpi）・.svg

依存は requirements.txt の範囲内（matplotlib / pandas）のみ。
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BACKEND_DIR.parent / "docs" / "images"
OUTPUT_STEM = "fig4_f1_comparison"

# 日本語ラベル用フォント（macOS: Hiragino、Windows/Linux 向けフォールバック）
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    "Noto Sans CJK JP", "Yu Gothic", "Meiryo",
]
plt.rcParams["axes.unicode_minus"] = False

# 計画書の表と同じ3条件（CSV の condition 名 → 表示名）
CONDITIONS = [
    ("A_rule_mapping_only", "ルールベースのみ\n（基準重み）"),
    ("C_1dcnn", "1D-CNNのみ"),
    ("D_hybrid", "ハイブリッド\n（提案手法）"),
]
TARGET_F1_MICRO = 0.93  # 成功基準
COLOR_MICRO = "#1f77b4"
COLOR_MACRO = "#ff7f0e"


def main() -> None:
    csv_path = BACKEND_DIR / "output" / "f1_comparison_test.csv"
    df = pd.read_csv(csv_path)
    sub = df.set_index("condition").loc[[c for c, _ in CONDITIONS]]

    n_samples = int(sub["n_samples"].iloc[0])
    micro = sub["f1_micro"].to_numpy(dtype=float)
    macro = sub["f1_macro"].to_numpy(dtype=float)
    labels = [label for _, label in CONDITIONS]

    x = np.arange(len(CONDITIONS))
    width = 0.36

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars_micro = ax.bar(x - width / 2, micro, width, color=COLOR_MICRO,
                        label="F1 micro")
    bars_macro = ax.bar(x + width / 2, macro, width, color=COLOR_MACRO,
                        label="F1 macro")

    for bars, values in ((bars_micro, micro), (bars_macro, macro)):
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.008,
                    f"{value:.3f}", ha="center", va="bottom", fontsize=10)

    # 成功基準（F1 micro ≥ 0.93）
    ax.axhline(TARGET_F1_MICRO, color="#d62728", ls="--", lw=1.2, zorder=0)
    ax.text(-0.42, TARGET_F1_MICRO + 0.008,
            f"成功基準: F1 micro {TARGET_F1_MICRO} 以上",
            color="#d62728", fontsize=9, ha="left", va="bottom")

    ax.set_xticks(x, labels)
    ax.set_ylabel("F1スコア")
    ax.set_ylim(0, 1.09)
    ax.set_title(f"図4：各条件のF1スコア比較（MuscleMapラベル付き評価セット test_seen {n_samples:,}サンプル）",
                 fontsize=12)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="lower right", fontsize=10)

    fig.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        out_path = OUTPUT_DIR / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(out_path, dpi=300) if suffix == "png" else fig.savefig(out_path)
        print(f"保存: {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
