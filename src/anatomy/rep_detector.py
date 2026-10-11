import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from scipy.signal import find_peaks, peak_prominences
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

def load_knee_angles(csv_path: str) -> pd.Series:
    df = pd.read_csv(csv_path)
    angles = []
    for _, row in df.iterrows():
        if row['right_knee_visibility'] < 0.7:
            angles.append(np.nan)
            continue
        hip   = np.array([row['right_hip_x'],   row['right_hip_y']])
        knee  = np.array([row['right_knee_x'],  row['right_knee_y']])
        ankle = np.array([row['right_ankle_x'], row['right_ankle_y']])
        v1 = hip - knee; v2 = ankle - knee
        cos_a = np.dot(v1,v2)/(np.linalg.norm(v1)*np.linalg.norm(v2)+1e-8)
        angles.append(np.degrees(np.arccos(np.clip(cos_a,-1,1))))
    s = pd.Series(angles).ffill().bfill()
    return s.rolling(window=15, center=True).mean().ffill().bfill()


def detect_reps(angles: pd.Series,
                min_prominence: float = 20.0,
                min_distance: int = 30,
                angle_min: float = 90.0,
                angle_max: float = 160.0) -> list:
    """
    2段階フィルタによるレップ検出

    prominence：周囲との相対的な深さ（カメラ角度非依存）
    angle範囲：人体的にありえない値を除外（ノイズ対策）
    """
    inverted = -angles.values
    peaks, _ = find_peaks(inverted, prominence=min_prominence, distance=min_distance)
    prominences = peak_prominences(inverted, peaks)[0]

    reps = []
    rep_count = 0
    for peak, prom in zip(peaks, prominences):
        angle_at_bottom = float(angles.iloc[peak])

        # 角度フィルタ：人体的にありえない値を除外
        if not (angle_min <= angle_at_bottom <= angle_max):
            print(f"  [除外] frame={peak} angle={angle_at_bottom:.1f}° prominence={prom:.1f} → 角度範囲外")
            continue

        # start：底より前で角度が高い（立位）最後のフレーム
        standing_thresh = angles.mean() - angles.std() * 0.5
        before = angles.iloc[:peak]
        start_candidates = before[before > standing_thresh]
        start = int(start_candidates.index[-1]) if len(start_candidates) > 0 else 0

        # end：底より後で角度が高い（立位）最初のフレーム
        after = angles.iloc[peak:]
        end_candidates = after[after > standing_thresh]
        end = int(end_candidates.index[0]) if len(end_candidates) > 0 else len(angles) - 1

        rep_count += 1
        reps.append({
            "rep": rep_count,
            "start": start,
            "bottom": int(peak),
            "end": end,
            "min_angle": round(angle_at_bottom, 1),
            "prominence": round(float(prom), 1)
        })

    return reps


def visualize_reps(angles: pd.Series, reps: list, output_path: str):
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(angles, color='steelblue', linewidth=1.2, label='膝角度（平滑化）')
    ax.axhline(y=angles.mean(), color='gray', linestyle='--', alpha=0.5,
               label=f'平均({angles.mean():.1f}°)')

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    for rep in reps:
        color = colors[(rep['rep'] - 1) % len(colors)]
        ax.axvspan(rep['start'], rep['end'], alpha=0.2, color=color)
        ax.axvline(x=rep['bottom'], color=color, linewidth=2, alpha=0.8)
        ax.text(rep['bottom'], angles.min() - 5,
                f"Rep{rep['rep']}\n{rep['min_angle']}°",
                ha='center', fontsize=9, color=color, fontweight='bold')

    ax.set_xlabel('フレーム')
    ax.set_ylabel('角度（度）')
    ax.set_title('スクワット　レップ自動検出（Prominence + 角度フィルタ）')
    ax.legend(loc='lower right')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"保存: {output_path}")


if __name__ == "__main__":
    CSV_PATH   = "data/processed/squat_landmarks.csv"
    OUTPUT_IMG = "data/processed/rep_detection.png"

    print("膝角度を読み込み中...")
    angles = load_knee_angles(CSV_PATH)

    print("レップ検出中...")
    reps = detect_reps(angles)

    print(f"\n=== 検出結果: {len(reps)}レップ ===")
    for r in reps:
        print(f"  Rep{r['rep']}: フレーム {r['start']}〜{r['end']} "
              f"（最深部: {r['bottom']}フレーム, {r['min_angle']}°, prominence={r['prominence']}）")

    visualize_reps(angles, reps, OUTPUT_IMG)
