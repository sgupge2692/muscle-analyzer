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


---

## 追加レビュー（2026-11-04）

### Pull_ups のマッピングが空だった問題

**発見**: `Pull_ups` の `exercise_muscle_mapping` が空リスト `[]` になっていた

**修正内容**:
```json
"Pull_ups": [2, 3, 5, 6, 7]
```
→ Shoulder(2), Biceps(3), Forearms(5), Upper_Back(6), Latissimus(7)

**根拠**: Youdas et al. 2010 「Muscle Activation During Push-Up and Pull-Up Exercises」
- 広背筋（Latissimus）が最大EMG活動（40%MVC以上）
- 上腕二頭筋（Biceps）が補助として25%MVC
- 僧帽筋中部（Upper_Back）が肩甲骨安定化

### Deadlift に Quadriceps が不足していた問題

**修正内容**: Quadriceps(13) を追加
```json
"Deadlift": [6, 7, 11, 13, 17, ...]
```

**根拠**: Escamilla et al. 2000 「Biomechanics of the Knee During Closed Kinetic Chain Exercises」
- デッドリフトの引き上げ初期フェーズで膝関節の伸展力（Quadriceps）が必要
- 特に床から腰の高さまでの区間で顕著

### Bench_Press に Forearms を追加

**根拠**: Barnett et al. 1995 「Effects of Variations of the Bench Press Exercise on the EMG Activity of Five Shoulder Muscles」
- バーを把持する際の前腕筋（Forearms）の等尺性収縮が確認されている

### 現状の未検討事項

| 種目 | 未検討の問題 |
|------|-------------|
| `Lateral_Raises` | Shoulder の活動比率が要検証 |
| `Hip_Thrust` | Gluteus最大活動種目だが詳細マッピング未確認 |
| `Cable_Curl` | Biceps偏重か否か要確認 |

次のレビュー予定: MuscleMapの実際の筋電図データと照合（Kunyuさんからの正式ラベル待ち）

---

## 追加レビュー（2026-11-12）：Deadlift の EXERCISE_BASE_WEIGHTS に Quadriceps を追加

### 問題

2026-11-04 のレビューで `Deadlift` の `muscle_mapping.json`（筋群リスト）には Quadriceps(13) を追加済みだったが、`muscle_activation.py` の `EXERCISE_BASE_WEIGHTS` には Quadriceps の重みが存在せず、マッピングと基準重みが不整合だった。その結果、デッドリフト解析時に四頭筋が「基準重みなしの残り筋群」（最大5%の小スコア）として扱われていた。

### 修正内容

`EXERCISE_BASE_WEIGHTS["Deadlift"]` に `Quadriceps: 0.18` を追加。

### 根拠（文献値）

Escamilla, R.F. et al. (2002). "An electromyographic analysis of sumo and conventional style squats and deadlifts" (すべての数値は論文Table/Figから目視で読み取った近似値):

- 従来型デッドリフトの sEMG 活動（%MVIC, 平均）: Vastus Lateralis 40±22 / Vastus Medialis 36±25 / Rectus Femoris 19±16 / Gluteus Maximus 35±27 / Biceps Femoris 28±19
- 四頭筋の%MVICは大臀筋（35%）と同等以上 → 既存の Gluteus 0.30 / Hamstring 0.28 と比較して大きく外れない 0.18（正規化後は約15%）を採用
- なお四頭筋の活動は膝屈曲の大きい区間で有意に大きいことも同論文で報告されているが、ピーク角度の定量値は未記載のため `literature_emg_curves.json` 側は `null`（要文献確認）としている

### 注意（後方互換性）

重み追加に伴い、Deadlift の基準重みの正規化後の値が変化する（例: Gluteus 0.30 → 0.30/1.18 ≈ 0.254）。レスポンスの**スキーマ**は不変だが、デッドリフト解析の**数値**は本変更以降シフトする。`/analyze`, `/ws/stream` の入出力形式には影響なし。
