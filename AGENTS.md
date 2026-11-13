# AGENTS.md — Muscle Analyzer

モノレポ: `backend/`（FastAPI + Python 3.13）と `frontend/`（Next.js 16.4.3 / React 19 / Tailwind v4）。2つの独立アプリで、共通のワークスペース設定はない。デプロイは Railway（Root Directory を `backend` に設定）と Vercel（同 `frontend`）。

## バックエンドの起動

- **venv はリポジトリ直下の `.venv`**（`backend/.venv` ではない）。起動は必ず `backend` ディレクトリで:
  ```bash
  cd backend && ../.venv/bin/uvicorn src.api.main:app --reload --port 8000
  ```
- `backend/.env` が必須（`cp .env.example .env`、`JWT_SECRET` を設定）。`src/api/main.py` 内の手製ローダーが **import より前に** `.env` を読む（`auth.py` が import 時に `JWT_SECRET` を参照するため、import 順を壊さないこと）。
- Docker 開発（推奨・バックエンドのみ）: リポジトリ直下で `docker compose up --build`。`src/` と `data/` は bind mount でホットリロード。
- **PyTorch 学習は Docker の外で実行**（macOS の Docker からは MPS を使えない）: `cd backend && python src/ml/train.py`（ST-GCN は `train_stgcn.py`）。出力は `output/`。

## 依存関係の制約

- `requirements.txt` はピン固定。**scikit-learn 1.9.1 は下げない** — 学習済み `.pkl` とバージョンが違うと推論結果が不正になる（卒論の評価実験もこの版）。
- numpy 2.5 / scipy 1.18 のため **Python 3.12+ 必須**（Dockerfile は python:3.13-slim）。
- Dockerfile の `libegl1` / `libgles2` は MediaPipe に必須（無いと PoseLandmarker 生成時に必ず失敗）。削除しない。

## data/ の扱い

- `data/users.json` がユーザーストア（Supabase 使う場合は `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`。service_role キーを NEXT_PUBLIC_* に出すな）。
- **MuscleMap データセットは学術研究限定（EULA）**。Docker イメージに焼き込んだりレジストリに push しないこと。`data/muscle_mapping.json`（141種目×20筋群）は自前資産。

## テスト・検証

- `backend/tests/` は空。pytest / lint / typecheck の設定は存在しない。
- 検証は実動作で: サーバー起動 → `GET /health`、`ENV=development` なら `/docs` で Swagger 確認。依存の整合は `python src/check_env.py`。

## フロントエンド

- `frontend/AGENTS.md` は `next dev` が自動生成する Next.js 16 のルールブロック。**削除しない**。Next.js 16 の API は学習データと異なるので、`node_modules/next/dist/docs/` の該当ガイドを先に読む。
- React 19: `useRef<T | null>(null)` が必要（`useRef<T>(null)` は型エラー）。
- dev 起動前にポート 3000 を確認: `lsof -ti:3000 | xargs kill -9`。

## 研究計画書の変更

- `docs/研究計画書_*.md` に新しい成功基準・評価項目・研究の軸を追加する場合は、実装前に提案として報告し承認を得る。無断でスコープを拡張しない（詳細は `GUARDRAILS.md`）。

## Git 運用

- main に直接 push。コミットメッセージは日本語で `feat:` / `fix:` / `docs:` 接頭辞。
- 詳細ガイド: `docs/DEVELOPER_GUIDE.md`（起動・学習手順）、`docs/deploy.md`（Railway/Vercel）。
