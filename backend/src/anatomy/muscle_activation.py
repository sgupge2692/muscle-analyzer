import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

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

def estimate_activation(angle_features: pd.DataFrame,
                        active_muscles: list,
                        window: int = 15) -> pd.DataFrame:
    """
    関節角度から筋肉活動強度（0〜1）を推定

    active_muscles: muscle_mapping.jsonから取得した筋群名リスト
    戻り値: フレームごとの各筋肉の活動強度DataFrame
    """
    activations = {}

    for muscle in active_muscles:
        if muscle not in MUSCLE_JOINT_MAP:
            continue

        joint_scores = []
        for joint_col, direction in MUSCLE_JOINT_MAP[muscle]:
            if joint_col not in angle_features.columns:
                continue

            series = angle_features[joint_col].copy()

            # NaNを補完
            series = series.ffill().bfill()

            # 0〜1に正規化
            mn, mx = series.min(), series.max()
            #ゼロ除算
            if mx - mn < 1e-6:
                normalized = pd.Series(0.5, index=series.index)
            else:
                normalized = (series - mn) / (mx - mn)

            # 方向に応じて反転
            # small = 角度が小さいほど収縮強度が高い
            # large = 角度が大きいほど収縮強度が高い
            if direction == "small":
                score = 1.0 - normalized
            else:
                score = normalized

            # 速度成分を加味（速く動くほど強度UP）
            vel_col = f'{joint_col}_vel'
            if vel_col in angle_features.columns:
                vel = angle_features[vel_col].abs().ffill().bfill()
                vel_norm = vel / (vel.max() + 1e-8)
                score = score * 0.8 + vel_norm * 0.2

            joint_scores.append(score)

        if joint_scores:
            # 複数関節の平均
            activations[muscle] = pd.concat(joint_scores, axis=1).mean(axis=1)
    #.DataFrameは辞書や表データをきれいな表形式に変換する機能
    return pd.DataFrame(activations)

def visualize_activation(activations: pd.DataFrame,
                         exercise: str,
                         output_path: str):
    """筋肉活動強度を時系列グラフで可視化"""
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
