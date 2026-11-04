# 開発者ガイド — Muscle Analyzer

## 起動コマンド

### バックエンド

```bash
cd ~/Desktop/01_Development/laboratory/muscle-analyzer

# 初回のみ：venv作成
/opt/homebrew/bin/python3.13 -m venv .venv --without-pip
.venv/bin/python -c "
import urllib.request, zipfile, sys
urllib.request.urlretrieve('https://files.pythonhosted.org/packages/py3/p/pip/pip-24.0-py3-none-any.whl','/tmp/pw.zip')
zipfile.ZipFile('/tmp/pw.zip').extractall([p for p in sys.path if 'site-packages' in p][0])
"
.venv/bin/python -m pip install -r backend/requirements.txt

# 通常起動
cd backend && ../.venv/bin/uvicorn src.api.main:app --reload --port 8000
```

### フロントエンド

```bash
cd ~/Desktop/01_Development/laboratory/muscle-analyzer/frontend

# 初回のみ
npm install

# 通常起動（3000番が空いているか確認してから）
lsof -ti:3000 | xargs kill -9 2>/dev/null; npm run dev
```

ブラウザで `http://localhost:3000` を開く

### 両方まとめて起動（推奨）

```bash
cd ~/Desktop/01_Development/laboratory/muscle-analyzer

# ターミナル1
cd backend && ../.venv/bin/uvicorn src.api.main:app --reload --port 8000

# ターミナル2（Cmd+T で新タブ）
lsof -ti:3000 | xargs kill -9 2>/dev/null
cd frontend && npm run dev
```

### よくあるトラブル

| 症状 | 原因 | 解決 |
|------|------|------|
| 別のアプリ（AURA等）が3000で動いている | ポート競合 | `lsof -ti:3000 \| xargs kill -9` |
| `ModuleNotFoundError: No module named 'pandas'` | venvが古いパスを参照 | `../.venv/bin/uvicorn` で起動 |
| `sw.js 404` | Service Workerなし | 無視してOK（動作に影響なし） |
| バックエンドが起動直後にクラッシュ | .envがない | `cp backend/.env.example backend/.env` して `JWT_SECRET` を設定 |

---

## 環境変数

### バックエンド（`backend/.env`）

```bash
cp backend/.env.example backend/.env
# JWT_SECRETを生成して設定
python3 -c "import secrets; print(secrets.token_hex(32))"
```

```env
ENV=development
JWT_SECRET=<上記で生成した値>
ALLOWED_ORIGINS=http://localhost:3000
MAX_FILE_SIZE_MB=200
LANDMARK_3D_STRIDE=2
USERS_DB_PATH=data/users.json
```

### フロントエンド（`frontend/.env.local`）

```bash
cp frontend/.env.local.example frontend/.env.local
```

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## アプリの主要機能

### 動画アップロード解析
1. 種目を選択（スクワット/デッドリフト等）
2. 目標膝角度をスライダーで設定
3. 動画をドラッグ&ドロップ（最大200MB）
4. 「解析する」→ レップごとの筋肉活動ヒートマップが表示

### リアルタイムカメラ解析
1. 「リアルタイム解析」タブを選択
2. 「▶ リアルタイム解析を開始」をクリック
3. カメラ許可を承認
4. スクワット等をしながらリアルタイムで骨格・筋肉活動を確認

### 3Dアバタービューア
- 解析完了後「3Dアバター」タブに切替
- マウスドラッグ / スワイプで視点回転
- スクロールでズーム
- ▶ボタンで動きを再生
- ↺でリセット

---

## コードの主要ファイル

### バックエンド

```
backend/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPIエントリポイント・全エンドポイント
│   │   ├── auth.py              # JWT認証・bcryptパスワード管理
│   │   └── websocket_stream.py  # リアルタイムカメラ解析（WebSocket）
│   ├── pose/
│   │   └── extract_landmarks.py # MediaPipe骨格検出（フレームスキップ対応）
│   ├── anatomy/
│   │   ├── angle_features.py    # 関節角度・38特徴量の計算
│   │   ├── muscle_activation.py # ルールベース筋肉活動推定
│   │   ├── form_checker.py      # フォームチェック（理想角度範囲との比較）
│   │   ├── ml_predictor.py      # MLモデル推論（sklearn/PyTorch）
│   │   └── musclemap_features.py # MuscleMapデータセット特徴量抽出
│   ├── ml/
│   │   ├── model.py             # 1D-CNN モデル定義
│   │   ├── stgcn.py             # ST-GCN モデル定義
│   │   ├── dataset.py           # MuscleMapデータローダー
│   │   ├── train.py             # 1D-CNN学習スクリプト
│   │   └── train_stgcn.py       # ST-GCN学習スクリプト
│   └── visualization/
│       └── heatmap_renderer.py  # SVGヒートマップ生成（CLI用）
└── data/
    ├── muscle_mapping.json      # 141種目×20筋群マッピング（自前資産）
    └── raw/musclemap_benchmark/ # MuscleMapデータセット本体（gitignore）
```

### フロントエンド

```
frontend/src/
├── app/
│   ├── page.tsx         # メインページ（種目選択・動画アップロード・結果表示）
│   └── layout.tsx       # レイアウト（Geistフォント・メタデータ）
├── components/
│   ├── ResultPanel.tsx      # 解析結果パネル（タブ切替・筋肉活動・フォーム）
│   ├── AvatarViewer3D.tsx   # 3Dカプセル人体モデルビューア
│   ├── CameraAnalyzer.tsx   # リアルタイムカメラ解析UI
│   ├── MuscleHeatmap.tsx    # 体表ヒートマップ（SVG）
│   ├── FormFeedbackCard.tsx # フォームチェック結果表示
│   └── BodyEstimator.tsx    # 体型推定UI（写真アップロード）
├── lib/
│   └── api.ts           # バックエンドAPIクライアント関数
└── types/
    └── analysis.ts      # TypeScript型定義
```

---

## 学習リソース

### このプロジェクトで使っている技術

#### MediaPipe
- [公式ドキュメント](https://ai.google.dev/edge/mediapipe/solutions/guide)
- [Pose Landmarker タスク](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
- 重要概念: `pose_world_landmarks`（メートル単位の3D座標）vs `pose_landmarks`（画面座標0〜1）

#### FastAPI
- [公式チュートリアル](https://fastapi.tiangolo.com/ja/tutorial/)
- 重要: `Depends()`による依存性注入、`UploadFile`、WebSocket
- 認証は `HTTPBearer` + JWT（`auth.py` 参照）

#### Next.js 16 / React 19
- [Next.js ドキュメント](https://nextjs.org/docs)
- React 19の変更点: `useRef<T | null>(null)` が必要（`useRef<T>(null)` は型エラー）
- Tailwind CSS v4: `@import "tailwindcss"` + `postcss.config.mjs` が必要

#### PyTorch（1D-CNN / ST-GCN）
- [PyTorch チュートリアル](https://pytorch.org/tutorials/)
- 重要: `nn.Conv1d`の入力形状 `(N, C, L)`
- 本プロジェクトの入力: `(N, 3, 30, 17)` = (バッチ, xyz, フレーム, 関節)

#### バイオメカニクス（研究の核心）
- Escamilla et al. 2001「Knee biomechanics of the dynamic squat exercise」→ スクワット膝角度
- Youdas et al. 2010「Muscle Activation During Push-Up and Pull-Up」→ 懸垂筋群
- Contreras et al. 2015「筋断面積と活動強度の関係」→ body_scale補正の根拠

#### WebRTC / WebSocket
- [MDN getUserMedia](https://developer.mozilla.org/ja/docs/Web/API/MediaDevices/getUserMedia)
- [MDN WebSocket](https://developer.mozilla.org/ja/docs/Web/API/WebSocket)
- `CameraAnalyzer.tsx` での実装が参考になる

### 研究関連ドキュメント

| ファイル | 内容 |
|---------|------|
| `docs/研究計画書_v7.md` | 最新版研究計画書（1〜4章・年間計画） |
| `docs/muscle_mapping_review.md` | 筋群マッピングのバイオメカニクスレビュー記録 |
| `docs/deploy.md` | Railway/Vercelデプロイ手順 |
| `README.md` | プロジェクト概要・API一覧・セットアップ |

---

## Git運用メモ

```bash
# 毎回の作業前
cd ~/Desktop/01_Development/laboratory/muscle-analyzer
git pull origin main

# 作業後
git add -A
git commit -m "feat/fix/docs: 変更内容"
git push origin main

# リモートと競合した場合
git pull --rebase origin main
git push origin main

# コンフリクトした場合（リモートを優先）
git checkout --theirs <ファイル>
git add <ファイル>
git rebase --continue
```

---

## MLモデルの学習（ローカル実行）

```bash
cd ~/Desktop/01_Development/laboratory/muscle-analyzer
source .venv/bin/activate

# 1D-CNN学習
cd backend && python src/ml/train.py

# ST-GCN学習
python src/ml/train_stgcn.py

# 学習済みモデルの保存先
# output/best_1dcnn.pt
# output/best_stgcn.pt
```

Apple Silicon (M系) では `device = torch.device("mps")` が使える。  
`train.py` の `DEVICE` を `"mps"` に変更すると GPU 相当の速度で学習できる。
