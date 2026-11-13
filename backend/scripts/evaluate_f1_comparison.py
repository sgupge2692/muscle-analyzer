"""
筋肉活動分類の3条件比較評価スクリプト（成功基準1: F1 micro ≥ 0.93 の判定用）

研究計画書の評価実験を制度化するもの:
    条件A: ルールベースのみ（種目×筋群マッピングのみ。角度変調なし）
    条件B: ルールベース＋角度変調（estimate_activation の出力をサンプル内正規化して二値化）
    条件C: 1D-CNNのみ（best_1dcnn.pt，閾値0.5）
    条件D: ハイブリッド（ルールベース正規化値とCNN確率の0.5/0.5融合，閾値0.5）
    参照: RandomForest（muscle_classifier.pkl，既存ベースライン）

手順の原則:
    - 角度変調・融合の閾値は val_seen で選択し，test_seen でのみ最終評価する
      （テストセットでの閾値選択による過大評価を防ぐ）
    - split は train.py の split_indices と同じ規約（ファイル名キーワード）
    - 結果は output/f1_comparison_*.csv に保存する（train.py と異なり標準出力だけにしない）

ルールベース入力の注意:
    MuscleMap の骨格は COCO17 の2D関節（.skl）であり，バックエンド本番パイプライン
    （MediaPipe 33ランドマーク・3D）と計測条件が異なる。足首角度（foot_index 依存）は
    COCO17 では計算不能なため NaN。この差異は論文中で明記すること。

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/evaluate_f1_comparison.py

依存は requirements.txt の範囲内（torch / scikit-learn / numpy / pandas）のみ。
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
sys.path.insert(0, str(BACKEND_DIR / "src" / "ml"))

from dataset import MuscleMapDataset, normalize_frames  # noqa: E402
from anatomy.angle_features import extract_angles  # noqa: E402
from anatomy.muscle_activation import estimate_activation  # noqa: E402
from anatomy.ml_predictor import COCO17_MEDIAPIPE  # noqa: E402

LABELED_PKL = BACKEND_DIR / "data/processed/musclemap_labeled.pkl"
SKL_DIR = BACKEND_DIR / "data/raw/musclemap_benchmark/musclemap136_skl"
MAPPING_PATH = BACKEND_DIR / "data/muscle_mapping.json"
CNN_WEIGHTS = BACKEND_DIR / "output/best_1dcnn.pt"
RF_PKL = BACKEND_DIR / "data/processed/muscle_classifier.pkl"

OUTPUT_SUMMARY = BACKEND_DIR / "output/f1_comparison_test.csv"
OUTPUT_TUNING = BACKEND_DIR / "output/f1_comparison_val_thresholds.csv"
CACHE_RULE_VAL = BACKEND_DIR / "output/_cache_rule_val.npz"
CACHE_RULE_TEST = BACKEND_DIR / "output/_cache_rule_test.npz"

NUM_CLASSES = 20
CNN_THRESHOLD = 0.5          # 学習時と同じ固定閾値
FUSION_WEIGHTS = [0.1, 0.2, 0.3, 0.5]  # ハイブリッドのルールベース側の重み（val_seen で選択）
RULE_THRESHOLDS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]  # val_seen で選択する候補
FUSION_THRESHOLDS = [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]

DEVICE = "cpu"  # 評価は再現性優先でCPU固定（バッチは小さくないため許容範囲）


# ── 共通ユーティリティ ───────────────────────────────────────

def split_indices(samples: list[dict]) -> tuple[list[int], list[int], list[int]]:
    """train.py の split_indices と同じ規約"""
    train_idx, val_idx, test_idx = [], [], []
    for i, s in enumerate(samples):
        f = s["file"]
        if "train" in f:
            train_idx.append(i)
        elif "val_seen" in f:
            val_idx.append(i)
        elif "test_seen" in f:
            test_idx.append(i)
    return train_idx, val_idx, test_idx


def f1_metrics(preds: np.ndarray, labels: np.ndarray) -> dict:
    """マルチラベルの micro / macro F1 と precision / recall"""
    tp = float((preds * labels).sum())
    fp = float((preds * (1 - labels)).sum())
    fn = float(((1 - preds) * labels).sum())
    micro_p = tp / (tp + fp + 1e-8)
    micro_r = tp / (tp + fn + 1e-8)
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r + 1e-8)
    # macro: ラベルごとのF1平均（そのラベルの正例が無い場合は除外）
    f1s = []
    for c in range(labels.shape[1]):
        c_tp = float((preds[:, c] * labels[:, c]).sum())
        c_fp = float((preds[:, c] * (1 - labels[:, c])).sum())
        c_fn = float(((1 - preds[:, c]) * labels[:, c]).sum())
        if c_tp + c_fn == 0:
            continue  # 正例が存在しないラベルは除外
        p = c_tp / (c_tp + c_fp + 1e-8)
        r = c_tp / (c_tp + c_fn + 1e-8)
        f1s.append(2 * p * r / (p + r + 1e-8))
    return {
        "f1_micro": micro_f1,
        "f1_macro": float(np.mean(f1s)) if f1s else float("nan"),
        "precision_micro": micro_p,
        "recall_micro": micro_r,
    }


def load_mapping() -> tuple[dict, dict]:
    import json
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return mapping["exercise_muscle_mapping"], mapping["muscle_groups"]


def active_muscles_for(emm: dict, groups: dict, exercise: str) -> list[str]:
    ids = emm.get(exercise, [])
    return [groups[str(i)] for i in ids if str(i) in groups]


# ── ルールベース側の特徴量・活動度計算 ───────────────────────

def angle_features_from_skl(skl_path: Path) -> pd.DataFrame | None:
    """COCO17の2D骨格(.skl)からバックエンドと同じ手順の角度特徴量DataFrameを作る

    compute_angle_features と同等の処理（平滑化・非対称性・角速度）を
    .skl 入力に対して再現する。foot_index が無いため足首角度は常にNaN。
    """
    with open(skl_path, "rb") as f:
        skl = pickle.load(f)
    keypoints = skl["keypoint"][0]        # (T, V, 2)
    scores = skl["keypoint_score"][0]     # (T, V)

    # 30フレームにリサンプル（CNN入力と同じ正規化）
    x = normalize_frames(keypoints, scores)          # (3, 30, 17) x,y,score
    xy = x[:2].transpose(2, 1, 0)                    # (30, 17, 2)
    vis = x[2].transpose(1, 0)                       # (30, 17)

    rows = []
    for t in range(xy.shape[0]):
        row = {}
        for v, name in enumerate(COCO17_MEDIAPIPE):
            row[f"{name}_x"] = float(xy[t, v, 0])
            row[f"{name}_y"] = float(xy[t, v, 1])
            row[f"{name}_visibility"] = float(vis[t, v])
        # COCO17 に foot_index は無い。visibility のデフォルト値（1.0）が
        # 可視性チェックを通してしまい _pt で KeyError になるため、
        # 予め NaN 座標を入れて足首角度を NaN にフォールバックさせる
        for side in ("left", "right"):
            row[f"{side}_foot_index_x"] = np.nan
            row[f"{side}_foot_index_y"] = np.nan
        rows.append(extract_angles(pd.Series(row)))
    feat = pd.DataFrame(rows)

    # compute_angle_features と同じ後処理
    base_cols = feat.columns.tolist()
    feat = feat.rolling(5, center=True, min_periods=1).mean()
    if "right_knee" in feat and "left_knee" in feat:
        feat["knee_asymmetry"] = (feat["right_knee"] - feat["left_knee"]).abs()
    if "right_hip" in feat and "left_hip" in feat:
        feat["hip_asymmetry"] = (feat["right_hip"] - feat["left_hip"]).abs()
    for col in base_cols:
        feat[f"{col}_vel"] = feat[col].diff().abs().fillna(0)
    return feat


def rule_scores(samples: list[dict], indices: list[int],
                emm: dict, groups: dict) -> tuple[np.ndarray, np.ndarray]:
    """各サンプルのルールベース活動度（サンプル内正規化済み20筋ベクトル）を計算

    戻り値: (norm_scores (N,20), labels (N,20))
    正規化: estimate_activation の平均活動度をサンプル内最大値で割る（最大=1）。
    角度が全NaN等で活動度が計算不能な場合はフォールバックとして
    マッピング筋を1.0、非マッピング筋を0.0とする（条件Aと一致）。
    """
    n = len(indices)
    scores = np.zeros((n, NUM_CLASSES), dtype=np.float32)
    labels = np.zeros((n, NUM_CLASSES), dtype=np.float32)

    for row_i, idx in enumerate(indices):
        s = samples[idx]
        exercise = s["exercise"]
        muscles = active_muscles_for(emm, groups, exercise)
        name_to_id = {name: int(i) for i, name in groups.items()}

        for m in s["muscle_labels"]:
            labels[row_i, m] = 1.0

        try:
            feat = angle_features_from_skl(SKL_DIR / s["file"].replace(".mp4", ".pkl"))
            act = estimate_activation(feat, muscles, exercise=exercise)
            mean = act.mean(axis=0)
            if float(mean.max()) > 1e-6:
                norm = mean / mean.max()
            else:
                norm = None
        except Exception:
            norm = None

        if norm is not None:
            for name, val in norm.items():
                if name in name_to_id:
                    scores[row_i, name_to_id[name]] = float(val)
        else:
            for m in muscles:
                scores[row_i, name_to_id[m]] = 1.0

    # NaN は「推定不能=予測しない」扱いに統一（比較・二値化での伝播を防ぐ）
    scores = np.nan_to_num(scores, nan=0.0)
    return scores, labels


# ── 条件別の二値化 ───────────────────────────────────────────

def binarize(scores: np.ndarray, threshold: float) -> np.ndarray:
    return (scores >= threshold).astype(np.float32)


def main() -> None:
    emm, groups = load_mapping()

    with open(LABELED_PKL, "rb") as f:
        samples = pickle.load(f)
    _, val_idx, test_idx = split_indices(samples)
    print(f"val_seen: {len(val_idx)}, test_seen: {len(test_idx)}")

    # ── ルールベース側の活動度スコア（val/test で共通の手順）──
    # 反復実行に備えてキャッシュ（中間スコアは output/_cache_rule_*.npz）
    if CACHE_RULE_VAL.exists() and CACHE_RULE_TEST.exists():
        c_val = np.load(CACHE_RULE_VAL)
        c_test = np.load(CACHE_RULE_TEST)
        rule_val, labels_val = c_val["scores"], c_val["labels"]
        rule_test, labels_test = c_test["scores"], c_test["labels"]
        print("ルールベース活動度をキャッシュから読み込み")
    else:
        print("ルールベース活動度を計算中（val_seen）...")
        rule_val, labels_val = rule_scores(samples, val_idx, emm, groups)
        print("ルールベース活動度を計算中（test_seen）...")
        rule_test, labels_test = rule_scores(samples, test_idx, emm, groups)
        np.savez(CACHE_RULE_VAL, scores=rule_val, labels=labels_val)
        np.savez(CACHE_RULE_TEST, scores=rule_test, labels=labels_test)

    # ── 条件A: マッピングのみ（角度変調なし）──
    mapping_val = rule_val.copy()
    mapping_val[rule_val > 0] = 1.0  # マッピング筋=1.0（フォールバック含む）

    # ── 条件C: 1D-CNN ──
    print("1D-CNN推論中...")
    import torch
    from model import MuscleClassifier1DCNN  # noqa: E402

    model = MuscleClassifier1DCNN()
    model.load_state_dict(torch.load(CNN_WEIGHTS, map_location=DEVICE, weights_only=True))
    model.eval()

    eval_dataset = MuscleMapDataset(LABELED_PKL, SKL_DIR, augment=False)
    cnn_val = _cnn_probs(model, eval_dataset, val_idx)
    cnn_test = _cnn_probs(model, eval_dataset, test_idx)

    # ── 閾値・融合重みの選択（val_seen のみで実施）──
    tuning_rows = []
    for t in RULE_THRESHOLDS:
        m_b = f1_metrics(binarize(rule_val, t), labels_val)
        for w in FUSION_WEIGHTS:
            h = w * rule_val + (1 - w) * cnn_val
            for ft in FUSION_THRESHOLDS:
                m_h = f1_metrics(binarize(h, ft), labels_val)
                tuning_rows.append({
                    "rule_threshold": t,
                    "fusion_weight_rule": w,
                    "fusion_threshold": ft,
                    "val_f1_micro_rule": round(m_b["f1_micro"], 4),
                    "val_f1_micro_hybrid": round(m_h["f1_micro"], 4),
                })
    tuning = pd.DataFrame(tuning_rows)
    best_idx = tuning["val_f1_micro_hybrid"].idxmax()
    best_rule_t = float(tuning.loc[tuning["val_f1_micro_rule"].idxmax(), "rule_threshold"])
    best_fusion_w = float(tuning.loc[best_idx, "fusion_weight_rule"])
    best_fusion_t = float(tuning.loc[best_idx, "fusion_threshold"])
    print("\n[val_seen での閾値選択]")
    print(tuning.to_string(index=False))
    print(f"\n選択された角度変調閾値: {best_rule_t} / 融合重み(ルール側): {best_fusion_w} / 融合閾値: {best_fusion_t}")

    # ── test_seen での最終評価 ──
    hybrid_test = best_fusion_w * rule_test + (1 - best_fusion_w) * cnn_test
    mapping_test = rule_test.copy()
    mapping_test[rule_test > 0] = 1.0

    conditions = {
        "A_rule_mapping_only": mapping_test,
        "B_rule_angle_mod": binarize(rule_test, best_rule_t),
        "C_1dcnn": binarize(cnn_test, CNN_THRESHOLD),
        "D_hybrid": binarize(hybrid_test, best_fusion_t),
    }

    # 参照: RandomForest（feature_cols は学習時のものをそのまま使用）
    try:
        rf_preds = _rf_probs(samples, test_idx, groups)
        conditions["RF_baseline"] = binarize(rf_preds, CNN_THRESHOLD)
        rf_available = True
    except Exception as e:
        print(f"RF baseline をスキップ: {e}")
        rf_available = False

    rows = []
    for name, preds in conditions.items():
        m = f1_metrics(preds, labels_test)
        rows.append({"condition": name, **{k: round(v, 4) for k, v in m.items()},
                     "n_samples": len(test_idx)})
    summary = pd.DataFrame(rows)
    print("\n[test_seen での最終評価]")
    print(summary.to_string(index=False))

    OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
    tuning.to_csv(OUTPUT_TUNING, index=False, encoding="utf-8-sig")
    print(f"\n保存: {OUTPUT_SUMMARY}")
    print(f"保存: {OUTPUT_TUNING}")


def _cnn_probs(model, dataset, indices: list[int]) -> np.ndarray:
    """指定インデックスのCNN確率 (N,20) を計算"""
    import torch
    probs = []
    with torch.no_grad():
        for idx in indices:
            x, _ = dataset[idx]
            logits = model(x.unsqueeze(0))
            probs.append(torch.sigmoid(logits)[0].numpy())
    return np.array(probs, dtype=np.float32)


def _rf_probs(samples: list[dict], indices: list[int], groups: dict) -> np.ndarray:
    """RandomForest の確率 (N,20) を計算（ml_predictor.predict_muscles のバッチ版）

    注意: muscle_classifier.pkl は本番パイプラインの自前データで学習されており
    mlb.classes_ は筋ID 1〜19（0=不明 を含まない19クラス）。MuscleMap の
    20筋ラベル空間には筋名経由で写像する（26行目付近の groups が 名前←→ID の対応）。
    """
    with open(RF_PKL, "rb") as f:
        bundle = pickle.load(f)
    model, mlb, feature_cols = bundle["model"], bundle["mlb"], bundle["feature_cols"]
    name_to_id = {name: int(i) for i, name in groups.items()}

    n = len(indices)
    X = np.zeros((n, len(feature_cols)), dtype=np.float32)
    for row_i, idx in enumerate(indices):
        s = samples[idx]
        feat = angle_features_from_skl(SKL_DIR / s["file"].replace(".mp4", ".pkl"))
        for c_i, col in enumerate(feature_cols):
            base, stat = col.rsplit("_", 1)
            series = feat[base].dropna() if base in feat.columns else pd.Series(dtype=float)
            if len(series) == 0:
                X[row_i, c_i] = 0.0
            elif stat == "mean":
                X[row_i, c_i] = series.mean()
            elif stat == "min":
                X[row_i, c_i] = series.min()
            elif stat == "max":
                X[row_i, c_i] = series.max()
            elif stat == "range":
                X[row_i, c_i] = series.max() - series.min()

    out = np.zeros((n, NUM_CLASSES), dtype=np.float32)
    for i, est in enumerate(model.estimators_):
        p = est.predict_proba(X)
        prob = p[:, 1] if p.shape[1] > 1 else p[:, 0]
        class_id = int(mlb.classes_[i])           # 筋ID（0〜19 または 1〜19）
        name = groups.get(str(class_id))
        if name is None:
            continue
        out[:, name_to_id[name]] = prob
    return np.nan_to_num(out, nan=0.0)


if __name__ == "__main__":
    main()
