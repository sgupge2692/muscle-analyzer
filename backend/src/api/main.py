import sys, json, shutil, tempfile, os, uuid, logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, WebSocket
from fastapi.security import HTTPBearer

security = HTTPBearer(auto_error=False)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from pose.extract_landmarks import extract_landmarks, landmarks_csv_to_3d_sequence
from anatomy.angle_features import compute_angle_features
from anatomy.rep_detector import load_knee_angles, detect_reps
from anatomy.muscle_activation import estimate_activation
from anatomy.form_checker import check_form
from api.auth import router as auth_router, get_current_user
from api.websocket_stream import websocket_stream_endpoint

# ── ロギング設定 ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("muscle_analyzer")

# ── アップロード制限 ────────────────────────────────────────
MAX_FILE_SIZE_MB    = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES  = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "video/webm", "video/x-matroska",
}
ALLOWED_EXTENSIONS  = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_EXTS  = {".jpg", ".jpeg", ".png", ".webp"}

# 3Dシーケンスのフレーム間引き率（1=全フレーム, 3=1/3に間引き）
# 30fpsの動画で3にすると10fps相当になりレスポンスサイズが約1/3になる
LANDMARK_3D_STRIDE  = int(os.getenv("LANDMARK_3D_STRIDE", "3"))

# ── FastAPI ─────────────────────────────────────────────────
app = FastAPI(
    title="Muscle Analyzer API",
    version="0.5.0",
    docs_url="/docs" if os.getenv("ENV", "development") == "development" else None,
    redoc_url=None,
)

# 認証ルーターを登録
app.include_router(auth_router)


@app.websocket("/ws/stream")
async def websocket_stream(
    websocket: WebSocket,
    exercise: str = "Squats",
):
    """
    リアルタイムカメラ解析WebSocketエンドポイント
    ws://host/ws/stream?exercise=Squats
    """
    await websocket_stream_endpoint(websocket, exercise=exercise)

# ── CORS ────────────────────────────────────────────────────
_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Accept"],
    max_age=600,
)

# ── セキュリティヘッダー ────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
    return response

# ── レートリミット（slowapi） ───────────────────────────────
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(
            status_code=429,
            content={"detail": "リクエストが多すぎます。しばらく待ってからお試しください。"},
        )

    _rate_limit_available = True
    logger.info("レートリミット有効")
except (ImportError, Exception) as e:
    _rate_limit_available = False
    logger.warning(f"slowapi未インストール。レートリミット無効（pip install slowapi で有効化）")

    class _DummyLimiter:
        def limit(self, *a, **kw):
            def decorator(f): return f
            return decorator
    limiter = _DummyLimiter()

# ── データロード ────────────────────────────────────────────
MAPPING_JSON = Path("data/muscle_mapping.json")
with open(MAPPING_JSON) as f:
    MAPPING = json.load(f)

_ml_available = False
try:
    from anatomy.ml_predictor import load_model, predict_muscles
    load_model()
    _ml_available = True
    logger.info("MLモデルロード成功")
except Exception as e:
    logger.warning(f"MLモデルロード失敗（ルールベースのみ使用）: {e}")


# ── ヘルパー：バリデーション ────────────────────────────────
def _validate_video(file: UploadFile, content: bytes) -> None:
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(413, f"ファイルサイズが上限（{MAX_FILE_SIZE_MB}MB）を超えています")
    if len(content) == 0:
        raise HTTPException(400, "空のファイルです")
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(415, f"対応していないファイル形式です（対応: {', '.join(ALLOWED_EXTENSIONS)}）")
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(415, f"対応していないContent-Typeです: {file.content_type}")
    magic = content[:12]
    is_mp4  = magic[4:8] in (b"ftyp", b"mdat", b"moov") or magic[:4] == b"\x00\x00\x00\x18"
    is_mov  = b"ftyp" in magic or b"moov" in magic
    is_avi  = magic[:4] == b"RIFF" and magic[8:12] == b"AVI "
    is_webm = magic[:4] == b"\x1a\x45\xdf\xa3"
    if not any([is_mp4, is_mov, is_avi, is_webm]):
        logger.warning(f"マジックバイト不一致: {magic.hex()[:24]} - 処理を続行")


def _validate_image(file: UploadFile, content: bytes) -> None:
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "画像は10MB以下にしてください")
    if len(content) == 0:
        raise HTTPException(400, "空のファイルです")
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(415, "対応していない画像形式です（jpg/png/webp）")
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, f"対応していないContent-Typeです: {file.content_type}")


# ── エンドポイント ──────────────────────────────────────────
@app.get("/health")
def health():
    is_dev = os.getenv("ENV", "development") == "development"
    base = {"status": "ok", "version": "0.5.0"}
    if is_dev:
        base["ml_available"] = _ml_available
        base["supported_exercises"] = list(MAPPING["exercise_muscle_mapping"].keys())
    return base


@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    exercise: str = "Squats",
    target_angle: float = 110.0,
    ml_mode: bool = False,
    body_scale: float = 1.0,
    frame_skip: int = 2,       # フレームスキップ数（速度改善）
    credentials = Depends(security),   # オプション認証（未ログインでも使用可）
):
    # ログイン済みの場合はユーザーIDをログに記録
    current_user_id = None
    if credentials:
        try:
            from api.auth import _verify_jwt
            payload = _verify_jwt(credentials.credentials)
            current_user_id = payload.get("sub")
            logger.info(f"認証済みリクエスト: user={current_user_id}")
        except Exception:
            pass  # 無効なトークンは無視（オプション認証のため）
    if exercise not in MAPPING["exercise_muscle_mapping"]:
        raise HTTPException(400, f"未対応の種目です: {exercise}")
    if not (40.0 <= target_angle <= 170.0):
        raise HTTPException(400, "target_angleは40〜170の範囲で指定してください")
    if not (0.5 <= body_scale <= 2.0):
        raise HTTPException(400, "body_scaleは0.5〜2.0の範囲で指定してください")

    content = await file.read()
    _validate_video(file, content)

    safe_filename = f"{uuid.uuid4()}{Path(file.filename or 'video.mp4').suffix.lower()}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_video = Path(tmpdir) / safe_filename
        tmp_video.write_bytes(content)

        # 1. 骨格検出
        landmarks_csv = Path(tmpdir) / "landmarks.csv"
        try:
            extract_landmarks(str(tmp_video), str(landmarks_csv), frame_skip=frame_skip)
        except Exception as e:
            logger.error(f"ランドマーク抽出失敗: {e}", exc_info=True)
            raise HTTPException(500, "動画の解析に失敗しました。別の動画をお試しください")

        # 2. 関節角度計算
        try:
            features = compute_angle_features(str(landmarks_csv))
        except Exception as e:
            logger.error(f"角度計算失敗: {e}", exc_info=True)
            raise HTTPException(500, "角度計算に失敗しました")

        # 3. レップ検出
        angles = load_knee_angles(str(landmarks_csv))
        reps   = detect_reps(
            angles,
            angle_min=max(40.0, target_angle - 50),
            angle_max=target_angle + 15,
            min_prominence=15.0,
        )
        logger.info(f"レップ検出: {len(reps)}件 / exercise={exercise} / target={target_angle}°")

        # 4. 筋肉活動推定
        muscle_ids     = MAPPING["exercise_muscle_mapping"][exercise]
        muscle_groups  = MAPPING["muscle_groups"]
        active_muscles = [muscle_groups[str(i)] for i in muscle_ids]
        activations    = estimate_activation(features, active_muscles, exercise=exercise, body_scale=body_scale)

        # 5. 3Dランドマーク時系列（MLモードより前に生成）
        landmarks_3d_full = landmarks_csv_to_3d_sequence(str(landmarks_csv))
        landmarks_3d = landmarks_3d_full[::LANDMARK_3D_STRIDE]
        logger.info(f"3Dランドマーク: {len(landmarks_3d_full)}フレーム → {len(landmarks_3d)}フレーム（stride={LANDMARK_3D_STRIDE}）")

        # 6. MLモード（PyTorch CNN優先、なければscikit-learn）
        ml_scores = None
        if ml_mode:
            try:
                from anatomy.ml_predictor import predict_muscles_torch, is_torch_model_available
                if is_torch_model_available():
                    muscle_id_map = {i: muscle_groups[str(i)] for i in range(len(muscle_groups))}
                    ml_scores = predict_muscles_torch(landmarks_3d_full, muscle_id_map)
                    logger.info("PyTorch CNN推論成功")
                elif _ml_available:
                    ml_scores = predict_muscles(features)
                    logger.info("scikit-learn推論（CNNモデル未訓練）")
            except Exception as e:
                logger.warning(f"ML推論失敗: {e}")

        # 7. レップごとの集計 + フォーム診断
        rep_data      = {}
        form_feedback = {}

        if reps:
            for r in reps:
                key  = f"rep_{r['rep']}"
                mask = (activations.index >= r["start"]) & (activations.index <= r["end"])
                sl   = activations[mask]
                rep_data[key] = {
                    col: round(float(sl[col].mean()), 4)
                    for col in sl.columns
                }
                issues = check_form(features, exercise, r["start"], r["end"], target_angle=target_angle)
                if issues:
                    form_feedback[key] = issues
        else:
            rep_data["rep_1"] = {
                col: round(float(activations[col].mean()), 4)
                for col in activations.columns
            }
            issues = check_form(features, exercise, target_angle=target_angle)
            if issues:
                form_feedback["rep_1"] = issues


    response = {
        "exercise":      exercise,
        "total_reps":    len(rep_data),
        "activations":   rep_data,
        "form_feedback": form_feedback,
        "ml_available":  _ml_available,
        "landmarks_3d":  landmarks_3d,
    }
    if ml_scores is not None:
        response["ml_scores"] = ml_scores

    return response


@app.post("/estimate_body")
@limiter.limit("5/minute")
async def estimate_body(
    request: Request,
    front_image: UploadFile = File(...),
    side_image:  UploadFile = File(None),
    height_cm:   float = 170.0,
):
    """
    正面・側面写真から体型パラメータを推定する（フェーズ2機能）

    現時点はMediaPipeで肩幅・股関節幅・骨格比率を推定する簡易版。
    将来的にはSMPLモデルに差し替えて体積・筋断面積も推定する予定。

    Returns:
        shoulder_width_cm: 肩幅推定値（cm）
        hip_width_cm:      骨盤幅推定値（cm）
        torso_ratio:       胴体/身長比
        leg_ratio:         脚長/身長比
        body_scale:        全体スケール係数（筋肉活動推定の重み補正に使用）
    """
    if not (100.0 <= height_cm <= 220.0):
        raise HTTPException(400, "height_cmは100〜220の範囲で指定してください")

    front_content = await front_image.read()
    _validate_image(front_image, front_content)

    side_content = None
    if side_image and side_image.filename:
        side_content = await side_image.read()
        _validate_image(side_image, side_content)

    try:
        result = _estimate_body_from_images(front_content, side_content, height_cm)
    except Exception as e:
        logger.error(f"体型推定失敗: {e}", exc_info=True)
        raise HTTPException(500, "体型推定に失敗しました")

    return result


def _estimate_body_from_images(
    front_bytes: bytes,
    side_bytes: bytes | None,
    height_cm: float,
) -> dict:
    """
    MediaPipeで正面画像から骨格比率を推定する。

    推定ロジック：
    - 肩幅 = |左肩x - 右肩x| * 画像幅px → cm変換（身長を基準にスケール）
    - 骨盤幅 = |左腰x - 右腰x| * 画像幅px → cm変換
    - 上半身比 = |肩y - 腰y| / |頭y - 足y|
    - 脚長比   = |腰y - 足y| / |頭y - 足y|

    ※ 2D画像からの推定なので奥行き成分は含まない簡易推定。
      精度向上はフェーズ3でSMPLモデルに置き換える。
    """
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    import numpy as np

    MODEL_PATH = "src/pose/pose_landmarker.task"

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.PoseLandmarkerOptions(base_options=base_options)
    detector = mp_vision.PoseLandmarker.create_from_options(options)

    # 正面画像を解析
    nparr  = np.frombuffer(front_bytes, np.uint8)
    img    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h_px, w_px = img.shape[:2]
    rgb    = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_img)

    if not result.pose_landmarks:
        raise ValueError("正面画像から骨格を検出できませんでした。全身が写った画像を使用してください")

    lm = result.pose_landmarks[0]

    # MediaPipe landmark index
    # 11: left_shoulder, 12: right_shoulder
    # 23: left_hip,      24: right_hip
    # 0:  nose,          27: left_ankle, 28: right_ankle
    def pt(idx): return lm[idx]

    left_shoulder  = pt(11)
    right_shoulder = pt(12)
    left_hip       = pt(23)
    right_hip      = pt(24)
    nose           = pt(0)
    left_ankle     = pt(27)
    right_ankle    = pt(28)

    # ピクセル幅→cm変換係数
    # 全身高（画面内）を基準にスケール
    body_top_y    = nose.y
    body_bottom_y = (left_ankle.y + right_ankle.y) / 2
    body_height_ratio = body_bottom_y - body_top_y  # 0〜1の比率

    if body_height_ratio < 0.1:
        raise ValueError("全身が写っていない可能性があります")

    px_per_cm = (body_height_ratio * h_px) / height_cm

    # 肩幅
    shoulder_width_px = abs(left_shoulder.x - right_shoulder.x) * w_px
    shoulder_width_cm = round(shoulder_width_px / px_per_cm, 1)

    # 骨盤幅
    hip_width_px = abs(left_hip.x - right_hip.x) * w_px
    hip_width_cm = round(hip_width_px / px_per_cm, 1)

    # 上半身・脚長比
    shoulder_y     = (left_shoulder.y + right_shoulder.y) / 2
    hip_y          = (left_hip.y + right_hip.y) / 2
    ankle_y        = (left_ankle.y + right_ankle.y) / 2
    torso_ratio    = round((hip_y - shoulder_y) / body_height_ratio, 3)
    leg_ratio      = round((ankle_y - hip_y) / body_height_ratio, 3)

    # 体格スケール係数（標準体型を1.0とする）
    # 肩幅と骨盤幅の比率で体格の「横幅」を標準化
    STANDARD_SHOULDER_CM = 42.0  # 成人男性平均
    body_scale = round(shoulder_width_cm / STANDARD_SHOULDER_CM, 3)

    return {
        "shoulder_width_cm": shoulder_width_cm,
        "hip_width_cm":      hip_width_cm,
        "torso_ratio":       torso_ratio,
        "leg_ratio":         leg_ratio,
        "body_scale":        body_scale,
        "height_cm":         height_cm,
        "note":              "2D画像からの簡易推定。精度向上はSMPLモデルへの移行で対応予定（フェーズ3）",
    }
