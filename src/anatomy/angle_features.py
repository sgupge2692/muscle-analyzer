import pandas as pd
import numpy as np

def calc_angle(p1, p2, p3):
    """3点から関節角度を計算（p2が頂点）"""
    v1 = p1 - p2
    v2 = p3 - p2
    cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return np.degrees(np.arccos(np.clip(cos_a, -1, 1)))

def extract_angles(row):
    """1フレーム分の座標から全関節角度を抽出"""
    def pt(name):
        return np.array([row[f'{name}_x'], row[f'{name}_y']])

    angles = {}

    for side in ['right', 'left']:
        try:
            angles[f'{side}_knee'] = calc_angle(
                pt(f'{side}_hip'), pt(f'{side}_knee'), pt(f'{side}_ankle'))
        except:
            angles[f'{side}_knee'] = np.nan

    for side in ['right', 'left']:
        try:
            angles[f'{side}_hip'] = calc_angle(
                pt(f'{side}_shoulder'), pt(f'{side}_hip'), pt(f'{side}_knee'))
        except:
            angles[f'{side}_hip'] = np.nan

    for side in ['right', 'left']:
        try:
            angles[f'{side}_elbow'] = calc_angle(
                pt(f'{side}_shoulder'), pt(f'{side}_elbow'), pt(f'{side}_wrist'))
        except:
            angles[f'{side}_elbow'] = np.nan

    for side in ['right', 'left']:
        try:
            angles[f'{side}_shoulder'] = calc_angle(
                pt(f'{side}_elbow'), pt(f'{side}_shoulder'), pt(f'{side}_hip'))
        except:
            angles[f'{side}_shoulder'] = np.nan

    for side in ['right', 'left']:
        try:
            angles[f'{side}_ankle'] = calc_angle(
                pt(f'{side}_knee'), pt(f'{side}_ankle'), pt(f'{side}_foot_index'))
        except:
            angles[f'{side}_ankle'] = np.nan

    try:
        mid_shoulder = (pt('right_shoulder') + pt('left_shoulder')) / 2
        mid_hip      = (pt('right_hip')      + pt('left_hip'))      / 2
        spine_vec    = mid_shoulder - mid_hip
        vertical     = np.array([0, -1])
        cos_a = np.dot(spine_vec, vertical) / (np.linalg.norm(spine_vec) + 1e-8)
        angles['spine_tilt'] = np.degrees(np.arccos(np.clip(cos_a, -1, 1)))
    except:
        angles['spine_tilt'] = np.nan

    return angles

def add_velocity_acceleration(df: pd.DataFrame) -> pd.DataFrame:
    """
    速度・加速度・左右非対称性を追加

    速度   = 角度の1フレーム差分（どれだけ速く動いてるか）
    加速度 = 速度の1フレーム差分（どれだけ急激に動いてるか）
    左右差 = 左右の角度差（アンバランス検出）
    """
    angle_cols = list(df.columns)
    result = df.copy()

    for col in angle_cols:
        result[f'{col}_vel'] = df[col].diff()

    for col in angle_cols:
        result[f'{col}_acc'] = result[f'{col}_vel'].diff()

    pairs = ['knee', 'hip', 'elbow', 'shoulder', 'ankle']
    for joint in pairs:
        r = f'right_{joint}'
        l = f'left_{joint}'
        if r in df.columns and l in df.columns:
            result[f'{joint}_asymmetry'] = df[r] - df[l]

    return result

def compute_angle_features(csv_path: str) -> pd.DataFrame:
    """CSVから全フレームの関節角度＋速度＋加速度＋左右差を計算"""
    df = pd.read_csv(csv_path)
    records = []
    for _, row in df.iterrows():
        angles = extract_angles(row)
        angles['frame'] = row['frame']
        records.append(angles)

    angle_df = pd.DataFrame(records).set_index('frame')
    smoothed = angle_df.rolling(window=15, center=True).mean()
    full_features = add_velocity_acceleration(smoothed)

    return full_features

if __name__ == "__main__":
    CSV_PATH = "data/processed/squat_landmarks.csv"
    OUTPUT   = "data/processed/angle_features.csv"

    print("関節角度・速度・加速度を計算中...")
    features = compute_angle_features(CSV_PATH)

    print(f"\nshape: {features.shape}")
    print(f"\n特徴量一覧:")
    for col in features.columns:
        print(f"  {col}")

    features.to_csv(OUTPUT)
    print(f"\n保存: {OUTPUT}")
