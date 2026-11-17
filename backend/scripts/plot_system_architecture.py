"""
提案システムの全体構成図（研究計画書 図1用）

研究計画書 v18 の 2.1 節「システム全体構成」のテキスト図に基づき、
入力 → 骨格推定 → 特徴量抽出 → ハイブリッド推定（ルールベース + 深層学習）
→ ヒートマップ可視化 → フォームフィードバック の6段構成を作図する。

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/plot_system_architecture.py

出力:
    docs/images/fig1_system_architecture.png（300dpi）・.svg

依存は requirements.txt の範囲内（matplotlib）のみ。
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BACKEND_DIR.parent / "docs" / "images"
OUTPUT_STEM = "fig1_system_architecture"

# 日本語ラベル用フォント（macOS: Hiragino、Windows/Linux 向けフォールバック）
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    "Noto Sans CJK JP", "Yu Gothic", "Meiryo",
]
plt.rcParams["axes.unicode_minus"] = False

# 配色（印刷に耐える淡色 + 濃い枠線）
C_INPUT = {"fc": "#eeeeee", "ec": "#666666"}
C_STAGE = {"fc": "#dbe9f6", "ec": "#1f77b4"}
C_HYBRID = {"fc": "#fdf1dc", "ec": "#e08214"}
C_RULE = {"fc": "#ffffff", "ec": "#e08214"}
C_DNN = {"fc": "#ffffff", "ec": "#1f77b4"}
C_OUT = {"fc": "#e2f0d9", "ec": "#548235"}


def box(ax, x: float, y: float, w: float, h: float, text: str,
        style: dict, fontsize: float = 12, weight: str = "bold") -> None:
    """角丸ボックス + 中央テキストを描画する（座標系は 0〜100）。"""
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.6,rounding_size=1.2",
                           facecolor=style["fc"], edgecolor=style["ec"],
                           linewidth=1.6, zorder=2)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, fontweight=weight, zorder=3)


def arrow(ax, x: float, y_from: float, y_to: float) -> None:
    """縦方向の接続矢印を描画する。"""
    ax.add_patch(FancyArrowPatch((x, y_from), (x, y_to),
                                 arrowstyle="-|>", mutation_scale=22,
                                 linewidth=1.8, color="#444444", zorder=1))


def stage_label(ax, y: float, text: str) -> None:
    """左端に処理段階名を添える。"""
    ax.text(2, y, text, ha="left", va="center", fontsize=10,
            color="#888888", fontweight="bold")


def main() -> None:
    fig, ax = plt.subplots(figsize=(9.5, 11.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    cx = 50  # 中央
    bw = 62  # 主要ボックス幅

    # --- 1. 動画入力 ---
    box(ax, cx - bw / 2, 90, bw, 7, "動画入力（アップロード / リアルタイム）", C_INPUT)
    stage_label(ax, 93.5, "入力")
    arrow(ax, cx, 89.4, 85.0)

    # --- 2. 骨格推定 ---
    box(ax, cx - bw / 2, 77, bw, 8,
        "MediaPipe Pose Landmarker\n（骨格検出・33点3D座標）", C_STAGE, fontsize=11.5)
    stage_label(ax, 81, "骨格推定")
    arrow(ax, cx, 76.4, 71.5)

    # --- 3. 特徴量抽出 ---
    box(ax, cx - bw / 2, 63, bw, 8,
        "特徴量エンジン\n（関節角度・速度・非対称性 計38特徴量）", C_STAGE, fontsize=11.5)
    stage_label(ax, 67, "特徴量抽出")

    # --- 4. ハイブリッド推定モジュール（外枠 + 2サブモジュール + 統合）---
    box(ax, 8, 33, 84, 25, "", C_HYBRID)
    ax.text(50, 54.5, "ハイブリッド推定モジュール", ha="center", va="center",
            fontsize=12.5, fontweight="bold", color="#8c5a00", zorder=3)
    # 特徴量エンジン → 2サブモジュールへ分岐
    arrow(ax, 30, 62.4, 51.0)
    arrow(ax, 70, 62.4, 51.0)
    ax.plot([30, 70], [62.4, 62.4], color="#444444", lw=1.8, zorder=1)
    box(ax, 13, 42.5, 32, 7, "ルールベース\n（解剖学モデル × 関節角度）", C_RULE, fontsize=10.5, weight="normal")
    box(ax, 55, 42.5, 32, 7, "深層学習\n（1D-CNN / ST-GCN）", C_DNN, fontsize=10.5, weight="normal")
    arrow(ax, 29, 42.0, 39.0)
    arrow(ax, 71, 42.0, 39.0)
    box(ax, 30, 35.5, 40, 4.2, "統合（融合）", C_HYBRID, fontsize=10.5)
    stage_label(ax, 45.5, "筋活動推定")
    arrow(ax, cx, 32.4, 27.5)

    # --- 5. ヒートマップ可視化 ---
    box(ax, cx - bw / 2, 19, bw, 8,
        "筋肉動態ヒートマップ可視化\n（Next.js / Canvas API）", C_OUT, fontsize=11.5)
    stage_label(ax, 23, "可視化")
    arrow(ax, cx, 18.4, 13.5)

    # --- 6. フォームフィードバック ---
    box(ax, cx - bw / 2, 5, bw, 8,
        "フォーム矯正フィードバック\n（テキスト + 3Dアバター）", C_OUT, fontsize=11.5)
    stage_label(ax, 9, "フィードバック")

    fig.suptitle("図1：提案システムの全体構成", fontsize=14, y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        out_path = OUTPUT_DIR / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(out_path, dpi=300) if suffix == "png" else fig.savefig(out_path)
        print(f"保存: {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
