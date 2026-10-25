# ────────────────────────────────────────────────
# Muscle Analyzer Backend - Dockerfile
# Railway / 本番用
# ────────────────────────────────────────────────

# Python 3.11 slim（軽量）
FROM python:3.11-slim

WORKDIR /app

# システム依存ライブラリ
# - libgl1: OpenCV が必要
# - libglib2.0-0: MediaPipe が必要
# - curl: ヘルスチェック用
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
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
