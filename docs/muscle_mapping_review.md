# muscle_mapping.json バイオメカニクスレビュー

**レビュー日**: 2026-10-24  
**対象ファイル**: `backend/data/muscle_mapping.json`  
**修正前種目数**: 137 → **修正後**: 141

---

## 発見した問題点と対応

### 🔴 欠落（研究スコープに直結）

| 問題 | 詳細 | 対応 |
|------|------|------|
| `Squats`（通常スクワット）が未収録 | Squat_Hold等の派生のみで、研究主要種目のベーススクワットがなかった | **追加**: `[11,12,13,14,15,17]` |
| `Deadlift`（バーベル）が未収録 | 研究テーマ「スクワット・デッドリフト」のデッドリフト本体がなかった | **追加**: `[6,7,11,12,17]` |
| `Romanian_Deadlift` が未収録 | ハムストリング強調のRDLはデッドリフト評価に重要 | **追加**: `[11,12,17]` |
| `Bench_Press` が未収録 | 上半身プッシュ系の代表種目として追加 | **追加**: `[1,2,4]` |

### 🟡 筋群の抜け漏れ（バイオメカニクス的修正）

| 種目 | 問題 | 修正内容 |
|------|------|---------|
| `Squat_Hold` | Calves(14)なし。スクワット静止保持では下腿三頭筋が等尺性収縮する | Calves(14)追加 |
| `Squat_Hold_Side_Bends` | 同上 | Calves(14)追加 |
| `squat_hold_punches` | 同上 | Calves(14)追加 |
| `Lateral_Squats` | 横方向スクワットでも下腿三頭筋の安定作用あり | Calves(14)追加 |
| `Diamond_Pushups` | ナローグリップでは前鋸筋（Upper_Back相当）も関与 | Upper_Back(6)追加 |
| `Jumping_Lunges` | ジャンプ動作で腸腰筋（Inner_Thigh代替）が強く関与 | Inner_Thigh(15)追加 |
| `Lunge_Step-Ups` | ステップアップ動作で股関節屈曲筋が働く | Inner_Thigh(15)追加 |

### 🔵 設計方針の確認事項（変更なし）

| 項目 | 判断 |
|------|------|
| `Upper_Abs` / `Lower_Abs` の分割 | 解剖学的には腹直筋は一体だが、EMG研究では上部・下部で活性差があり、この粒度は研究上許容範囲 |
| `Neck_Head(0)` が全種目で未使用 | データセット（MuscleMap）にネック系種目が含まれないため。`Neck_Head_reserved` に名称変更して明示 |
| `Latissimus(7)` が4件のみ | プルダウン系種目がデータセットに少ないためやむなし。将来の種目追加時に拡充予定 |

---

## 修正後の主要種目マッピング（バイオメカニクス根拠付き）

### スクワット系
```
Squats:             [Lower_Back, Hamstring, Quadriceps, Calves, Inner_Thigh, Gluteus]
                    → 主動作筋：大腿四頭筋・大臀筋、協働筋：ハムスト・内転筋群、安定：脊柱起立筋・下腿三頭筋
Squat_Hold:         [Lower_Back, Hamstring, Quadriceps, Calves, Inner_Thigh, Gluteus]  ← Calves追加
Jump_Squats:        [Lower_Abs, Lower_Back, Hamstring, Quadriceps, Calves, Gluteus, Feet_Ankles]
```

### デッドリフト系
```
Deadlift:           [Upper_Back, Latissimus, Lower_Back, Hamstring, Gluteus]
                    → 主動作筋：大臀筋・ハムスト、協働筋：脊柱起立筋・広背筋・僧帽筋
Romanian_Deadlift:  [Lower_Back, Hamstring, Gluteus]
                    → ヒップヒンジ特化。ハムスト最大伸張
Single_leg_dead_lifts: [Lower_Back, Hamstring, Gluteus]  ← 既存（変更なし）
```

### プッシュアップ系
```
Push_ups:           [Chest, Shoulder, Triceps, Upper_Back, Upper_Abs, Lower_Abs, Lower_Back]
Diamond_Pushups:    [Chest, Shoulder, Triceps, Upper_Back, Upper_Abs, Lower_Abs, Lower_Back]  ← Upper_Back追加
Pike_push-up:       [Chest, Shoulder, Triceps, Upper_Back, Upper_Abs, Lower_Abs, Lower_Back]
```

---

## 今後の課題（将来対応）

1. **Kunyuさんからの正式ラベルとの一致率検証**  
   → 正式ラベル受領後、本マッピングとの一致率を計算し論文の評価指標に組み込む

2. **BenchPress / Overhead_Press 系の拡充**  
   → 上半身プッシュ系の評価に必要

3. **EMG先行研究との定量的照合**  
   → 各種目の筋活動比率（%MVC）を文献から収集し、ヒートマップの輝度値設計に反映する

4. **Neck_Head(0) の活用**  
   → 首・僧帽筋上部系種目（シュラッグ等）を追加する場合に使用

---

## 参考文献（バイオメカニクス根拠）

- Escamilla, R.F. (2001). Knee biomechanics of the dynamic squat exercise. *Medicine & Science in Sports & Exercise*, 33(1), 127-141.
- Contreras, B., et al. (2015). A biomechanical analysis of the Romanian, 45-degree, and lying prone hip extension exercises. *Strength & Conditioning Journal*.
- Lehman, G.J. (2005). The influence of grip width and forearm pronation/supination on upper-body myoelectric activity during the flat bench press. *Journal of Strength and Conditioning Research*, 19(3), 587-591.
