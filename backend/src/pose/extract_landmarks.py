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

    通常ランドマーク（画面座標 0~1）に加えて
    pose_world_landmarks（メートル単位の実空間3D座標）も保存する。
    world座標は腰の中点を原点とした右手系座標系で、
    体格に依存しない骨格分析・3Dアバター表示に使用する。

    Args:
        video_path: 入力動画パス
        output_csv: 出力CSVパス
    Returns:
        処理フレーム数
    """
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=False,  # 不要なのでOFF（速度向上）
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(video_path)

    # ヘッダー: 通常座標 + world座標（wx, wy, wz）
    header = ["frame"]
    for name in LANDMARK_NAMES:
        header += [f"{name}_x", f"{name}_y", f"{name}_z", f"{name}_visibility"]
    for name in LANDMARK_NAMES:
        header += [f"{name}_wx", f"{name}_wy", f"{name}_wz"]

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
                landmarks       = result.pose_landmarks[0]
                world_landmarks = result.pose_world_landmarks[0] if result.pose_world_landmarks else None

                row = [frame_count]

                # 通常座標（画面座標 0~1）
                for lm in landmarks:
                    row += [round(lm.x, 4), round(lm.y, 4),
                            round(lm.z, 4), round(lm.visibility, 4)]

                # world座標（メートル単位、腰中点が原点）
                if world_landmarks:
                    for lm in world_landmarks:
                        row += [round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)]
                else:
                    row += [0.0] * (len(LANDMARK_NAMES) * 3)

                writer.writerow(row)
                detected += 1

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"  {frame_count}フレーム処理済み...")

    cap.release()
    print(f"完了: {detected}/{frame_count}フレーム検出 → {output_csv}")
    return frame_count


def landmarks_csv_to_3d_sequence(csv_path: str) -> list[dict]:
    """
    CSVからworld座標の時系列データを抽出してフロント送信用に変換する

    Returns:
        [
          {
            "frame": 0,
            "landmarks": {
              "left_shoulder": {"x": 0.12, "y": -0.45, "z": 0.03},
              ...
            }
          },
          ...
        ]
    """
    import pandas as pd

    df = pd.read_csv(csv_path)
    sequence = []

    for _, row in df.iterrows():
        frame_data = {"frame": int(row["frame"]), "landmarks": {}}
        for name in LANDMARK_NAMES:
            wx_col = f"{name}_wx"
            wy_col = f"{name}_wy"
            wz_col = f"{name}_wz"
            if wx_col in row:
                frame_data["landmarks"][name] = {
                    "x": round(float(row[wx_col]), 4),
                    "y": round(float(row[wy_col]), 4),
                    "z": round(float(row[wz_col]), 4),
                }
        sequence.append(frame_data)

    return sequence


if __name__ == "__main__":
    extract_landmarks(
        video_path="data/raw/squat_sample.mp4",
        output_csv="data/processed/squat_landmarks.csv",
    )
