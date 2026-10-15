"""
MLモデルによる筋肉活動推定
ルールベース(muscle_activation.py)とは独立して管理する
"""
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent.parent / "data/processed/muscle_classifier.pkl"

_model_cache = None

def load_model():
    global _model_cache
    if _model_cache is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"モデルが見つかりません: {MODEL_PATH}")
        with open(MODEL_PATH, "rb") as f:
            _model_cache = pickle.load(f)
    return _model_cache

def predict_muscles(angle_features: pd.DataFrame) -> dict[str, float]:
    """
    角度特徴量DataFrameから筋肉活動スコアを推定
    戻り値: {筋群ID文字列: 確率スコア} の辞書
    """
    bundle = load_model()
    model       = bundle["model"]
    mlb         = bundle["mlb"]
    feature_cols = bundle["feature_cols"]

    # フレームをまたいだ統計量に変換（訓練時と同じ前処理）
    row = {}
    for col in feature_cols:
        # 元の角度列名を復元（_mean/_min/_max/_rangeを除く）
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

    # 各クラスの確率を取得
    proba_list = [est.predict_proba(X)[0] for est in model.estimators_]
    scores = {}
    for i, muscle_id in enumerate(mlb.classes_):
        # predict_probaは[neg確率, pos確率]の順
        prob = proba_list[i]
        scores[str(muscle_id)] = round(float(prob[1] if len(prob) > 1 else prob[0]), 4)

    return scores
