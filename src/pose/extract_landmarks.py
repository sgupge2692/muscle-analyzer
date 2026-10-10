import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import csv
import os

# ランドマークの名前（番号→部位名の対応）
# これを知っておくとCSVが読みやすくなる
LANDMARK_NAMES = [
    "nose",           # 0: 鼻
    "left_eye_inner", # 1: 左目内側
    "left_eye",       # 2: 左目
    "left_eye_outer", # 3: 左目外側
    "right_eye_inner",# 4: 右目内側
    "right_eye",      # 5: 右目
    "right_eye_outer",# 6: 右目外側
    "left_ear",       # 7: 左耳
    "right_ear",      # 8: 右耳
    "mouth_left",     # 9: 口左
    "mouth_right",    # 10: 口右
    "left_shoulder",  # 11: 左肩
    "right_shoulder", # 12: 右肩
    "left_elbow",     # 13: 左肘
    "right_elbow",    # 14: 右肘
    "left_wrist",     # 15: 左手首
    "right_wrist",    # 16: 右手首
    "left_pinky",     # 17: 左小指
    "right_pinky",    # 18: 右小指
    "left_index",     # 19: 左人差し指
    "right_index",    # 20: 右人差し指
    "left_thumb",     # 21: 左親指
    "right_thumb",    # 22: 右親指
    "left_hip",       # 23: 左腰
    "right_hip",      # 24: 右腰
    "left_knee",      # 25: 左膝
    "right_knee",     # 26: 右膝
    "left_ankle",     # 27: 左足首
    "right_ankle",    # 28: 右足首
    "left_heel",      # 29: 左かかと
    "right_heel",     # 30: 右かかと
    "left_foot_index",# 31: 左つま先
    "right_foot_index"# 32: 右つま先
]

# モデルの設定
model_path = "src/pose/pose_landmarker.task"
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.PoseLandmarkerOptions(base_options=base_options)
detector = vision.PoseLandmarker.create_from_options(options)

# 動画を開く
cap = cv2.VideoCapture("data/raw/squat_sample.mp4")

# CSVのヘッダーを作成
# frame, nose_x, nose_y, nose_z, left_shoulder_x, ... という形式
header = ["frame"]
for name in LANDMARK_NAMES:
    header += [f"{name}_x", f"{name}_y", f"{name}_z", f"{name}_visibility"]

# CSVに書き込み
output_path = "data/processed/squat_landmarks.csv"
with open(output_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)  # ヘッダー行を書く

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)

        if result.pose_landmarks:
            landmarks = result.pose_landmarks[0]

            # 1行分のデータを作成
            row = [frame_count]
            for landmark in landmarks:
                row += [
                    round(landmark.x, 4),          # x座標（0〜1の比率）
                    round(landmark.y, 4),          # y座標（0〜1の比率）
                    round(landmark.z, 4),          # z座標（奥行き）
                    round(landmark.visibility, 4)  # 見えてるか（0〜1）
                ]
            writer.writerow(row)

        frame_count += 1
        if frame_count % 30 == 0:
            print(f"{frame_count}フレーム処理済み...")

cap.release()
print(f"✅ 完了！{output_path} に保存しました")
