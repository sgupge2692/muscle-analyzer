import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os

# モデルのパス（すでにダウンロード済みなのでスキップされる）
model_path = "src/pose/pose_landmarker.task"
if not os.path.exists(model_path):
    print("モデルをダウンロード中...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
        model_path
    )

# 骨格のつながり定義（どの点とどの点を線で繋ぐか）
# MediaPipeの33個のランドマークの番号で指定する
CONNECTIONS = [
    (11, 12),  # 左肩 - 右肩
    (11, 13), (13, 15),  # 左腕
    (12, 14), (14, 16),  # 右腕
    (11, 23), (12, 24),  # 肩 - 腰
    (23, 24),  # 左腰 - 右腰
    (23, 25), (25, 27),  # 左脚
    (24, 26), (26, 28),  # 右脚
    (0, 11), (0, 12),   # 鼻 - 肩
]

# 検出器の設定
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.PoseLandmarkerOptions(base_options=base_options)
detector = vision.PoseLandmarker.create_from_options(options)

# 動画を開く
cap = cv2.VideoCapture("data/raw/squat_sample.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("data/processed/squat_pose.mp4", fourcc, 30, (
    int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
    int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
))

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
        h, w, _ = frame.shape

        # 点を描画
        for landmark in landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        # 線を描画（ここが追加部分）
        for start_idx, end_idx in CONNECTIONS:
            x1 = int(landmarks[start_idx].x * w)
            y1 = int(landmarks[start_idx].y * h)
            x2 = int(landmarks[end_idx].x * w)
            y2 = int(landmarks[end_idx].y * h)
            cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)

    out.write(frame)
    frame_count += 1
    if frame_count % 30 == 0:
        print(f"{frame_count}フレーム処理済み...")

cap.release()
out.release()
print(f"✅ 完了！合計{frame_count}フレーム処理しました")
