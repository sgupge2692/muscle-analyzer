# ────────────────────────────────────────────────
# Muscle Analyzer Backend - Dockerfile
# Railway / 本番用
# ────────────────────────────────────────────────

# Python 3.13 slim（軽量）。numpy 2.5 / scipy 1.18 が Python 3.12+ を要求するため 3.11 は不可
FROM python:3.13-slim

WORKDIR /app

# システム依存ライブラリ
# - libgl1: OpenCV が必要（旧 libgl1-mesa-glx は Debian で非推奨/削除されたため libgl1 を指定）
# - libglib2.0-0: MediaPipe が必要
# - libegl1 / libgles2: MediaPipe の libmediapipe.so が要求する(libEGL.so.1 / libGLESv2.so.2)。
#   無いと PoseLandmarker 生成時に OSError で解析が必ず失敗する
# - curl: ヘルスチェック用
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libegl1 \
    libgles2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージをインストール
# requirements.txt を先にコピーすることで
# コードだけ変わったときに pip install をキャッシュできる（ビルドが速くなる）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート公開（Railway は PORT 環境変数を自動設定する）
EXPOSE 8000

# ヘルスチェック
# Railwayがコンテナの起動確認に使う
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 起動コマンド
# - --host 0.0.0.0: コンテナ外からアクセスできるようにする
# - workers 2: 同時リクエストを2つ処理（動画処理はCPU重いので多くしない）
# - PORT: Railwayが自動設定する環境変数を使う
CMD uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 2 \
    --log-level info
