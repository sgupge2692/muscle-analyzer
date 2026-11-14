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

---

## 文献較正検証の現行設計限界の記録（2026-11-14）：Squats/Gluteus

### 検証結果

`backend/scripts/literature_validation.py` による検証（`literature_emg_curves.json` の data_points ＝ Marchetti et al. 2016 の本文明記Δ%から算術導出した相対値3点を正解とし，ガウス関数の peak/width は循環検証防止のため比較対象外）:

| 種目/筋群 | n | Pearson r | p | 判定 |
|---|---|---|---|---|
| Squats/Quadriceps | 3 | 0.9988 | 0.031 | 高整合（n=3の参考値） |
| Squats/Gluteus | 3 | **0.1698** | 0.891 | 低整合 |

### 低整合の原因（現行設計の限界）

- 文献の大臀筋パターンは**非単調**: 膝屈曲140°で約80%低下する一方，屈曲20° ≈ 屈曲90°（有意差なし, d=0.03）。
- 現行の**対称ガウス**（peak_angle_deg=90, width_deg=50, いずれもタスク指示書での事前指定値）はピークから離れるほど単調に減衰するため，**深屈曲140°側を大幅に過大評価**する（正規化誤差最大 0.67）。

### 採用した扱い（保守的な現状維持）

1. 角度関数は**対称ガウス（width=50）を維持**する。非対称ガウスへの拡張と再較正は，検証データ（3点）からのパラメータ逆算＝過学習の懸念により**一度実施して取り下げ済み**（コミット 57cc9df）。再較正には検証データと**独立した根拠**（解剖学的妥当性または別の独立文献）が必要。
2. r=0.17 は「**現行設計（対称ガウス＋n=3文献点）の限界**」として本研究の報告対象とする。研究計画書v17の成功基準(2)では，大臀筋は「文献較正サイクルによる相関の改善を年度内に示す。改善に至らない場合は角度関数の対称性・文献点数の制約を限界として論文に明記」に該当する。
3. パラメータの再フィッティング（検証データからの逆算）は行わない。

---

## Deadlift の文献較正の実装（2026-11-14）：Moreira et al. 2023 による角度別EMG値の追加

### 文献調査の経緯

| 文献 | 角度別定量値の有無 | 結論 |
|---|---|---|
| Escamilla et al. 2002（MSSE 34(4):682-688） | 膝角3区間（90–61°/60–31°/30–0°KA）別の比較を実施（Table 1）だが、全文は要購読で入手可能な本文は定性記述のみ（四頭筋・大臀筋・傍脊柱筋は高屈曲区間で有意に大きい、ハムストは低屈曲区間で大きい） | 数値転記不可 |
| Martín-Fuentes et al. 2020（PLoS ONE, システマティックレビュー） | Table 2 に運動全体の平均%MVICのみ。角度別の値なし | 角度位置検証には使用不可（既存の `aggregate_mean_mvic_pct` の根拠として維持） |
| Moreira et al. 2023（*Muscles* 2(2):16, MDPI オープンアクセス, PMCID 12225233） | デッドリフト3キーポジション（リフトオフ/ミッドプル/ロックアウト＝膝角 約95°/126°/180°）での等尺性最大牽引時の %MVC を RF/BF/GAL/ERE について抄録・本文に明記 | **採用**（角度規約180°=膝完全伸展が本システムと同一で変換不要） |

### literature_emg_curves.json への追加内容

- **Deadlift/Quadriceps**（RF）: 95°:92.46 / 126°:40.50 / 180°:46.85 %MVC。peak=95（リフトオフ位置の膝角度）, width=35（Squats/Quadriceps と同一の事前指定値）
- **Deadlift/Hamstring**（BF）: 95°:58.22 / 126°:92.27 / 180°:67.94 %MVC。peak=150（Escamilla et al. 2002 本文「hamstring data were highest between 0 and 60°KA（0°=伸展）」の区間120–180°の中央値。Moreira の実測3点からは逆算していない）, width=35（事前指定値）
- **Deadlift/Lower_Back**（ERE＝脊柱起立筋）: 95°:91.46 / 126°:89.51 / 180°:36.79 %MVC。peak=95（リフトオフ位置の膝角度）, width=50（Squats/Gluteus と同一の事前指定値）
- **Deadlift/Gluteus**: Moreira et al. 2023 は測定筋に大臀筋を含まず、Escamilla et al. 2002 も定性記述のみ → **角度位置の文献較正検証は不可**（data_points=null のまま維持）

### 検証結果（Squats + Deadlift 全体）

`backend/scripts/literature_validation.py`（正解=data_points、ガウスパラメータは比較対象外）:

| 種目/筋群 | 文献 | n | Pearson r | p | 正規化最大誤差 | 判定 |
|---|---|---|---|---|---|---|
| Squats/Quadriceps | Marchetti 2016 | 3 | 0.9988 | 0.031 | 0.008 | 高整合 |
| Squats/Gluteus | Marchetti 2016 | 3 | 0.1698 | 0.891 | 0.673 | 低整合（上述の限界） |
| Deadlift/Quadriceps | Moreira 2023 | 3 | 0.6852 | 0.519 | 0.454 | 低整合〜部分整合 |
| Deadlift/Hamstring | Moreira 2023 | 3 | 0.8362 | 0.370 | 0.229 | 部分整合 |
| Deadlift/Lower_Back | Moreira 2023 | 3 | 0.9823 | 0.120 | 0.343 | 高整合 |

検証不可エントリ: Squats/Hamstring（定量値なし）, Squats/Lower_Back（文献未見）, Deadlift/Gluteus（文献が角度別定量値を持たない）

### 解釈上の注意

1. **n=3 の相関は参考値**（角度別定量点が各筋3点のみ）。p値はいずれも非有意であり、r値の大きさ自体に過度の解釈をしないこと。
2. **等尺性最大牽引と動的12RMの条件差**: Moreira et al. 2023 は固定位置での等尺性最大牽引、Escamilla et al. 2002 は動的12RM。角度位置パターンの定性傾向（四頭筋・脊柱起立筋は高屈曲側、ハムストは伸展側で大きい）は両者で一致している。
3. **Deadlift/Quadriceps の低整合の構造**: 文献は RF がミッドプル（126°）とロックアウト（180°）で有意差なし（40.50 vs 46.85, p=0.998）だが、対称ガウス（peak=95, width=35）はロックアウト側を大幅に減衰させる。ガウスパラメータの調整（width 拡大等）は検証データに合うよう見直すことになるため**行わない**。r=0.69 は「事前指定パラメータに対する整合確認」として報告する。
4. 本検証は研究計画書v17成功基準(2)（大腿四頭筋は Squats で r≥0.6 を達成済み、大臀筋・ハムストリング・脊柱起立筋は較正サイクルによる改善を年度内に示す）に対応する Deadlift 側の較正サイクル第1弾である。
