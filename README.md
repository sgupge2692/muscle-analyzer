# 🏋️ Muscle Analyzer

筋トレ動画の解析による**筋肉動態の可視化とフォーム矯正**DXツール

[![Next.js](https://img.shields.io/badge/Next.js-16.4.3-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-1.1.1-blue)](https://mediapipe.dev/)
[![License](https://img.shields.io/badge/License-Academic-orange)](./backend/EULA_1.pdf)

## 概要

単眼カメラ映像（動画アップロード or リアルタイムカメラ）から骨格を推定し、  
どの筋肉がどれだけ活動しているかを20筋群のヒートマップで可視化します。

### 主な機能

| 機能 | 説明 |
|------|------|
| 🎥 動画アップロード解析 | MP4/MOV（最大200MB）をアップロードしてレップごとに解析 |
| 📹 リアルタイム解析 | WebSocketでカメラ映像をストリーミング解析 |
| 💪 筋肉活動ヒートマップ | 20筋群の活動強度を体表マップで可視化 |
| 🦴 3Dアバタービューア | カプセル人体モデルで任意視点から動きを確認 |
| 📐 フォームチェック | 関節角度と理想範囲を比較してエラー/警告を表示 |
| 👤 体型推定 | 正面写真から肩幅・骨盤幅・骨格比率を推定し精度向上 |
| 🔐 認証 | JWT + bcrypt(cost=12)によるセキュアなユーザー管理 |

### 対応種目（141種目）

スクワット、デッドリフト、ルーマニアンDL、ランジ、プッシュアップ、ベンチプレス、スクワットホールドなど

---

## 技術スタック

### フロントエンド
- **Next.js 16.4.3** + TypeScript + Tailwind CSS v4
- Canvas API（ヒートマップ・3Dアバター描画）
- WebRTC + WebSocket（リアルタイムカメラ解析）
- Vercel（ホスティング）

### バックエンド
- **FastAPI 0.115** + Python 3.12+
- **MediaPipe 1.1.1**（骨格検出・33点3D座標）
- NumPy / pandas / scikit-learn / PyTorch
- bcrypt（パスワードハッシュ化）
- Railway（ホスティング）

### 機械学習
- **1D-CNN**（Conv 3層 32→64→128ch、MLP 512→256）
- **ST-GCN**（5ブロック 64→64→128→128→256、SE-Attention）
- MuscleMapデータセット（学術研究限定・EULA署名済み）

---

## セットアップ

### バックエンド

```bash
cd backend

# Python 3.12+ 推奨（macOS: brew install python@3.13）
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 環境変数
cp .env.example .env
# JWT_SECRET を必ず変更してください
# python3 -c "import secrets; print(secrets.token_hex(32))"

# 起動
uvicorn src.api.main:app --reload --port 8000
```

### フロントエンド

```bash
cd frontend
npm install

# 環境変数
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL にバックエンドURLを設定

npm run dev
```

ブラウザで `http://localhost:3000` を開く

---

## API

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/health` | GET | ヘルスチェック |
| `/analyze` | POST | 動画解析（最大200MB） |
| `/estimate_body` | POST | 体型推定（正面写真） |
| `/ws/stream` | WebSocket | リアルタイムカメラ解析 |
| `/auth/register` | POST | ユーザー登録 |
| `/auth/login` | POST | ログイン（JWT発行） |
| `/auth/me` | GET | 現在のユーザー情報 |

### /analyze パラメータ

```
file:         動画ファイル（multipart/form-data）
exercise:     種目名（例: Squats, Deadlift）
target_angle: 目標膝角度（40〜170、デフォルト110）
frame_skip:   フレームスキップ数（1=全フレーム、2=1/2、デフォルト2）
body_scale:   体格スケール係数（0.5〜2.0、/estimate_bodyから取得）
ml_mode:      ML推論モード（true/false）
```

---

## デプロイ

### Railway（バックエンド）

1. `railway.app` でプロジェクト作成
2. GitHub リポジトリを接続、**Root Directory を `backend` に設定**
3. 環境変数を設定：

```
JWT_SECRET=<32文字以上のランダム文字列>
ENV=production
ALLOWED_ORIGINS=https://your-app.vercel.app
MAX_FILE_SIZE_MB=200
```

### Vercel（フロントエンド）

1. `vercel.com` でプロジェクト作成
2. **Root Directory を `frontend` に設定**
3. 環境変数を設定：

```
NEXT_PUBLIC_API_URL=https://your-app.railway.app
NEXT_PUBLIC_WS_URL=wss://your-app.railway.app
```

---

## ライセンス・利用制限

- フロントエンド・バックエンドのコード：研究・個人利用可
- **MuscleMapデータセット**：学術研究限定（EULAに従い再配布・商用利用禁止）
- 商用フェーズは Free Exercise DB（Unlicense）＋自前収集データで構成

---

## 研究情報

佐賀大学理工学部 中山研究室（卒業研究 2026年度）  
研究テーマ：筋トレ動画の解析による筋肉動態の可視化とフォーム矯正  
研究計画書：[docs/研究計画書_v7.md](./docs/研究計画書_v7.md)
