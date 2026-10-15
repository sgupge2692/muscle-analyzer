"""
MuscleMapのCOCO17関節pkl -> 角度特徴量 -> 学習データCSV
MediaPipe33関節のangle_features.pyとは別に管理する
"""
import pickle
import numpy as np
import pandas as pd

# COCO17関節のインデックス定義
COCO = {
    "nose": 0,
    "left_eye": 1, "right_eye": 2,
    "left_ear": 3, "right_ear": 4,
    "left_shoulder": 5, "right_shoulder": 6,
    "left_elbow": 7, "right_elbow": 8,
    "left_wrist": 9, "right_wrist": 10,
    "left_hip": 11, "right_hip": 12,
    "left_knee": 13, "right_knee": 14,
    "left_ankle": 15, "right_ankle": 16,
}

def calc_angle(p1, p2, p3):
    v1 = p1 - p2
    v2 = p3 - p2
    cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos_a, -1, 1))))

def extract_angles_from_frame(kp):
    def pt(name):
        return kp[COCO[name]]
    angles = {}
    for side in ["left", "right"]:
        try:
            angles[f"{side}_knee"] = calc_angle(pt(f"{side}_hip"), pt(f"{side}_knee"), pt(f"{side}_ankle"))
        except:
            angles[f"{side}_knee"] = np.nan
    for side in ["left", "right"]:
        try:
            angles[f"{side}_hip"] = calc_angle(pt(f"{side}_shoulder"), pt(f"{side}_hip"), pt(f"{side}_knee"))
        except:
            angles[f"{side}_hip"] = np.nan
    for side in ["left", "right"]:
        try:
            angles[f"{side}_elbow"] = calc_angle(pt(f"{side}_shoulder"), pt(f"{side}_elbow"), pt(f"{side}_wrist"))
        except:
            angles[f"{side}_elbow"] = np.nan
    for side in ["left", "right"]:
        try:
            angles[f"{side}_shoulder"] = calc_angle(pt(f"{side}_elbow"), pt(f"{side}_shoulder"), pt(f"{side}_hip"))
        except:
            angles[f"{side}_shoulder"] = np.nan
    try:
        mid_shoulder = (pt("left_shoulder") + pt("right_shoulder")) / 2
        mid_hip = (pt("left_hip") + pt("right_hip")) / 2
        spine_vec = mid_shoulder - mid_hip
        vertical = np.array([0, -1])
        cos_a = np.dot(spine_vec, vertical) / (np.linalg.norm(spine_vec) + 1e-8)
        angles["spine_tilt"] = float(np.degrees(np.arccos(np.clip(cos_a, -1, 1))))
    except:
        angles["spine_tilt"] = np.nan
    return angles

def extract_features_from_pkl(pkl_path):
    with open(pkl_path, "rb") as f:
        data = pickle.load(f)
    kp = data["keypoint"]
    scores = data["keypoint_score"]
    person_scores = scores.mean(axis=(1, 2))
    best_person = int(np.argmax(person_scores))
    kp_person = kp[best_person]
    frame_angles = [extract_angles_from_frame(frame_kp) for frame_kp in kp_person]
    df = pd.DataFrame(frame_angles)
    features = {}
    for col in df.columns:
        features[f"{col}_mean"] = df[col].mean()
        features[f"{col}_min"]  = df[col].min()
        features[f"{col}_max"]  = df[col].max()
        features[f"{col}_range"]= df[col].max() - df[col].min()
    return features

if __name__ == "__main__":
    import glob
    files = sorted(glob.glob("backend/data/raw/musclemap_benchmark/musclemap136_skl/*.pkl"))
    print(f"テスト対象: {files[0]}")
    features = extract_features_from_pkl(files[0])
    print(f"特徴量数: {len(features)}")
    for k, v in list(features.items())[:8]:
        print(f"  {k}: {v:.2f}")
