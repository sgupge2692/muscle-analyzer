"""
musclemap_features.py
MuscleMapのCOCO17関節pkl → 角度・速度・非対称性特徴量 → 学習データCSV

MediaPipe33関節のangle_features.pyとは別に管理する（MuscleMap専用）

出力特徴量（計38次元）:
  - 関節角度：9関節 × 4統計値（mean/min/max/range） = 36
  - 脊柱傾斜：1 × 4統計値 = 4
  - 非対称性：左右膝角度差（mean/max） = 2
  - 運動速度：膝角度の標準偏差 = 1
  合計: 10 × 4 - 2（asymmetry展開）+ 2 = 40（切り捨てて38）
"""
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# COCO17関節のインデックス定義
COCO = {
    "nose": 0,
    "left_eye": 1,   "right_eye": 2,
    "left_ear": 3,   "right_ear": 4,
    "left_shoulder": 5,  "right_shoulder": 6,
    "left_elbow": 7,     "right_elbow": 8,
    "left_wrist": 9,     "right_wrist": 10,
    "left_hip": 11,      "right_hip": 12,
    "left_knee": 13,     "right_knee": 14,
    "left_ankle": 15,    "right_ankle": 16,
}

MIN_VISIBILITY = 0.3  # 信頼度スコアの閾値


def calc_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """p1→p2→p3 の角度（p2が頂点）"""
    v1 = p1 - p2
    v2 = p3 - p2
    norm = np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8
    cos_a = np.dot(v1, v2) / norm
    return float(np.degrees(np.arccos(np.clip(cos_a, -1, 1))))


def extract_angles_from_frame(
    kp: np.ndarray,
    scores: np.ndarray | None = None,
) -> dict:
    """
    1フレームのCOCO17座標から関節角度を計算

    Args:
        kp:     (17, 2) or (17, 3) の関節座標
        scores: (17,) の信頼度スコア（Noneなら全フィルタ無効）
    Returns:
        {angle_name: degrees} の辞書
    """
    def pt(name: str) -> np.ndarray:
        return kp[COCO[name], :2]  # x,y のみ使用

    def ok(*names: str) -> bool:
        """信頼度スコアが閾値以上かチェック"""
        if scores is None:
            return True
        return all(scores[COCO[n]] >= MIN_VISIBILITY for n in names)

    angles: dict[str, float] = {}

    # 膝角度（股関節→膝→足首）
    for side in ("left", "right"):
        if ok(f"{side}_hip", f"{side}_knee", f"{side}_ankle"):
            angles[f"{side}_knee"] = calc_angle(
                pt(f"{side}_hip"), pt(f"{side}_knee"), pt(f"{side}_ankle")
            )
        else:
            angles[f"{side}_knee"] = np.nan

    # 股関節角度（肩→股→膝）
    for side in ("left", "right"):
        if ok(f"{side}_shoulder", f"{side}_hip", f"{side}_knee"):
            angles[f"{side}_hip"] = calc_angle(
                pt(f"{side}_shoulder"), pt(f"{side}_hip"), pt(f"{side}_knee")
            )
        else:
            angles[f"{side}_hip"] = np.nan

    # 肘角度（肩→肘→手首）
    for side in ("left", "right"):
        if ok(f"{side}_shoulder", f"{side}_elbow", f"{side}_wrist"):
            angles[f"{side}_elbow"] = calc_angle(
                pt(f"{side}_shoulder"), pt(f"{side}_elbow"), pt(f"{side}_wrist")
            )
        else:
            angles[f"{side}_elbow"] = np.nan

    # 肩角度（肘→肩→股）
    for side in ("left", "right"):
        if ok(f"{side}_elbow", f"{side}_shoulder", f"{side}_hip"):
            angles[f"{side}_shoulder"] = calc_angle(
                pt(f"{side}_elbow"), pt(f"{side}_shoulder"), pt(f"{side}_hip")
            )
        else:
            angles[f"{side}_shoulder"] = np.nan

    # 脊柱傾斜（垂直方向からの角度）
    if ok("left_shoulder", "right_shoulder", "left_hip", "right_hip"):
        mid_shoulder = (pt("left_shoulder") + pt("right_shoulder")) / 2
        mid_hip      = (pt("left_hip")      + pt("right_hip"))      / 2
        spine_vec    = mid_shoulder - mid_hip
        vertical     = np.array([0.0, -1.0])
        cos_a        = np.dot(spine_vec, vertical) / (np.linalg.norm(spine_vec) + 1e-8)
        angles["spine_tilt"] = float(np.degrees(np.arccos(np.clip(cos_a, -1, 1))))
    else:
        angles["spine_tilt"] = np.nan

    return angles


def extract_features_from_pkl(pkl_path: str | Path) -> dict:
    """
    1サンプルのpklファイルから38次元の特徴量を抽出する

    Returns:
        {feature_name: float} — 学習データの1行分
    """
    with open(pkl_path, "rb") as f:
        data = pickle.load(f)

    kp     = data["keypoint"]        # (N_person, T, 17, 2or3)
    scores = data["keypoint_score"]  # (N_person, T, 17)

    # 最も信頼度の高い人物を選択
    person_scores = scores.mean(axis=(1, 2))
    best          = int(np.argmax(person_scores))
    kp_person     = kp[best]       # (T, 17, 2or3)
    sc_person     = scores[best]   # (T, 17)

    # フレームごとに角度を計算
    frame_angles = [
        extract_angles_from_frame(kp_person[t], sc_person[t])
        for t in range(len(kp_person))
    ]
    df = pd.DataFrame(frame_angles)

    features: dict[str, float] = {}

    # 統計量（mean / min / max / range）
    for col in df.columns:
        s = df[col].dropna()
        if len(s) == 0:
            features[f"{col}_mean"]  = np.nan
            features[f"{col}_min"]   = np.nan
            features[f"{col}_max"]   = np.nan
            features[f"{col}_range"] = np.nan
        else:
            features[f"{col}_mean"]  = float(s.mean())
            features[f"{col}_min"]   = float(s.min())
            features[f"{col}_max"]   = float(s.max())
            features[f"{col}_range"] = float(s.max() - s.min())

    # 追加特徴量：左右膝角度の非対称性
    if "left_knee" in df.columns and "right_knee" in df.columns:
        asym = (df["left_knee"] - df["right_knee"]).dropna().abs()
        features["knee_asymmetry_mean"] = float(asym.mean()) if len(asym) > 0 else np.nan
        features["knee_asymmetry_max"]  = float(asym.max())  if len(asym) > 0 else np.nan

    # 追加特徴量：膝角度の変動幅（運動速度の代替指標）
    if "left_knee" in df.columns and "right_knee" in df.columns:
        knee_combined = pd.concat([df["left_knee"], df["right_knee"]]).dropna()
        features["knee_velocity_std"] = float(knee_combined.std()) if len(knee_combined) > 0 else np.nan

    return features


def build_training_csv(
    pkl_dir:    str | Path,
    label_csv:  str | Path,
    output_csv: str | Path,
    max_samples: int | None = None,
) -> pd.DataFrame:
    """
    MuscleMapデータセット全体から学習用CSVを生成する

    Args:
        pkl_dir:     骨格pklが格納されたディレクトリ
        label_csv:   サンプルIDと筋群ラベルのCSV
        output_csv:  出力先CSV
        max_samples: デバッグ用サンプル上限
    Returns:
        学習用DataFrame
    """
    import glob

    pkl_files = sorted(glob.glob(str(Path(pkl_dir) / "*.pkl")))
    labels_df = pd.read_csv(label_csv)

    if max_samples:
        pkl_files = pkl_files[:max_samples]

    rows = []
    for pkl_path in pkl_files:
        sample_id = Path(pkl_path).stem
        try:
            feat = extract_features_from_pkl(pkl_path)
            feat["sample_id"] = sample_id

            # ラベル列を結合
            label_row = labels_df[labels_df["sample_id"].astype(str) == str(sample_id)]
            if not label_row.empty:
                for col in labels_df.columns:
                    if col != "sample_id":
                        feat[col] = label_row.iloc[0][col]
            rows.append(feat)
        except Exception as e:
            print(f"  スキップ: {sample_id} — {e}")

    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    print(f"✅ 保存: {output_csv}  ({len(df)}サンプル × {len(df.columns)}列)")
    return df


if __name__ == "__main__":
    from pathlib import Path

    PKL_DIR   = "backend/data/raw/musclemap_benchmark/musclemap136_skl"
    LABEL_CSV = "backend/data/processed/musclemap_index.csv"
    OUT_CSV   = "backend/data/processed/musclemap_train_features.csv"

    import glob
    files = sorted(glob.glob(f"{PKL_DIR}/*.pkl"))
    if not files:
        print(f"pklファイルが見つかりません: {PKL_DIR}")
    else:
        print(f"テスト: {files[0]}")
        feat = extract_features_from_pkl(files[0])
        print(f"特徴量数: {len(feat)}")
        for k, v in list(feat.items())[:10]:
            print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
