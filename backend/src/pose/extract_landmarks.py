import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import csv
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

LANDMARK_NAMES = [
    "nose","left_eye_inner","left_eye","left_eye_outer",
    "right_eye_inner","right_eye","right_eye_outer",
    "left_ear","right_ear","mouth_left","mouth_right",
    "left_shoulder","right_shoulder","left_elbow","right_elbow",
    "left_wrist","right_wrist","left_pinky","right_pinky",
    "left_index","right_index","left_thumb","right_thumb",
    "left_hip","right_hip","left_knee","right_knee",
    "left_ankle","right_ankle","left_heel","right_heel",
    "left_foot_index","right_foot_index"
]

MODEL_PATH = "src/pose/pose_landmarker.task"


def extract_landmarks(
    video_path: str,
    output_csv: str,
    frame_skip: int = 2,       # フレームスキップ数（2=1フレームおきに処理、速度2倍）
    max_frames: Optional[int] = None,  # 最大処理フレーム数（Noneで全フレーム）
) -> int:
    """
    動画からMediaPipeでランドマークを抽出してCSVに保存する

    速度改善:
    - frame_skip=2 で処理量を1/2に削減（30fps動画→15fps相当）
    - MediaPipe Liteモデルを使用（重いFullモデルより2倍高速）
    - output_segmentation_masks=False でセグメンテーション無効化

    Args:
        video_path:  入力動画パス
        output_csv:  出力CSVパス
        frame_skip:  処理するフレームの間隔（1=全フレーム、2=1/2、3=1/3）
        max_frames:  最大処理フレーム数（長い動画の制限用）
    Returns:
        処理フレーム数
    """
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=False,
        num_poses=1,                    # 1人のみ検出（速度向上）
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"動画情報: {total_frames}フレーム / {fps:.1f}fps / frame_skip={frame_skip}")

    header = ["frame"]
    for name in LANDMARK_NAMES:
        header += [f"{name}_x", f"{name}_y", f"{name}_z", f"{name}_visibility"]
    for name in LANDMARK_NAMES:
        header += [f"{name}_wx", f"{name}_wy", f"{name}_wz"]

    frame_count = 0
    detected    = 0
    processed   = 0

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # フレームスキップ
            if frame_count % frame_skip != 0:
                frame_count += 1
                continue

            # 最大フレーム数制限
            if max_frames and processed >= max_frames:
                break

            # 解像度を下げて高速化（幅640px以上なら縮小）
            h, w = frame.shape[:2]
            if w > 640:
                scale  = 640 / w
                frame  = cv2.resize(frame, (640, int(h * scale)))

            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_img)

            if result.pose_landmarks:
                landmarks       = result.pose_landmarks[0]
                world_landmarks = result.pose_world_landmarks[0] if result.pose_world_landmarks else None

                row = [frame_count]
                for lm in landmarks:
                    row += [round(lm.x, 4), round(lm.y, 4),
                            round(lm.z, 4), round(lm.visibility, 4)]
                if world_landmarks:
                    for lm in world_landmarks:
                        row += [round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)]
                else:
                    row += [0.0] * (len(LANDMARK_NAMES) * 3)

                writer.writerow(row)
                detected += 1

            frame_count += 1
            processed   += 1

            if processed % 30 == 0:
                print(f"  {processed}フレーム処理済み...")

    cap.release()
    print(f"完了: {detected}/{processed}フレーム検出（スキップ後）→ {output_csv}")
    return processed


def landmarks_csv_to_3d_sequence(csv_path: str) -> list[dict]:
    """CSVからworld座標の時系列データを抽出してフロント送信用に変換する"""
    import pandas as pd

    df       = pd.read_csv(csv_path)
    sequence = []

    for _, row in df.iterrows():
        frame_data = {"frame": int(row["frame"]), "landmarks": {}}
        for name in LANDMARK_NAMES:
            wx_col = f"{name}_wx"
            if wx_col in row:
                frame_data["landmarks"][name] = {
                    "x": round(float(row[wx_col]), 4),
                    "y": round(float(row[f"{name}_wy"]), 4),
                    "z": round(float(row[f"{name}_wz"]), 4),
                }
        sequence.append(frame_data)

    return sequence


if __name__ == "__main__":
    extract_landmarks(
        video_path="data/raw/squat_sample.mp4",
        output_csv="data/processed/squat_landmarks.csv",
        frame_skip=2,
    )
