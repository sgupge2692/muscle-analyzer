# track-b-experimental（トラックB・評価対象外）

このブランチは，トラックA（文献較正パイプライン・卒論の評価対象）から意図的に分離した実験コードを退避・保持するためのブランチである．

## 位置づけ

- **本ブランチのコードは卒論の評価対象外である**．トラックAの成功基準（F1 micro ≥ 0.93，文献較正 r）には一切寄与せず，卒論の実験・考察に含めないこと．
- 評価方法・成功基準を拡張する内容を含むため，GUARDRAILS.md の「研究計画書のスコープ変更」に抵触するコードはここにのみ存在する．
- main への**マージは原則禁止**．マージ条件：**卒論提出後 かつ トラックA完了後**．マージする場合は研究計画書の変更手続き（実装前の提案・承認）を先に行うこと．

## 退避対象ファイルと元コミット

| ファイル | 元コミット | 内容 |
|---|---|---|
| `backend/src/anatomy/deviation_diagnosis.py` | `6ae3bf3` | 活動曲線逸脱診断（課題C）＋エビデンスレベル表示 |
| `backend/src/anatomy/velocity_metrics.py` | `6ae3bf3` | レップ角速度・velocity loss・フォーム妥当性フィルタ・二点法1RM推定（課題D） |
| `backend/src/ml/model_evo.py` | `a60ebd5`（初出 `93bba09`） | 強化版1D-CNN（MuscleClassifier1DCNNEvo・未学習） |
| `frontend/src/components/DiagnosisCard.tsx` | `d7a3a59` | 「診断・疲労」タブUI（逸脱診断・エビデンスレベル・velocity loss 表示） |
| `frontend/src/components/AvatarViewer3DR3F.tsx` | `a12017d` | React Three Fiber メッシュ人型3Dビューア（トラックBフェーズ1） |
| `backend/scripts/test_deviation_diagnosis.py` | `9fe857e`（初出 `6ae3bf3`） | 逸脱診断・velocity metrics の最小単体テスト |

## 前提

- main 側では `evidence_levels`（文献較正の信頼度レベル）のみ `backend/src/anatomy/evidence_level.py` として残存する（文献較正パイプラインの正式な成果物のため）．本ブランチの `deviation_diagnosis.py` はその原型（evidence_level 含む）を保持する．
- ブランチ作成時点の main: `111e3a2`（2026年11月14日）
