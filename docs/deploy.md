# デプロイ手順

## バックエンド（Railway）

### 初回セットアップ

1. [railway.app](https://railway.app) にGitHubでログイン
2. **New Project** → **Deploy from GitHub repo** → `sgupge2692/muscle-analyzer`
3. **Add Service** → **GitHub Repo**
4. Settings → **Root Directory** を `backend` に設定（必須）
5. RailwayがDockerfileを自動検出してビルド開始

### 環境変数（Variables タブで設定）

```
ENV=production
JWT_SECRET=<python3 -c "import secrets; print(secrets.token_hex(32))" で生成>
ALLOWED_ORIGINS=https://your-app.vercel.app
MAX_FILE_SIZE_MB=200
LANDMARK_3D_STRIDE=2
USERS_DB_PATH=data/users.json
```

### ユーザー保存先（Supabase）— 本番は必須

Railwayのファイルシステムはデプロイのたびに消えるため、設定しないと登録ユーザーが全員消えます。

1. Supabaseで（AURAとは別の）プロジェクトを作成
2. SQL Editor で `backend/sql/users.sql` を実行
3. Settings → API から **Project URL** と **service_role キー** を取得
4. Railway の Variables に追加：
```
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=<service_roleキー>
```
service_role キーはRLSを無視できる強い権限です。Railway以外（フロント・Git・チャット）に置かないこと。

### ヘルスチェック確認

デプロイ後、発行されたURLで確認：
```bash
curl https://your-app.railway.app/health
# → {"status":"ok","version":"0.6.0"}
```

### ビルド時間の目安

- 初回：10〜15分（MediaPipe等の重いパッケージのビルド）
- 2回目以降：3〜5分（Dockerレイヤーキャッシュ）

---

## フロントエンド（Vercel）

### 初回セットアップ

1. [vercel.com](https://vercel.com) にGitHubでログイン
2. **New Project** → `sgupge2692/muscle-analyzer` をインポート
3. **Root Directory** を `frontend` に設定
4. Framework Preset: **Next.js**（自動検出）

### 環境変数（Environment Variables で設定）

```
NEXT_PUBLIC_API_URL=https://your-app.railway.app
NEXT_PUBLIC_WS_URL=wss://your-app.railway.app
```

### 注意事項

- `wss://`（WebSocket Secure）を使うこと（`ws://`は本番では動かない）
- Railwayのデプロイが完了してからVercelに設定すること

---

## ローカル開発

```bash
# バックエンド
cd backend
source ../.venv/bin/activate
uvicorn src.api.main:app --reload --port 8000

# フロントエンド（別タブ）
cd frontend
npm run dev
```

### macOS Tahoe（26.x）での注意

Python 3.13で `.venv` を作成すること（3.12はensurepipが壊れている場合あり）：

```bash
/opt/homebrew/bin/python3.13 -m venv .venv --without-pip
# pipを手動インストール後
.venv/bin/python -m pip install -r requirements.txt
```

---

## よくあるエラー

| エラー | 原因 | 解決策 |
|--------|------|--------|
| `413 ファイルサイズが上限を超えています` | 動画が200MB超 | ffmpegで短く切る |
| `WebSocket接続失敗` | CORS設定またはorigin不一致 | ALLOWED_ORIGINSを確認 |
| `MLモデルロード失敗` | `.pkl`ファイルなし | 初回はルールベースのみで動作 |
| `pose_landmarker.task not found` | モデルファイルの配置ミス | `backend/src/pose/`に配置されているか確認 |
