"""
処理フローチャート（研究計画書 図3用）

研究計画書 v18 の 2.3 節「処理手順」の6ステップを作図する。
ステップ4（ルールベース一次推定）とステップ5（1D-CNN / ST-GCN による
マルチラベル分類）は並行処理として分岐・統合を描く。

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/plot_processing_flowchart.py

出力:
    docs/images/fig3_processing_flowchart.png（300dpi）・.svg

依存は requirements.txt の範囲内（matplotlib）のみ。
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BACKEND_DIR.parent / "docs" / "images"
OUTPUT_STEM = "fig3_processing_flowchart"

# 日本語ラベル用フォント（macOS: Hiragino、Windows/Linux 向けフォールバック）
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    "Noto Sans CJK JP", "Yu Gothic", "Meiryo",
]
plt.rcParams["axes.unicode_minus"] = False

# 配色（図1と共通のパレット）
C_STAGE = {"fc": "#dbe9f6", "ec": "#1f77b4"}
C_RULE = {"fc": "#fdf1dc", "ec": "#e08214"}
C_DNN = {"fc": "#e8f1fb", "ec": "#1f77b4"}
C_OUT = {"fc": "#e2f0d9", "ec": "#548235"}


def box(ax, x: float, y: float, w: float, h: float, text: str,
        style: dict, fontsize: float = 11.5) -> None:
    """角丸ボックス + 中央テキストを描画する（座標系は 0〜100）。"""
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.6,rounding_size=1.2",
                           facecolor=style["fc"], edgecolor=style["ec"],
                           linewidth=1.6, zorder=2)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, linespacing=1.5, zorder=3)


def arrow(ax, p_from: tuple[float, float], p_to: tuple[float, float]) -> None:
    """接続矢印を描画する。"""
    ax.add_patch(FancyArrowPatch(p_from, p_to,
                                 arrowstyle="-|>", mutation_scale=20,
                                 linewidth=1.8, color="#444444", zorder=1))


def line(ax, p_from: tuple[float, float], p_to: tuple[float, float]) -> None:
    """矢印なしの接続線を描画する。"""
    ax.plot([p_from[0], p_to[0]], [p_from[1], p_to[1]],
            color="#444444", lw=1.8, zorder=1)


def main() -> None:
    fig, ax = plt.subplots(figsize=(9, 9.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(25, 100)
    ax.axis("off")

    # --- ステップ1〜3: 直列処理 ---
    box(ax, 14, 89, 72, 7,
        "① フレームごとにMediaPipe Pose Landmarkerで\n33点骨格を推定（3D world座標）", C_STAGE)
    arrow(ax, (50, 88.4), (50, 83.6))
    box(ax, 14, 76, 72, 7,
        "② 関節角度（膝・股関節・肘等），角速度，\n左右非対称性など38特徴量を算出", C_STAGE)
    arrow(ax, (50, 75.4), (50, 70.6))
    box(ax, 14, 63, 72, 7,
        "③ 種目ごとのレップを関節角度の極値から自動検出", C_STAGE)

    # --- ステップ4/5: 並行処理（分岐 → 統合）---
    arrow(ax, (50, 62.4), (50, 58.0))
    line(ax, (27, 58.0), (73, 58.0))
    arrow(ax, (27, 58.0), (27, 53.6))
    arrow(ax, (73, 58.0), (73, 53.6))
    box(ax, 6, 46, 42, 7,
        "④ ルールベースモジュールで\n解剖学的知識に基づく一次推定を実施", C_RULE, fontsize=10.5)
    box(ax, 52, 46, 42, 7,
        "⑤ 1D-CNN（またはST-GCN）でレップ内の\n時系列特徴からマルチラベル分類", C_DNN, fontsize=10.5)
    arrow(ax, (27, 45.4), (27, 41.0))
    arrow(ax, (73, 45.4), (73, 41.0))
    line(ax, (27, 41.0), (73, 41.0))

    # --- ステップ6: 出力 ---
    arrow(ax, (50, 41.0), (50, 36.6))
    box(ax, 10, 29, 80, 7,
        "⑥ 推定結果を20筋群のヒートマップとして可視化，\n逸脱フレームを特定してフォームフィードバックを生成",
        C_OUT, fontsize=11)

    fig.suptitle("図3：処理フローチャート", fontsize=14, y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        out_path = OUTPUT_DIR / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(out_path, dpi=300) if suffix == "png" else fig.savefig(out_path)
        print(f"保存: {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
