import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import csv

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

def extract_landmarks(video_path: str, output_csv: str) -> int:
    """
    動画からMediaPipeでランドマークを抽出してCSVに保存する

    Args:
        video_path: 入力動画パス
        output_csv: 出力CSVパス
    Returns:
        処理フレーム数
    """
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(base_options=base_options)
    detector = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(video_path)

    header = ["frame"]
    for name in LANDMARK_NAMES:
        header += [f"{name}_x", f"{name}_y", f"{name}_z", f"{name}_visibility"]

    frame_count = 0
    detected = 0

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_image)

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                row = [frame_count]
                for lm in landmarks:
                    row += [round(lm.x, 4), round(lm.y, 4),
                            round(lm.z, 4), round(lm.visibility, 4)]
                writer.writerow(row)
                detected += 1

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"  {frame_count}フレーム処理済み...")

    cap.release()
    print(f"完了: {detected}/{frame_count}フレーム検出 → {output_csv}")
    return frame_count


if __name__ == "__main__":
    extract_landmarks(
        video_path="data/raw/squat_sample.mp4",
        output_csv="data/processed/squat_landmarks.csv"
    )
