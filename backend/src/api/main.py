import sys, json, shutil, tempfile, os, uuid, logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from pose.extract_landmarks import extract_landmarks
from anatomy.angle_features import compute_angle_features
from anatomy.rep_detector import load_knee_angles, detect_reps
from anatomy.muscle_activation import estimate_activation
from anatomy.form_checker import check_form

# ── ロギング設定 ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("muscle_analyzer")

# ── アップロード制限 ────────────────────────────────────────
MAX_FILE_SIZE_MB   = int(os.getenv("MAX_FILE_SIZE_MB", "100"))   # 100MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "video/webm", "video/x-matroska",
}
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}

# ── FastAPI ─────────────────────────────────────────────────
app = FastAPI(
    title="Muscle Analyzer API",
    version="0.4.0",
    # 本番では docs を無効化（情報漏洩防止）
    docs_url="/docs" if os.getenv("ENV", "development") == "development" else None,
    redoc_url=None,
)

# ── CORS ────────────────────────────────────────────────────
_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Accept"],   # * → 必要なヘッダーのみ
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
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    _rate_limit_available = True
    logger.info("レートリミット有効")
except ImportError:
    _rate_limit_available = False
    logger.warning("slowapi未インストール。レートリミット無効（pip install slowapi で有効化）")

    # フォールバック用のダミーデコレータ
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


# ── ヘルパー：ファイルバリデーション ───────────────────────
def _validate_video(file: UploadFile, content: bytes) -> None:
    """アップロードファイルの安全性検証"""
    # 1. ファイルサイズ
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            413, f"ファイルサイズが上限（{MAX_FILE_SIZE_MB}MB）を超えています"
        )
    if len(content) == 0:
        raise HTTPException(400, "空のファイルです")

    # 2. 拡張子（Content-Typeは偽装できるので拡張子も確認）
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                415, f"対応していないファイル形式です（対応: {', '.join(ALLOWED_EXTENSIONS)}）"
            )

    # 3. MIMEタイプ
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            415, f"対応していないContent-Typeです: {file.content_type}"
        )

    # 4. マジックバイト（ファイル先頭バイトで実際の形式を確認）
    magic = content[:12]
    is_mp4  = magic[4:8] in (b"ftyp", b"mdat", b"moov") or magic[:4] == b"\x00\x00\x00\x18"
    is_mov  = b"ftyp" in magic or b"moov" in magic
    is_avi  = magic[:4] == b"RIFF" and magic[8:12] == b"AVI "
    is_webm = magic[:4] == b"\x1a\x45\xdf\xa3"
    if not any([is_mp4, is_mov, is_avi, is_webm]):
        # マジックバイトで判定できない場合は警告のみ（厳格にしすぎると誤検知する）
        logger.warning(f"マジックバイト不一致: {magic.hex()[:24]} - 処理を続行")


# ── エンドポイント ──────────────────────────────────────────
@app.get("/health")
def health():
    """ヘルスチェック（本番では最小限の情報のみ返す）"""
    is_dev = os.getenv("ENV", "development") == "development"
    base = {"status": "ok", "version": "0.4.0"}
    if is_dev:
        base["ml_available"] = _ml_available
        base["supported_exercises"] = list(MAPPING["exercise_muscle_mapping"].keys())
    return base


@app.post("/analyze")
@limiter.limit("10/minute")   # IP単位で1分10回まで
async def analyze(
    request: Request,          # slowapi に必要
    file: UploadFile = File(...),
    exercise: str = "Squats",
    target_angle: float = 110.0,
    ml_mode: bool = False,
):
    # ── 入力バリデーション ──────────────────────────────────
    # 種目
    if exercise not in MAPPING["exercise_muscle_mapping"]:
        raise HTTPException(400, f"未対応の種目です: {exercise}")

    # 目標角度（人体の可動域範囲に制限）
    if not (40.0 <= target_angle <= 170.0):
        raise HTTPException(400, "target_angleは40〜170の範囲で指定してください")

    # ファイル読み込み・バリデーション
    content = await file.read()
    _validate_video(file, content)

    # ── 処理 ───────────────────────────────────────────────
    # ファイル名はuuidで無害化（Path Traversal対策）
    safe_filename = f"{uuid.uuid4()}{Path(file.filename or 'video.mp4').suffix.lower()}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_video = Path(tmpdir) / safe_filename
        tmp_video.write_bytes(content)

        # 1. 骨格検出
        landmarks_csv = Path(tmpdir) / "landmarks.csv"
        try:
            extract_landmarks(str(tmp_video), str(landmarks_csv))
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
        activations    = estimate_activation(features, active_muscles, exercise=exercise)

        # 5. MLモード
        ml_scores = None
        if ml_mode and _ml_available:
            try:
                ml_scores = predict_muscles(features)
            except Exception as e:
                logger.warning(f"ML推論失敗: {e}")

        # 6. レップごとの集計 + フォーム診断
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
    }
    if ml_scores is not None:
        response["ml_scores"] = ml_scores

    return response
