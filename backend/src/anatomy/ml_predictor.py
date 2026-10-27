"""
MLモデルによる筋肉活動推定
ルールベース(muscle_activation.py)とは独立して管理する

対応モデル:
  - scikit-learn (RandomForest + MultiLabelBinarizer): muscle_classifier.pkl
  - PyTorch 1D-CNN: best_1dcnn.pt + muscle_id_map.json
"""
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

MODEL_PKL_PATH  = Path(__file__).parent.parent.parent / "data/processed/muscle_classifier.pkl"
MODEL_PT_PATH   = Path(__file__).parent.parent.parent / "output/best_1dcnn.pt"
MUSCLE_MAP_PATH = Path(__file__).parent.parent.parent / "data/processed/muscle_id_map.json"

_sklearn_cache = None
_torch_cache   = None


# ── scikit-learn モデル ─────────────────────────────────────
def load_model():
    """scikit-learn モデルをロード（キャッシュ）"""
    global _sklearn_cache
    if _sklearn_cache is None:
        if not MODEL_PKL_PATH.exists():
            raise FileNotFoundError(f"モデルが見つかりません: {MODEL_PKL_PATH}")
        with open(MODEL_PKL_PATH, "rb") as f:
            _sklearn_cache = pickle.load(f)
    return _sklearn_cache


def predict_muscles(angle_features: pd.DataFrame) -> dict[str, float]:
    """
    角度特徴量DataFrameから筋肉活動スコアを推定（scikit-learn版）
    戻り値: {筋群ID文字列: 確率スコア} の辞書
    """
    bundle = load_model()
    model        = bundle["model"]
    mlb          = bundle["mlb"]
    feature_cols = bundle["feature_cols"]

    row = {}
    for col in feature_cols:
        base = col.rsplit("_", 1)[0]
        stat = col.rsplit("_", 1)[1]
        if base not in angle_features.columns:
            row[col] = 0.0
            continue
        series = angle_features[base].dropna()
        if len(series) == 0:
            row[col] = 0.0
        elif stat == "mean":
            row[col] = float(series.mean())
        elif stat == "min":
            row[col] = float(series.min())
        elif stat == "max":
            row[col] = float(series.max())
        elif stat == "range":
            row[col] = float(series.max() - series.min())
        else:
            row[col] = 0.0

    X = np.array([[row[c] for c in feature_cols]])
    proba_list = [est.predict_proba(X)[0] for est in model.estimators_]
    scores = {}
    for i, muscle_id in enumerate(mlb.classes_):
        prob = proba_list[i]
        scores[str(muscle_id)] = round(float(prob[1] if len(prob) > 1 else prob[0]), 4)

    return scores


# ── PyTorch 1D-CNN モデル ───────────────────────────────────
def load_torch_model():
    """PyTorch 1D-CNNモデルをロード（キャッシュ）"""
    global _torch_cache
    if _torch_cache is not None:
        return _torch_cache

    if not MODEL_PT_PATH.exists():
        raise FileNotFoundError(f"PyTorchモデルが見つかりません: {MODEL_PT_PATH}")

    import torch
    import sys
    sys.path.append(str(Path(__file__).parent.parent / "ml"))
    from model import MuscleClassifier1DCNN

    model = MuscleClassifier1DCNN()
    state = torch.load(MODEL_PT_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    _torch_cache = model
    return model


def predict_muscles_torch(
    landmarks_sequence: list[dict],
    muscle_id_to_name: dict[int, str],
) -> dict[str, float]:
    """
    3Dランドマーク時系列から筋肉活動スコアを推定（PyTorch 1D-CNN版）

    Args:
        landmarks_sequence: landmarks_csv_to_3d_sequence() の出力
            [{"frame": 0, "landmarks": {"left_shoulder": {"x":..,"y":..,"z":..}, ...}}, ...]
        muscle_id_to_name: {20筋肉ID: 筋肉名} のマッピング

    Returns:
        {筋肉名: 確率スコア(0〜1)} の辞書
    """
    import torch

    # COCO17関節のMediaPipe名対応（MuscleMapはCOCO17形式）
    COCO17_MEDIAPIPE = [
        "nose",
        "left_eye", "right_eye",
        "left_ear", "right_ear",
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_wrist", "right_wrist",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
    ]
    NUM_FRAMES  = 30
    NUM_JOINTS  = 17
    NUM_CHANNELS = 3  # x, y, z

    T = len(landmarks_sequence)
    if T == 0:
        return {}

    # (T, 17, 3) のndarrayを作成
    raw = np.zeros((T, NUM_JOINTS, NUM_CHANNELS), dtype=np.float32)
    for t, frame in enumerate(landmarks_sequence):
        lm = frame["landmarks"]
        for v, joint_name in enumerate(COCO17_MEDIAPIPE):
            if joint_name in lm:
                raw[t, v, 0] = lm[joint_name]["x"]
                raw[t, v, 1] = lm[joint_name]["y"]
                raw[t, v, 2] = lm[joint_name]["z"]

    # フレーム数を30に正規化（線形補間）→ (3, 30, 17)
    result = np.zeros((NUM_CHANNELS, NUM_FRAMES, NUM_JOINTS), dtype=np.float32)
    old_idx = np.linspace(0, 1, T)
    new_idx = np.linspace(0, 1, NUM_FRAMES)
    for v in range(NUM_JOINTS):
        for c in range(NUM_CHANNELS):
            result[c, :, v] = np.interp(new_idx, old_idx, raw[:, v, c])

    # バッチ次元を追加 → (1, 3, 30, 17)
    x = torch.tensor(result).unsqueeze(0)

    model = load_torch_model()
    with torch.no_grad():
        logits = model(x)                    # (1, 20)
        probs  = torch.sigmoid(logits)[0]    # (20,)

    scores = {}
    for muscle_id, prob in enumerate(probs.tolist()):
        name = muscle_id_to_name.get(muscle_id, str(muscle_id))
        scores[name] = round(prob, 4)

    return scores


def is_torch_model_available() -> bool:
    return MODEL_PT_PATH.exists()
