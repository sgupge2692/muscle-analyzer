# デプロイ手順書

## 構成

```
GitHub (sgupge2692/muscle-analyzer)
├── frontend/ → Vercel（自動デプロイ）
└── backend/  → Railway（Dockerコンテナ）
```

## 1. バックエンド（Railway）

### 初回セットアップ

1. https://railway.app にアクセス → GitHubでログイン
2. 「New Project」→「Deploy from GitHub repo」→ `muscle-analyzer` を選択
3. 「Add Service」→「GitHub Repo」→ Root Directory を `backend/` に設定
4. 環境変数を設定（Variables タブ）:

```
ENV=production
ALLOWED_ORIGINS=https://your-app.vercel.app  # 後でVercelのURLに変更
MAX_FILE_SIZE_MB=100
```

5. 「Deploy」→ ログを確認
6. 発行されたURL（例: `https://muscle-analyzer-production.up.railway.app`）をメモ

### 再デプロイ
`git push origin main` するだけで自動デプロイ

### ヘルスチェック確認
```bash
curl https://your-backend.railway.app/health
```

---

## 2. フロントエンド（Vercel）

### 初回セットアップ

1. https://vercel.com にアクセス → GitHubでログイン
2. 「Add New Project」→ `muscle-analyzer` を選択
3. 設定:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js（自動検出）
4. 環境変数を設定:

```
NEXT_PUBLIC_API_URL=https://your-backend.railway.app  # Railwayで発行されたURL
```

5. 「Deploy」
6. 発行されたURL（例: `https://muscle-analyzer.vercel.app`）をメモ

### デプロイ後の追加作業

RailwayのALLOWED_ORIGINSをVercelのURLに更新:
```
ALLOWED_ORIGINS=https://muscle-analyzer.vercel.app
```

### 再デプロイ
`git push origin main` するだけで自動デプロイ

---

## 3. ローカル開発

```bash
# バックエンド
cd backend
cp .env.example .env         # 初回のみ
source ../.venv/bin/activate
uvicorn src.api.main:app --reload --port 8000

# フロントエンド（別タブ）
cd frontend
cp .env.local.example .env.local  # 初回のみ
npm run dev
```

---

## 4. 環境変数一覧

### バックエンド（Railway）
| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `ENV` | 実行環境（development/production） | development |
| `ALLOWED_ORIGINS` | CORSで許可するURL | http://localhost:3000 |
| `MAX_FILE_SIZE_MB` | アップロード上限（MB） | 100 |
| `PORT` | Railwayが自動設定 | 8000 |

### フロントエンド（Vercel）
| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `NEXT_PUBLIC_API_URL` | バックエンドAPIのURL | http://localhost:8000 |

---

## 5. トラブルシューティング

### CORSエラーが出る
→ RailwayのALLOWED_ORIGINSにVercelのURLが入っているか確認

### Railway でビルドが失敗する
→ ログを確認。`libgl1-mesa-glx` が見つからない場合はDockerfileのaptパッケージを確認

### Vercel でビルドが失敗する
→ `frontend/` がRoot Directoryに設定されているか確認
