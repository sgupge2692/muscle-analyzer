"""
angle_features.py
MediaPipeランドマークCSV → 関節角度・角速度・非対称性 特徴量DataFrame

compute_angle_features() の出力列:
  right_knee / left_knee / right_hip / left_hip
  right_elbow / left_elbow / right_shoulder / left_shoulder
  right_ankle / left_ankle
  spine_tilt
  knee_asymmetry / hip_asymmetry
  *_vel（各角度の角速度: フレーム間差分）
"""

import pandas as pd
import numpy as np

# 可視性スコアの閾値（これ未満のフレームはNaNとして扱う）
VIS_THRESHOLD = 0.5


def _calc_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """3点から関節角度を計算（p2が頂点）"""
    v1 = p1 - p2
    v2 = p3 - p2
    denom = np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8
    return float(np.degrees(np.arccos(np.clip(np.dot(v1, v2) / denom, -1, 1))))


def _pt(row: pd.Series, name: str) -> np.ndarray:
    return np.array([row[f"{name}_x"], row[f"{name}_y"]])


def _vis(row: pd.Series, *names: str) -> bool:
    """全関節の可視性スコアが閾値以上か確認"""
    return all(
        row.get(f"{n}_visibility", 1.0) >= VIS_THRESHOLD
        for n in names
    )


def extract_angles(row: pd.Series) -> dict:
    """1フレーム分の座標から全関節角度を抽出（可視性チェック付き）"""
    angles: dict[str, float] = {}

    for side in ("right", "left"):
        # 膝角度 (股→膝→足首)
        if _vis(row, f"{side}_hip", f"{side}_knee", f"{side}_ankle"):
            angles[f"{side}_knee"] = _calc_angle(
                _pt(row, f"{side}_hip"),
                _pt(row, f"{side}_knee"),
                _pt(row, f"{side}_ankle"),
            )
        else:
            angles[f"{side}_knee"] = np.nan

        # 股関節角度 (肩→股→膝)
        if _vis(row, f"{side}_shoulder", f"{side}_hip", f"{side}_knee"):
            angles[f"{side}_hip"] = _calc_angle(
                _pt(row, f"{side}_shoulder"),
                _pt(row, f"{side}_hip"),
                _pt(row, f"{side}_knee"),
            )
        else:
            angles[f"{side}_hip"] = np.nan

        # 肘角度 (肩→肘→手首)
        if _vis(row, f"{side}_shoulder", f"{side}_elbow", f"{side}_wrist"):
            angles[f"{side}_elbow"] = _calc_angle(
                _pt(row, f"{side}_shoulder"),
                _pt(row, f"{side}_elbow"),
                _pt(row, f"{side}_wrist"),
            )
        else:
            angles[f"{side}_elbow"] = np.nan

        # 肩角度 (肘→肩→股)
        if _vis(row, f"{side}_elbow", f"{side}_shoulder", f"{side}_hip"):
            angles[f"{side}_shoulder"] = _calc_angle(
                _pt(row, f"{side}_elbow"),
                _pt(row, f"{side}_shoulder"),
                _pt(row, f"{side}_hip"),
            )
        else:
            angles[f"{side}_shoulder"] = np.nan

        # 足首角度 (膝→足首→つま先)
        if _vis(row, f"{side}_knee", f"{side}_ankle", f"{side}_foot_index"):
            angles[f"{side}_ankle"] = _calc_angle(
                _pt(row, f"{side}_knee"),
                _pt(row, f"{side}_ankle"),
                _pt(row, f"{side}_foot_index"),
            )
        else:
            angles[f"{side}_ankle"] = np.nan

    # 脊柱傾斜角（垂直からの角度）
    if _vis(row, "left_shoulder", "right_shoulder", "left_hip", "right_hip"):
        mid_sh  = (_pt(row, "left_shoulder") + _pt(row, "right_shoulder")) / 2
        mid_hip = (_pt(row, "left_hip")      + _pt(row, "right_hip"))      / 2
        spine   = mid_sh - mid_hip
        vertical = np.array([0.0, -1.0])
        cos_a    = np.dot(spine, vertical) / (np.linalg.norm(spine) + 1e-8)
        angles["spine_tilt"] = float(np.degrees(np.arccos(np.clip(cos_a, -1, 1))))
    else:
        angles["spine_tilt"] = np.nan

    return angles


def compute_angle_features(landmarks_csv: str, smooth_window: int = 5) -> pd.DataFrame:
    """
    ランドマークCSVから角度特徴量DataFrameを生成する

    Args:
        landmarks_csv: extract_landmarks()が出力したCSVファイルパス
        smooth_window: 移動平均ウィンドウ（ノイズ除去）
    Returns:
        フレームをインデックスとする角度特徴量DataFrame
    """
    df = pd.read_csv(landmarks_csv, index_col="frame")

    # 全フレームの角度を一括計算
    angle_rows = [extract_angles(row) for _, row in df.iterrows()]
    feat = pd.DataFrame(angle_rows, index=df.index)

    # 移動平均による平滑化（外れ値除去）
    base_cols = feat.columns.tolist()
    feat = feat.rolling(smooth_window, center=True, min_periods=1).mean()

    # 左右非対称性特徴量
    if "right_knee" in feat and "left_knee" in feat:
        feat["knee_asymmetry"] = (feat["right_knee"] - feat["left_knee"]).abs()
    if "right_hip" in feat and "left_hip" in feat:
        feat["hip_asymmetry"]  = (feat["right_hip"]  - feat["left_hip"]).abs()

    # 角速度（フレーム間差分）
    for col in base_cols:
        feat[f"{col}_vel"] = feat[col].diff().abs().fillna(0)

    return feat
