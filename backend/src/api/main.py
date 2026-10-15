import sys, json, shutil, tempfile, os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from pose.extract_landmarks import extract_landmarks
from anatomy.angle_features import compute_angle_features
from anatomy.rep_detector import load_knee_angles, detect_reps
from anatomy.muscle_activation import estimate_activation

app = FastAPI(title="Muscle Analyzer API", version="0.2.0")

_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

MAPPING_JSON = Path("data/muscle_mapping.json")
with open(MAPPING_JSON) as f:
    MAPPING = json.load(f)

# MLモデルは起動時に読み込む（失敗しても起動は続ける）
_ml_available = False
try:
    from anatomy.ml_predictor import load_model, predict_muscles
    load_model()
    _ml_available = True
    print("MLモデルロード成功")
except Exception as e:
    print(f"MLモデルロード失敗（ルールベースのみ使用）: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "ml_available": _ml_available}


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    exercise: str = "Squat_Hold",
    target_angle: float = 110.0,
    ml_mode: bool = False,
):
    if exercise not in MAPPING["exercise_muscle_mapping"]:
        raise HTTPException(400, f"未対応の種目: {exercise}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_video = Path(tmpdir) / file.filename
        with open(tmp_video, "wb") as f:
            shutil.copyfileobj(file.file, f)

        landmarks_csv = Path(tmpdir) / "landmarks.csv"
        try:
            extract_landmarks(str(tmp_video), str(landmarks_csv))
        except Exception as e:
            raise HTTPException(500, f"ランドマーク抽出失敗: {e}")

        try:
            features = compute_angle_features(str(landmarks_csv))
        except Exception as e:
            raise HTTPException(500, f"角度計算失敗: {e}")

        angles = load_knee_angles(str(landmarks_csv))
        reps   = detect_reps(angles, target_angle=target_angle)

        muscle_ids     = MAPPING["exercise_muscle_mapping"][exercise]
        muscle_groups  = MAPPING["muscle_groups"]
        active_muscles = [muscle_groups[str(i)] for i in muscle_ids]

        # ルールベース推定
        activations = estimate_activation(features, active_muscles)

        # MLモード：モデルが使える場合のみ
        ml_scores = None
        if ml_mode and _ml_available:
            try:
                ml_scores = predict_muscles(features)
            except Exception as e:
                print(f"ML推論失敗: {e}")

        # レップごとの集計
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

    response = {
        "exercise": exercise,
        "total_reps": len(rep_data),
        "activations": rep_data,
        "ml_available": _ml_available,
    }
    if ml_scores is not None:
        response["ml_scores"] = ml_scores

    return response
