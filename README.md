# 💪 Muscle Analyzer

> **筋トレ動画における骨格推定と解剖学モデルを用いた筋肉動態可視化システムの開発**

単眼カメラの映像から、どの筋肉が「いつ・どれだけ」収縮・伸展しているかをリアルタイムで推定し、ヒートマップとして可視化する Web アプリ。卒業研究（佐賀大学・中山研 2026〜2027 年度）として実施。

---

## 🎯 プロジェクト概要

### 背景と課題
- 日本のフィットネス市場は約 **5,000 億円**（経産省 2022 年度）に拡大。自宅トレーニーが急増
- ジム利用者の約 **60%** が「正しいフォームがわからない」と回答（日本健康スポーツ連盟 2022 年）
- 既存の姿勢解析ツールは関節角度・フォーム分類どまり。**「どの筋肉が使われているか」の可視化に至っていない**
- パーソナルトレーナー指導は 1 回 5,000〜15,000 円のコスト障壁

### 提案手法
- MediaPipe Pose Landmarker で 33 点骨格を 3D 推定
- 解剖学ルールベース ＋ 時系列深層学習（1D-CNN / ST-GCN）のハイブリッドで筋活動を推定
- Next.js フロントエンド上に **筋肉ヒートマップ** としてリアルタイム可視化

### 新規性の核心
1. **解釈可能な可視化** — 解剖学モデルに基づき「どの筋肉・なぜ」を提示
2. **スマートフォン 1 台完結** — 専用センサ・実験環境不要
3. **筋トレ種目特化** — スクワット・デッドリフトから開始し種目ライブラリを拡張

### 成功判定基準
| 指標 | 目標値 |
|------|--------|
| 筋肉活動分類 F1 micro（スクワット・デッドリフト） | **0.93 以上** |
| 専門家（理学療法士・トレーナー）による妥当性評価 | **5 段階で 4.0 以上** |

---

## 🏗️ システム構成

```
[スマートフォン / ブラウザ]
       │ 動画アップロード
       ▼
[Next.js フロントエンド] ──── REST API ────▶ [FastAPI バックエンド]
  - Canvas API でヒートマップ描画                │
  - Tailwind CSS / TypeScript              ├─ MediaPipe Pose Landmarker
                                           ├─ 解剖学ルールベースモジュール
                                           ├─ 1D-CNN / ST-GCN モデル
                                           └─ Supabase（ユーザ・履歴管理）
```

---

## 🗂️ ディレクトリ構成

```
muscle-analyzer/
├── frontend/                   # Next.js + TypeScript + Tailwind
├── backend/
│   ├── src/
│   │   ├── pose/               # MediaPipe 骨格推定
│   │   │   ├── detect_pose.py
│   │   │   └── extract_landmarks.py
│   │   ├── anatomy/            # 解剖学モデル・筋活動推定
│   │   │   ├── knee_angle.py
│   │   │   ├── muscle_activation.py
│   │   │   ├── angle_features.py
│   │   │   ├── rep_detector.py
│   │   │   ├── squat_analysis.py
│   │   │   ├── musclemap_features.py
│   │   │   └── ml_predictor.py
│   │   ├── ml/                 # 機械学習モデル
│   │   │   ├── dataset.py
│   │   │   ├── model.py
│   │   │   └── train.py
│   │   ├── visualization/      # ヒートマップ描画
│   │   │   └── heatmap_renderer.py
│   │   └── api/                # FastAPI エンドポイント
│   │       └── main.py
│   ├── data/
│   │   ├── muscle_mapping.json # 137 種目 × 20 筋群 独自アノテーション
│   │   └── processed/          # 中間出力（可視化・特徴量）
│   ├── notebooks/              # 探索・検証用 Jupyter
│   ├── requirements.txt
│   └── Dockerfile
├── docs/
│   └── 研究計画書_v5.md
└── README.md
```

---

## 🛠️ 技術スタック

| レイヤ | 技術 |
|--------|------|
| フロントエンド | Next.js / TypeScript / Tailwind CSS / Canvas API |
| バックエンド | Python 3.11 / FastAPI / OpenCV / MediaPipe |
| 機械学習 | scikit-learn → PyTorch（1D-CNN / ST-GCN） |
| データ | NumPy / pandas / Jupyter |
| インフラ | Docker / Vercel / Railway / Supabase |
| データセット | MuscleMap（学術研究限定・EULA 署名済み）/ Free Exercise DB |

---

## 🗺️ ロードマップ

### Phase 0 — 基盤構築（2026 年 10 月 ✅ 完了）
- [x] MediaPipe 骨格検出パイプライン
- [x] 関節角度算出（膝角度・レップ検出）
- [x] MuscleMap データセット統合・特徴量抽出
- [x] 137 種目 × 20 筋群 独自マッピング JSON 作成

### Phase 1 — ルールベース MVP（2026 年 11〜12 月）
- [ ] 解剖学モデル（スクワット主要筋群）のルールベース推定
- [ ] ヒートマップ可視化 HTML 出力
- [ ] 研究計画書完成・発表（12 月）

### Phase 2 — ML モデル統合（2027 年 1〜3 月）
- [ ] scikit-learn による分類モデル実装
- [ ] MuscleMap 特徴量との統合評価
- [ ] FastAPI REST API 化

### Phase 3 — Web アプリ MVP（2027 年 4〜6 月）
- [ ] Next.js フロントエンド実装
- [ ] Supabase 認証・履歴管理
- [ ] デプロイ（Vercel + Railway）

### Phase 4 — 精度向上・論文（2027 年 7〜1 月）
- [ ] 1D-CNN / ST-GCN 実装・評価実験
- [ ] 専門家評価・ユーザスタディ
- [ ] 卒業論文執筆 → 2 月発表

---

## ⚠️ ライセンス・データ利用上の注意

- **MuscleMap データセット**：学術研究限定（EULA 署名済み 2026-10-11）。再配布・商用利用・公開環境への配置は不可。`data/raw/musclemap_benchmark/` は `.gitignore` 済み
- **製品フェーズ**：Free Exercise DB（Unlicense）＋ 自前収集データで構成予定
- `data/muscle_mapping.json`（独自アノテーション）は商用 OK の自前資産

---

## 🚀 セットアップ

```bash
# バックエンド
cd backend
pip install -r requirements.txt

# 環境変数
cp .env.example .env

# API 起動
uvicorn src.api.main:app --reload
```

---

## 📄 参考文献

- Bazarevsky et al. (2020). BlazePose. CVPR Workshop.
- Cao et al. (2017). OpenPose. CVPR.
- Chiquier & Vondrick (2023). Muscles in Action. ICCV.
- Appiah (2024). Mobile-Phone Pose Estimation for Gym-Exercise Form Correction. VISIGRAPP.
- Helmy et al. (2024). PoseRight. MIUCC.
- Zhu et al. (2025). 3D Human Pose Estimation with Muscles. NeurIPS.
- Chen et al. (2026). Pose2Muscle. arXiv:2609.18336.
