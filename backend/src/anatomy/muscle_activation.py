import pandas as pd
import numpy as np
import json
# 筋群ごとの「関連関節」と「角度が小さいほど収縮か大きいほど収縮か」の定義
MUSCLE_JOINT_MAP = {
    # ── 下半身 ──────────────────────────────────────────────────
    # 大腿四頭筋：膝屈曲（小さい角度）で伸張・収縮負荷が高い
    "Quadriceps":  [("right_knee",    "small"), ("left_knee",    "small")],
    # ハムストリング：股関節屈曲（小さい角度）で伸張。左右両側を使う
    "Hamstring":   [("right_hip",     "small"), ("left_hip",     "small")],
    # 大臀筋：股関節屈曲（小さい角度）で伸張→収縮力が高い
    "Gluteus":     [("right_hip",     "small"), ("left_hip",     "small")],
    # 脊柱起立筋：体幹前傾（大きい角度）で等尺性収縮
    "Lower_Back":  [("spine_tilt",    "large")],
    # 下腿三頭筋：足首角度が小さいほど伸張
    "Calves":      [("right_ankle",   "small"), ("left_ankle",   "small")],
    # 内転筋：股関節屈曲と膝内側化で活動
    "Inner_Thigh": [("knee_asymmetry","large")],
    "Outer_Thigh": [("knee_asymmetry","small")],
    # ── 上半身 Push ─────────────────────────────────────────────
    "Chest":       [("right_elbow",   "small"), ("left_elbow",   "small")],
    "Shoulder":    [("right_shoulder","small"), ("left_shoulder","small")],
    # 上腕三頭筋：肘伸展（大きい角度）で収縮
    "Triceps":     [("right_elbow",   "large"), ("left_elbow",   "large")],
    # ── 上半身 Pull ─────────────────────────────────────────────
    # 上腕二頭筋：肘屈曲（小さい角度）で収縮
    "Biceps":      [("right_elbow",   "small"), ("left_elbow",   "small")],
    "Upper_Back":  [("right_shoulder","large"), ("left_shoulder","large")],
    "Latissimus":  [("right_shoulder","large"), ("left_shoulder","large")],
    # ── 体幹 ────────────────────────────────────────────────────
    "Obliques":    [("spine_tilt",    "large"), ("hip_asymmetry","large")],
    "Upper_Abs":   [("right_hip",     "small"), ("left_hip",     "small")],
    "Lower_Abs":   [("right_hip",     "small"), ("left_hip",     "small")],
    # ── その他 ──────────────────────────────────────────────────
    "Forearms":    [("right_elbow",   "small"), ("left_elbow",   "small")],
    "Neck_Head_reserved": [("spine_tilt", "large")],
    "Neck_Head":   [("spine_tilt",    "large")],
    "Feet_Ankles": [("right_ankle",   "small"), ("left_ankle",   "small")],
    "Wrists":      [("right_elbow",   "small"), ("left_elbow",   "small")],
}

# 種目ごとの筋肉活動基準重み（バイオメカニクス先行研究に基づく）
# 値は相対的な活動強度の比率（合計1.0になるよう正規化して使う）
# 参考: Escamilla 2001, Contreras 2015, Saeterbakken 2013
EXERCISE_BASE_WEIGHTS: dict[str, dict[str, float]] = {
    "Squat_Hold": {
        "Quadriceps": 0.35, "Gluteus":    0.25, "Hamstring":  0.18,
        "Lower_Back": 0.10, "Calves":     0.07, "Inner_Thigh":0.05,
    },
    "Jump_Squats": {
        "Quadriceps": 0.38, "Gluteus":    0.22, "Hamstring":  0.15,
        "Lower_Back": 0.08, "Calves":     0.12, "Inner_Thigh":0.05,
    },
    "Lateral_Squats": {
        "Quadriceps": 0.30, "Gluteus":    0.25, "Hamstring":  0.18,
        "Lower_Back": 0.08, "Calves":     0.07,
        "Inner_Thigh":0.07, "Outer_Thigh":0.05,
    },
    "Forward_Lunges": {
        "Quadriceps": 0.38, "Gluteus":    0.25, "Hamstring":  0.20,
        "Calves":     0.10, "Inner_Thigh":0.07,
    },
    "Diamond_Pushups": {
        "Chest":      0.30, "Triceps":    0.45, "Shoulder":   0.15,
        "Lower_Back": 0.10,
    },
    "Pull_ups": {
        "Latissimus": 0.40, "Biceps":     0.25, "Upper_Back": 0.20,
        "Shoulder":   0.10, "Forearms":   0.05,
    },
    "Squats": {
        "Quadriceps": 0.35,
        "Gluteus":    0.25,
        "Hamstring":  0.18,
        "Lower_Back": 0.10,
        "Calves":     0.07,
        "Inner_Thigh":0.05,
    },
    "Deadlift": {
        "Gluteus":    0.30,
        "Hamstring":  0.28,
        "Lower_Back": 0.22,
        "Latissimus": 0.10,
        "Upper_Back": 0.10,
    },
    "Romanian_Deadlift": {
        "Hamstring":  0.40,
        "Gluteus":    0.35,
        "Lower_Back": 0.25,
    },
    "Lunges": {
        "Quadriceps": 0.35,
        "Gluteus":    0.28,
        "Hamstring":  0.20,
        "Calves":     0.10,
        "Inner_Thigh":0.07,
    },
    "Push_ups": {
        "Chest":      0.40,
        "Triceps":    0.30,
        "Shoulder":   0.20,
        "Lower_Back": 0.10,
    },
    "Bench_Press": {
        "Chest":      0.45,
        "Triceps":    0.30,
        "Shoulder":   0.25,
    },
}

def estimate_activation(angle_features: pd.DataFrame,
                        active_muscles: list,
                        exercise: str = "",
                        window: int = 15,
                        body_scale: float = 1.0) -> pd.DataFrame:
    """
    筋肉活動強度を推定。
    
    2段階アプローチ:
    1. 種目の基準重みがあればそれをベースに使う（バイオメカニクス的に正確）
    2. ない場合は関節角度の変化量（velocity）で動的に推定する

    active_muscles: muscle_mapping.jsonから取得した筋群名リスト
    exercise: 種目名（基準重みの参照に使用）
    """
    n_frames = len(angle_features)
    activations = {}

    # --- ステップ1: 基準重みが定義されている種目はそれを使う ---
    base_weights = EXERCISE_BASE_WEIGHTS.get(exercise, {})
    
    if base_weights:
        # 対象筋群のうち基準重みがあるものを抽出
        target_weights = {m: base_weights[m] for m in active_muscles if m in base_weights}
        
        if target_weights:
            # 基準重みを正規化（合計1.0）
            total = sum(target_weights.values())
            normalized_weights = {m: w / total for m, w in target_weights.items()}

            # body_scale補正：体格が大きい（body_scale>1）ほど
            # 大筋群（Gluteus/Quadriceps/Latissimus）への負荷が増加する傾向
            # 参考: Bret Contreras 2015「筋断面積と活動強度の関係」
            LARGE_MUSCLES = {"Gluteus", "Quadriceps", "Latissimus", "Hamstring"}
            if body_scale != 1.0:
                adjusted = {}
                for m, w in normalized_weights.items():
                    if m in LARGE_MUSCLES:
                        adjusted[m] = w * (1.0 + (body_scale - 1.0) * 0.3)
                    else:
                        adjusted[m] = w * (1.0 - (body_scale - 1.0) * 0.1)
                total_adj = sum(adjusted.values())
                normalized_weights = {m: w / total_adj for m, w in adjusted.items()}
            
            for muscle, base_w in normalized_weights.items():
                # 動的な変調：関節角度の変化率でベース重みを±20%変調
                dynamic_mod = _compute_dynamic_modifier(angle_features, muscle, window)
                # ベース重み × 動的変調（0.8〜1.2の範囲）
                raw = base_w * (0.8 + 0.4 * dynamic_mod)
                activations[muscle] = pd.Series(raw, index=angle_features.index)
            
            # 基準重みにない筋肉は動的推定で補完
            remaining = [m for m in active_muscles if m not in target_weights]
            for muscle in remaining:
                dynamic_mod = _compute_dynamic_modifier(angle_features, muscle, window)
                # 残りの筋肉は小さいスコアで追加（最大10%）
                activations[muscle] = pd.Series(0.05 * dynamic_mod, index=angle_features.index)
            
            return pd.DataFrame(activations)

    # --- ステップ2: フォールバック（旧来の関節角度ベース推定）---
    for muscle in active_muscles:
        if muscle not in MUSCLE_JOINT_MAP:
            continue
        joint_scores = []
        for joint_col, direction in MUSCLE_JOINT_MAP[muscle]:
            if joint_col not in angle_features.columns:
                continue
            series = angle_features[joint_col].copy().ffill().bfill()
            if 'asymmetry' in joint_col:
                series = series.abs()
                normalized = (series / 15.0).clip(0.0, 1.0)
            else:
                mn, mx = series.min(), series.max()
                if mx - mn < 1e-6:
                    normalized = pd.Series(0.5, index=series.index)
                else:
                    normalized = (series - mn) / (mx - mn)
            score = (1.0 - normalized) if direction == "small" else normalized
            vel_col = f'{joint_col}_vel'
            if vel_col in angle_features.columns:
                vel = angle_features[vel_col].abs().ffill().bfill()
                vel_norm = vel / (vel.max() + 1e-8)
                score = score * 0.8 + vel_norm * 0.2
            joint_scores.append(score)
        if joint_scores:
            activations[muscle] = pd.concat(joint_scores, axis=1).mean(axis=1)

    return pd.DataFrame(activations)


def _compute_dynamic_modifier(features: pd.DataFrame, muscle: str, window: int) -> pd.Series:
    """
    関節角度の変化速度から動的な活動変調係数（0〜1）を計算
    """
    if muscle not in MUSCLE_JOINT_MAP:
        return pd.Series(0.5, index=features.index)
    
    scores = []
    for joint_col, _ in MUSCLE_JOINT_MAP[muscle]:
        vel_col = f'{joint_col}_vel'
        if vel_col in features.columns:
            vel = features[vel_col].abs().ffill().bfill()
            vel_norm = (vel / (vel.max() + 1e-8)).rolling(window, center=True, min_periods=1).mean()
            scores.append(vel_norm)
    
    if not scores:
        return pd.Series(0.5, index=features.index)
    return pd.concat(scores, axis=1).mean(axis=1).clip(0, 1)


def visualize_activation(activations: pd.DataFrame,
                         exercise: str,
                         output_path: str):
    """筋肉活動強度を時系列グラフで可視化（CLI用）"""
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.rcParams['font.family'] = 'Hiragino Sans'
    fig, ax = plt.subplots(figsize=(14, 6))

    colors = plt.cm.tab20(np.linspace(0, 1, len(activations.columns)))
    for col, color in zip(activations.columns, colors):
        ax.plot(activations.index, activations[col],
                label=col, linewidth=1.5, color=color)

    ax.set_xlabel('フレーム')
    ax.set_ylabel('活動強度（0〜1）')
    ax.set_title(f'{exercise}筋肉活動強度推定')
    ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"保存: {output_path}")


if __name__ == "__main__":
    import csv, pathlib, sys

    FEATURES_CSV = "data/processed/angle_features.csv"
    MAPPING_JSON = "data/muscle_mapping.json"
    OUTPUT_IMG   = "data/processed/muscle_activation.png"
    OUTPUT_JSON  = "data/processed/muscle_activation.json"
    EXERCISE     = "Squat_Hold"

    print("特徴量を読み込み中...")
    features = pd.read_csv(FEATURES_CSV, index_col='frame')

    print("筋群マッピングを読み込み中...")
    with open(MAPPING_JSON) as f:
        mapping = json.load(f)

    muscle_ids     = mapping['exercise_muscle_mapping'].get(EXERCISE, [])
    muscle_groups  = mapping['muscle_groups']
    active_muscles = [muscle_groups[str(i)] for i in muscle_ids]

    print(f"\n種目: {EXERCISE}")
    print(f"対象筋群: {active_muscles}")

    print("\n筋肉活動強度を推定中...")
    activations = estimate_activation(features, active_muscles)

    print("\n=== 平均活動強度 ===")
    for col in activations.columns:
        print(f"  {col:15s}: {activations[col].mean():.3f}")

    visualize_activation(activations, EXERCISE, OUTPUT_IMG)

    # レップ区間を読み込む
    REPS_CSV = "data/processed/reps.csv"
    reps = []
    if pathlib.Path(REPS_CSV).exists():
        with open(REPS_CSV) as f:
            for row in csv.DictReader(f):
                reps.append((int(row["start_frame"]), int(row["end_frame"])))

    rep_data = {}
    if reps:
        for i, (start, end) in enumerate(reps, 1):
            mask = (activations.index >= start) & (activations.index <= end)
            sl   = activations[mask]
            rep_data[f"rep_{i}"] = {
                col: round(float(sl[col].mean()), 4)
                for col in sl.columns
            }
            print(f"\n=== Rep{i} (frame {start}~{end}) ===")
            for col, val in rep_data[f"rep_{i}"].items():
                bar = chr(9608) * int(val * 20)
                print(f"  {col:15s}: {val:.3f} {bar}")
    else:
        rep_data["rep_1"] = {
            col: round(float(activations[col].mean()), 4)
            for col in activations.columns
        }
        print("reps.csv なし -> 全体平均を rep_1 として保存")

    pathlib.Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(rep_data, f, indent=2, ensure_ascii=False)
    print(f"\n保存: {OUTPUT_JSON}")
