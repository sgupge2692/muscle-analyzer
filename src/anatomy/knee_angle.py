import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

df = pd.read_csv("data/processed/squat_landmarks.csv")

def calculate_angle(ax, ay, bx, by, cx, cy):
    BA = np.array([ax - bx, ay - by])
    BC = np.array([cx - bx, cy - by])
    cos_angle = np.dot(BA, BC) / (np.linalg.norm(BA) * np.linalg.norm(BC))
    return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))

VISIBILITY_THRESHOLD = 0.7  # この値未満の関節は信頼しない

left_knee_angles = []
right_knee_angles = []
frames = []

for _, row in df.iterrows():
    # 左膝：腰・膝・足首のvisibilityが全部0.7以上のときだけ計算
    left_visible = (
        row["left_hip_visibility"] > VISIBILITY_THRESHOLD and
        row["left_knee_visibility"] > VISIBILITY_THRESHOLD and
        row["left_ankle_visibility"] > VISIBILITY_THRESHOLD
    )

    right_visible = (
        row["right_hip_visibility"] > VISIBILITY_THRESHOLD and
        row["right_knee_visibility"] > VISIBILITY_THRESHOLD and
        row["right_ankle_visibility"] > VISIBILITY_THRESHOLD
    )

    if left_visible and right_visible:
        left_angle = calculate_angle(
            row["left_hip_x"],   row["left_hip_y"],
            row["left_knee_x"],  row["left_knee_y"],
            row["left_ankle_x"], row["left_ankle_y"]
        )
        right_angle = calculate_angle(
            row["right_hip_x"],   row["right_hip_y"],
            row["right_knee_x"],  row["right_knee_y"],
            row["right_ankle_x"], row["right_ankle_y"]
        )
        left_knee_angles.append(left_angle)
        right_knee_angles.append(right_angle)
        frames.append(row["frame"])

print(f"有効フレーム数: {len(frames)} / {len(df)} フレーム")

# グラフを描画
plt.figure(figsize=(12, 5))
plt.plot(frames, left_knee_angles, label="左膝", color="blue", alpha=0.7)
plt.plot(frames, right_knee_angles, label="右膝", color="red", alpha=0.7)
plt.axhline(y=90, color="green", linestyle="--", alpha=0.5, label="90°（パラレル）")
plt.xlabel("フレーム")
plt.ylabel("膝の角度（度）")
plt.title("スクワット中の膝の屈曲角度（visibility filter適用）")
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig("data/processed/knee_angle.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ data/processed/knee_angle.png に保存しました")
print(f"\n左膝：最小{min(left_knee_angles):.1f}° 最大{max(left_knee_angles):.1f}°")
print(f"右膝：最小{min(right_knee_angles):.1f}° 最大{max(right_knee_angles):.1f}°")
print(f"スクワットの最大深度：膝が{180 - min(left_knee_angles):.1f}°曲がっています")
