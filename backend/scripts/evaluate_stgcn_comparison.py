"""
ST-GCN移行比較の評価スクリプト（計画ファイル2-A: マイルストーン2の比較条件拡張）

evaluate_f1_comparison.py（制度化済みの3条件比較）と同じ手順・分割・プロトコルで，
ST-GCN を比較条件に加えた版:
    条件A: ルールベースのみ（種目×筋群マッピングのみ。角度変調なし）
    条件B: ルールベース＋角度変調（val_seen で閾値選択）
    条件C: 1D-CNNのみ（best_1dcnn.pt，閾値0.5）
    条件D: ハイブリッド（ルールベース＋1D-CNN 融合，val_seen で重み・閾値選択）
    条件E: ST-GCNのみ（best_stgcn.pt，閾値0.5）★本スクリプトで追加
    条件F: ハイブリッド（ルールベース＋ST-GCN 融合，val_seen で重み・閾値選択）★同上

手順の原則（evaluate_f1_comparison.py と同一）:
    - 角度変調・融合の閾値は val_seen で選択し，test_seen でのみ最終評価する
    - split は train.py / train_stgcn.py の split_indices と同じ規約
    - ST-GCN の重みは train_stgcn.py（現行アーキテクチャ）で学習したもの
      （旧チェックポイントはアーキテクチャ互換が無いため使用しない）

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/evaluate_stgcn_comparison.py

依存は requirements.txt ＋ torch（学習用。requirements.txt 未ピン。結果メモ参照）。
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
sys.path.insert(0, str(BACKEND_DIR / "src" / "ml"))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from dataset import MuscleMapDataset  # noqa: E402
from evaluate_f1_comparison import (  # noqa: E402
    CNN_THRESHOLD,
    CNN_WEIGHTS,
    DEVICE,
    FUSION_THRESHOLDS,
    FUSION_WEIGHTS,
    LABELED_PKL,
    RULE_THRESHOLDS,
    SKL_DIR,
    _cnn_probs,
    binarize,
    f1_metrics,
    load_mapping,
    rule_scores,
    split_indices,
)
from stgcn import STGCN  # noqa: E402

STGCN_WEIGHTS = BACKEND_DIR / "output/best_stgcn.pt"
OUTPUT_SUMMARY = BACKEND_DIR / "output/f1_comparison_stgcn_test.csv"
OUTPUT_TUNING = BACKEND_DIR / "output/f1_comparison_stgcn_val_thresholds.csv"
OUTPUT_PER_MUSCLE = BACKEND_DIR / "output/stgcn_per_muscle_test.csv"
OUTPUT_CONFUSION = BACKEND_DIR / "output/stgcn_confusion_test.csv"
CACHE_RULE_VAL = BACKEND_DIR / "output/_cache_rule_val.npz"
CACHE_RULE_TEST = BACKEND_DIR / "output/_cache_rule_test.npz"

STGCN_THRESHOLD = 0.5        # 学習時と同じ固定閾値（1D-CNN に準拠）
STGCN_BATCH = 64


def stgcn_probs(model: STGCN, dataset: MuscleMapDataset, indices: list[int]) -> np.ndarray:
    """指定インデックスのST-GCN確率 (N,20) を計算（バッチ推論・CPU）"""
    import torch

    model.eval()
    probs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(indices), STGCN_BATCH):
            chunk = indices[start:start + STGCN_BATCH]
            x = torch.stack([dataset[i][0] for i in chunk])
            logits = model(x)
            probs.append(torch.sigmoid(logits).numpy())
    return np.concatenate(probs, axis=0).astype(np.float32)


def per_muscle_metrics(
    preds: np.ndarray, labels: np.ndarray, groups: dict,
) -> list[dict]:
    """筋群別の混同行列（TP/FP/FN/TN）と precision / recall / F1 を計算する

    列 c は筋肉ID c（groups[str(c)] が筋群名）に対応する。
    正例が1件も無い筋群は precision / recall / F1 を NaN とする（f1_metrics の
    macro 計算での除外規約に合わせる）。
    """
    rows = []
    for c in range(labels.shape[1]):
        p_c, l_c = preds[:, c], labels[:, c]
        tp = float((p_c * l_c).sum())
        fp = float((p_c * (1 - l_c)).sum())
        fn = float(((1 - p_c) * l_c).sum())
        tn = float(((1 - p_c) * (1 - l_c)).sum())
        if tp + fn == 0:
            precision = recall = f1 = float("nan")
        else:
            precision = tp / (tp + fp + 1e-8)
            recall = tp / (tp + fn + 1e-8)
            f1 = 2 * precision * recall / (precision + recall + 1e-8)
        rows.append({
            "muscle_id": c,
            "muscle_name": groups.get(str(c), str(c)),
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        })
    return rows


def main() -> None:
    emm, groups = load_mapping()

    with open(LABELED_PKL, "rb") as f:
        samples = pickle.load(f)
    _, val_idx, test_idx = split_indices(samples)
    print(f"val_seen: {len(val_idx)}, test_seen: {len(test_idx)}")

    # ── ルールベース側の活動度（11/13実施分と同一プロトコルのキャッシュ）──
    if CACHE_RULE_VAL.exists() and CACHE_RULE_TEST.exists():
        c_val = np.load(CACHE_RULE_VAL)
        c_test = np.load(CACHE_RULE_TEST)
        rule_val, labels_val = c_val["scores"], c_val["labels"]
        rule_test, labels_test = c_test["scores"], c_test["labels"]
        print("ルールベース活動度をキャッシュから読み込み")
    else:
        print("キャッシュ無し → 再計算します")
        rule_val, labels_val = rule_scores(samples, val_idx, emm, groups)
        rule_test, labels_test = rule_scores(samples, test_idx, emm, groups)
        np.savez(CACHE_RULE_VAL, scores=rule_val, labels=labels_val)
        np.savez(CACHE_RULE_TEST, scores=rule_test, labels=labels_test)

    # ── 深層学習モデルの確率 ──
    print("1D-CNN推論中...")
    import torch
    from model import MuscleClassifier1DCNN  # noqa: E402

    cnn = MuscleClassifier1DCNN()
    cnn.load_state_dict(torch.load(CNN_WEIGHTS, map_location=DEVICE, weights_only=True))
    cnn.eval()

    print("ST-GCN推論中...")
    stgcn = STGCN()
    stgcn.load_state_dict(torch.load(STGCN_WEIGHTS, map_location="cpu", weights_only=True))

    eval_dataset = MuscleMapDataset(LABELED_PKL, SKL_DIR, augment=False)
    cnn_val = _cnn_probs(cnn, eval_dataset, val_idx)
    cnn_test = _cnn_probs(cnn, eval_dataset, test_idx)
    gcn_val = stgcn_probs(stgcn, eval_dataset, val_idx)
    gcn_test = stgcn_probs(stgcn, eval_dataset, test_idx)

    # ── val_seen で角度変調閾値・融合重み・融合閾値を選択 ──
    tuning_rows = []
    for t in RULE_THRESHOLDS:
        m_b = f1_metrics(binarize(rule_val, t), labels_val)
        for w in FUSION_WEIGHTS:
            h_cnn = w * rule_val + (1 - w) * cnn_val
            h_gcn = w * rule_val + (1 - w) * gcn_val
            for ft in FUSION_THRESHOLDS:
                m_h_cnn = f1_metrics(binarize(h_cnn, ft), labels_val)
                m_h_gcn = f1_metrics(binarize(h_gcn, ft), labels_val)
                tuning_rows.append({
                    "rule_threshold": t,
                    "fusion_weight_rule": w,
                    "fusion_threshold": ft,
                    "val_f1_micro_rule": round(m_b["f1_micro"], 4),
                    "val_f1_micro_hybrid_cnn": round(m_h_cnn["f1_micro"], 4),
                    "val_f1_micro_hybrid_stgcn": round(m_h_gcn["f1_micro"], 4),
                })
    tuning = pd.DataFrame(tuning_rows)

    best_rule_t = float(tuning.loc[tuning["val_f1_micro_rule"].idxmax(), "rule_threshold"])
    idx_cnn = tuning["val_f1_micro_hybrid_cnn"].idxmax()
    idx_gcn = tuning["val_f1_micro_hybrid_stgcn"].idxmax()
    best_w_cnn = float(tuning.loc[idx_cnn, "fusion_weight_rule"])
    best_t_cnn = float(tuning.loc[idx_cnn, "fusion_threshold"])
    best_w_gcn = float(tuning.loc[idx_gcn, "fusion_weight_rule"])
    best_t_gcn = float(tuning.loc[idx_gcn, "fusion_threshold"])
    print("\n[val_seen での選択]")
    print(f"  角度変調閾値: {best_rule_t}")
    print(f"  hybrid(ルール+CNN): 融合重み(ルール側)={best_w_cnn}, 融合閾値={best_t_cnn}")
    print(f"  hybrid(ルール+STGCN): 融合重み(ルール側)={best_w_gcn}, 融合閾値={best_t_gcn}")

    # ── test_seen での最終評価 ──
    mapping_test = rule_test.copy()
    mapping_test[rule_test > 0] = 1.0
    conditions = {
        "A_rule_mapping_only": mapping_test,
        "B_rule_angle_mod": binarize(rule_test, best_rule_t),
        "C_1dcnn": binarize(cnn_test, CNN_THRESHOLD),
        "D_hybrid_rule_cnn": binarize(best_w_cnn * rule_test + (1 - best_w_cnn) * cnn_test, best_t_cnn),
        "E_stgcn": binarize(gcn_test, STGCN_THRESHOLD),
        "F_hybrid_rule_stgcn": binarize(best_w_gcn * rule_test + (1 - best_w_gcn) * gcn_test, best_t_gcn),
    }

    rows = []
    for name, preds in conditions.items():
        m = f1_metrics(preds, labels_test)
        rows.append({"condition": name, **{k: round(v, 4) for k, v in m.items()},
                     "n_samples": len(test_idx)})
    summary = pd.DataFrame(rows)
    print("\n[test_seen での最終評価]")
    print(summary.to_string(index=False))

    # ── 筋群別F1・混同行列（深層学習条件C〜F。test_seen） ──
    per_muscle_rows = []
    for name in ("C_1dcnn", "D_hybrid_rule_cnn", "E_stgcn", "F_hybrid_rule_stgcn"):
        for r in per_muscle_metrics(conditions[name], labels_test, groups):
            per_muscle_rows.append({"condition": name, **r})
    per_muscle = pd.DataFrame(per_muscle_rows)
    print("\n[筋群別F1（ST-GCN関連条件・test_seen）]")
    print(per_muscle[per_muscle["condition"] == "E_stgcn"]
          .drop(columns=["condition"]).to_string(index=False))

    summary.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    tuning.to_csv(OUTPUT_TUNING, index=False, encoding="utf-8-sig")
    per_muscle.to_csv(OUTPUT_PER_MUSCLE, index=False, encoding="utf-8-sig")
    confusion = per_muscle[["condition", "muscle_id", "muscle_name", "tp", "fp", "fn", "tn"]]
    confusion.to_csv(OUTPUT_CONFUSION, index=False, encoding="utf-8-sig")
    print(f"\n保存: {OUTPUT_SUMMARY}")
    print(f"保存: {OUTPUT_TUNING}")
    print(f"保存: {OUTPUT_PER_MUSCLE}")
    print(f"保存: {OUTPUT_CONFUSION}")


if __name__ == "__main__":
    main()
