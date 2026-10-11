import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

df = pd.read_csv("data/processed/squat_landmarks.csv")

def calculate_angle(ax, ay, bx, by, cx, cy):
    """A→B→C の角度（Bが頂点）"""
    BA = np.array([ax - bx, ay - by])
    BC = np.array([cx - bx, cy - by])
    cos_angle = np.dot(BA, BC) / (np.linalg.norm(BA) * np.linalg.norm(BC))
    return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))

VISIBILITY_THRESHOLD = 0.7

# 結果を格納するリスト
data = {
    "frame": [],
    "left_knee_angle": [],    # 左膝角度
    "left_hip_angle": [],     # 左股関節角度
    "spine_angle": [],        # 背骨の傾き
    "knee_over_toe": [],      # 膝がつま先より前に出てるか（ピクセル差）
}

for _, row in df.iterrows():
    # 必要な関節のvisibilityチェック
    joints = [
        "left_shoulder", "right_shoulder",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle"
    ]
    if not all(row[f"{j}_visibility"] > VISIBILITY_THRESHOLD for j in joints):
        continue

    frame = row["frame"]

    # 左膝角度（腰→膝→足首）
    left_knee = calculate_angle(
        row["left_hip_x"],   row["left_hip_y"],
        row["left_knee_x"],  row["left_knee_y"],
        row["left_ankle_x"], row["left_ankle_y"]
    )

    # 左股関節角度（肩→腰→膝）
    # スクワットで前傾が深いほどこの角度は小さくなる
    left_hip = calculate_angle(
        row["left_shoulder_x"], row["left_shoulder_y"],
        row["left_hip_x"],      row["left_hip_y"],
        row["left_knee_x"],     row["left_knee_y"]
    )

    # 背骨の傾き（左肩→左腰のベクトルと垂直方向の角度）
    # 0°=完全に直立、90°=水平に倒れてる
    spine_dx = row["left_shoulder_x"] - row["left_hip_x"]
    spine_dy = row["left_shoulder_y"] - row["left_hip_y"]
    spine_angle = np.degrees(np.arctan2(abs(spine_dx), abs(spine_dy)))

    # 膝がつま先より前に出てるか（x座標の差）
    # 正の値 = 膝がつま先より前
    # 負の値 = 膝がつま先より後ろ（安全）
    knee_over_toe = row["left_knee_x"] - row["left_foot_index_x"]

    data["frame"].append(frame)
    data["left_knee_angle"].append(left_knee)
    data["left_hip_angle"].append(left_hip)
    data["spine_angle"].append(spine_angle)
    data["knee_over_toe"].append(knee_over_toe)

result_df = pd.DataFrame(data)

# スムージング
window = 15
for col in ["left_knee_angle", "left_hip_angle", "spine_angle", "knee_over_toe"]:
    result_df[col] = result_df[col].rolling(window, center=True).mean()

# 4つのグラフを並べて描画
fig, axes = plt.subplots(4, 1, figsize=(12, 14))

axes[0].plot(result_df["frame"], result_df["left_knee_angle"], color="blue")
axes[0].axhline(y=90, color="green", linestyle="--", alpha=0.5, label="90°")
axes[0].set_title("① 膝の屈曲角度（180°=伸びてる、小さいほど深くしゃがんでる）")
axes[0].set_ylabel("角度（度）")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

axes[1].plot(result_df["frame"], result_df["left_hip_angle"], color="orange")
axes[1].axhline(y=90, color="green", linestyle="--", alpha=0.5, label="90°")
axes[1].set_title("② 股関節角度（肩→腰→膝）（小さいほど前傾が深い）")
axes[1].set_ylabel("角度（度）")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

axes[2].plot(result_df["frame"], result_df["spine_angle"], color="red")
axes[2].axhline(y=30, color="orange", linestyle="--", alpha=0.5, label="30°（前傾許容ライン）")
axes[2].set_title("③ 背骨の傾き（0°=直立、大きいほど前傾してる）")
axes[2].set_ylabel("角度（度）")
axes[2].legend()
axes[2].grid(True, alpha=0.3)

axes[3].plot(result_df["frame"], result_df["knee_over_toe"], color="purple")
axes[3].axhline(y=0, color="red", linestyle="--", alpha=0.5, label="つま先ライン")
axes[3].set_title("④ 膝とつま先の位置関係（正=膝が前に出てる、負=安全）")
axes[3].set_ylabel("差（比率）")
axes[3].set_xlabel("フレーム")
axes[3].legend()
axes[3].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("data/processed/squat_analysis.png", dpi=150, bbox_inches="tight")
plt.close()

print("✅ data/processed/squat_analysis.png に保存しました")
print(f"\n有効フレーム数: {len(result_df)}")
print(f"\n【膝】最小: {result_df['left_knee_angle'].min():.1f}°")
print(f"【股関節】最小: {result_df['left_hip_angle'].min():.1f}°")
print(f"【背骨】最大傾き: {result_df['spine_angle'].max():.1f}°")
