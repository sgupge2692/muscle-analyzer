import sys, json, shutil, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from pose.extract_landmarks import extract_landmarks
from anatomy.angle_features import compute_angle_features
from anatomy.rep_detector import load_knee_angles, detect_reps
from anatomy.muscle_activation import estimate_activation

app = FastAPI(title="Muscle Analyzer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAPPING_JSON = Path("data/muscle_mapping.json")
with open(MAPPING_JSON) as f:
    MAPPING = json.load(f)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    exercise: str = "Squat_Hold"
):
    if exercise not in MAPPING["exercise_muscle_mapping"]:
        raise HTTPException(400, f"未対応の種目: {exercise}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 動画を一時保存
        tmp_video = Path(tmpdir) / file.filename
        with open(tmp_video, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # ランドマーク抽出
        landmarks_csv = Path(tmpdir) / "landmarks.csv"
        try:
            extract_landmarks(str(tmp_video), str(landmarks_csv))
        except Exception as e:
            raise HTTPException(500, f"ランドマーク抽出失敗: {e}")

        # 角度特徴量
        try:
            features = compute_angle_features(str(landmarks_csv))
        except Exception as e:
            raise HTTPException(500, f"角度計算失敗: {e}")

        # レップ検出
        angles = load_knee_angles(str(landmarks_csv))
        reps   = detect_reps(angles)

        # 筋肉活動推定
        muscle_ids     = MAPPING["exercise_muscle_mapping"][exercise]
        muscle_groups  = MAPPING["muscle_groups"]
        active_muscles = [muscle_groups[str(i)] for i in muscle_ids]
        activations    = estimate_activation(features, active_muscles)

        # レップ別集計
        rep_data = {}
        if reps:
            for r in reps:
                key  = f"rep_{r['rep']}"
                mask = (activations.index >= r["start"]) & (activations.index <= r["end"])
                sl   = activations[mask]
                rep_data[key] = {
                    col: round(float(sl[col].mean()), 4)
                    for col in sl.columns
                }
        else:
            rep_data["rep_1"] = {
                col: round(float(activations[col].mean()), 4)
                for col in activations.columns
            }

    return {
        "exercise": exercise,
        "total_reps": len(rep_data),
        "activations": rep_data
    }
