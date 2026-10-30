"""
websocket_stream.py — WebSocketによるリアルタイムカメラ解析

フロントからbase64エンコードされたフレームを受け取り、
MediaPipeで骨格検出 → 筋肉活動推定 → 結果を返す。

処理フロー:
  フロント（カメラ） → base64フレーム → WebSocket → MediaPipe → 筋肉活動 → フロント
"""
import asyncio
import base64
import json
import logging
import time
from collections import deque
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

logger = logging.getLogger("muscle_analyzer.ws")

MODEL_PATH    = "src/pose/pose_landmarker.task"
FRAME_HISTORY = 30   # 筋肉活動推定に使うフレーム数
TARGET_WIDTH  = 480  # 処理解像度（小さいほど速い）


class RealtimeAnalyzer:
    """
    WebSocketセッションごとに1インスタンス生成。
    フレームを受け取って骨格検出・筋肉活動推定を行う。
    """

    def __init__(self, exercise: str = "Squats", target_angle: float = 110.0):
        self.exercise     = exercise
        self.target_angle = target_angle
        self.detector     = self._create_detector()
        self.frame_buffer: deque = deque(maxlen=FRAME_HISTORY)
        self.frame_count  = 0
        self.last_result  = None
        self.fps_counter  = deque(maxlen=30)

    def _create_detector(self):
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return mp_vision.PoseLandmarker.create_from_options(options)

    def process_frame(self, frame_b64: str) -> Optional[dict]:
        """
        base64フレームを処理して結果を返す。
        2フレームに1回のみ骨格検出を実行（速度改善）。
        """
        t0 = time.perf_counter()
        self.frame_count += 1

        # 2フレームに1回のみ処理
        if self.frame_count % 2 != 0 and self.last_result:
            return self.last_result

        try:
            img_bytes = base64.b64decode(frame_b64)
            nparr    = np.frombuffer(img_bytes, np.uint8)
            frame    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return None

            # 解像度縮小
            h, w = frame.shape[:2]
            if w > TARGET_WIDTH:
                scale = TARGET_WIDTH / w
                frame = cv2.resize(frame, (TARGET_WIDTH, int(h * scale)))

            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_img)

            if not result.pose_landmarks:
                return {"type": "no_pose", "frame": self.frame_count}

            landmarks       = result.pose_landmarks[0]
            world_landmarks = result.pose_world_landmarks[0] if result.pose_world_landmarks else None

            # 関節座標を辞書化
            lm_dict = {}
            NAMES = [
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
            for i, lm in enumerate(landmarks):
                lm_dict[NAMES[i]] = {
                    "x": round(lm.x, 4), "y": round(lm.y, 4),
                    "z": round(lm.z, 4), "v": round(lm.visibility, 4)
                }

            # world座標（3Dビューア用）
            world_dict = {}
            if world_landmarks:
                for i, lm in enumerate(world_landmarks):
                    world_dict[NAMES[i]] = {
                        "x": round(lm.x, 4),
                        "y": round(lm.y, 4),
                        "z": round(lm.z, 4),
                    }

            # 膝角度を計算してフレームバッファに追加
            knee_angle = self._calc_knee_angle(lm_dict)
            self.frame_buffer.append({
                "frame":     self.frame_count,
                "landmarks": world_dict,
                "knee_angle": knee_angle,
            })

            # 筋肉活動推定（バッファが5フレーム以上あれば実行）
            activations = {}
            if len(self.frame_buffer) >= 5:
                activations = self._estimate_activations()

            # FPS計算
            elapsed = time.perf_counter() - t0
            self.fps_counter.append(elapsed)
            fps = 1.0 / (sum(self.fps_counter) / len(self.fps_counter))

            self.last_result = {
                "type":        "pose",
                "frame":       self.frame_count,
                "landmarks":   lm_dict,
                "world":       world_dict,
                "knee_angle":  knee_angle,
                "activations": activations,
                "fps":         round(fps, 1),
            }
            return self.last_result

        except Exception as e:
            logger.error(f"フレーム処理エラー: {e}")
            return {"type": "error", "message": str(e)}

    def _calc_knee_angle(self, lm: dict) -> dict:
        """左右の膝角度を計算"""
        angles = {}
        for side in ("left", "right"):
            try:
                hip   = np.array([lm[f"{side}_hip"]["x"],   lm[f"{side}_hip"]["y"]])
                knee  = np.array([lm[f"{side}_knee"]["x"],  lm[f"{side}_knee"]["y"]])
                ankle = np.array([lm[f"{side}_ankle"]["x"], lm[f"{side}_ankle"]["y"]])
                v1 = hip - knee; v2 = ankle - knee
                cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
                angles[side] = round(float(np.degrees(np.arccos(np.clip(cos_a, -1, 1)))), 1)
            except Exception:
                angles[side] = None
        return angles

    def _estimate_activations(self) -> dict:
        """バッファのフレームから筋肉活動を推定（ルールベース）"""
        import sys, os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        try:
            import json as _json
            from pathlib import Path

            mapping_path = Path(__file__).parent.parent.parent / "data/muscle_mapping.json"
            with open(mapping_path) as f:
                mapping = _json.load(f)

            muscle_ids     = mapping["exercise_muscle_mapping"].get(self.exercise, [])
            muscle_groups  = mapping["muscle_groups"]
            active_muscles = [muscle_groups[str(i)] for i in muscle_ids]

            # 最新フレームの膝角度から簡易推定
            recent = list(self.frame_buffer)[-10:]
            angles = [f["knee_angle"].get("right") for f in recent if f["knee_angle"].get("right")]
            if not angles:
                return {}

            avg_angle = sum(angles) / len(angles)
            min_angle = min(angles)

            # 膝角度が小さいほどQuadricepsが活動
            quad_act  = max(0.0, min(1.0, (180 - min_angle) / 110))
            glute_act = quad_act * 0.85
            ham_act   = quad_act * 0.65
            calf_act  = quad_act * 0.25

            base = {
                "Quadriceps": round(quad_act * 0.35, 4),
                "Gluteus":    round(glute_act * 0.25, 4),
                "Hamstring":  round(ham_act * 0.18, 4),
                "Lower_Back": round(0.08, 4),
                "Calves":     round(calf_act * 0.07, 4),
                "Inner_Thigh":round(0.05, 4),
            }
            # 正規化
            total = sum(base.values())
            return {k: round(v / total, 4) for k, v in base.items()} if total > 0 else base

        except Exception as e:
            logger.warning(f"活動推定エラー: {e}")
            return {}


async def websocket_stream_endpoint(websocket: WebSocket, exercise: str = "Squats"):
    """
    WebSocketエンドポイント本体
    ws://localhost:8000/ws/stream?exercise=Squats
    """
    await websocket.accept()
    analyzer = RealtimeAnalyzer(exercise=exercise)
    logger.info(f"WebSocket接続: exercise={exercise}")

    try:
        while True:
            # フロントからフレームを受信
            data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            msg  = json.loads(data)

            if msg.get("type") == "frame":
                result = analyzer.process_frame(msg["data"])
                if result:
                    await websocket.send_text(json.dumps(result))

            elif msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg.get("type") == "stop":
                break

    except WebSocketDisconnect:
        logger.info("WebSocket切断")
    except asyncio.TimeoutError:
        logger.info("WebSocketタイムアウト")
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        logger.info("WebSocketセッション終了")
