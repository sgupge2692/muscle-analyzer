"""
MuscleMap骨格データセット（改善版）
ST-GCN入力形式 (N, C, T, V) = (サンプル数, 3, 30フレーム, 17関節) に変換する

改善点:
  - normalize_frames をnumpyベクトル化（ネストforループ廃止）
  - DataAugmentation: ガウスノイズ・時間反転・スケールジッタ
"""

import pickle
import numpy as np
from pathlib import Path
from torch.utils.data import Dataset
import torch


# COCO17の隣接関係（ST-GCNのグラフ定義に使う）
COCO17_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),       # 顔
    (5, 6),                                  # 肩
    (5, 7), (7, 9),                          # 左腕
    (6, 8), (8, 10),                         # 右腕
    (5, 11), (6, 12),                        # 体幹
    (11, 12),                                # 腰
    (11, 13), (13, 15),                      # 左脚
    (12, 14), (14, 16),                      # 右脚
]

NUM_JOINTS = 17
NUM_FRAMES = 30  # 正規化後のフレーム数
NUM_CHANNELS = 3  # x, y, confidence


def normalize_frames(keypoints: np.ndarray, scores: np.ndarray, target_frames: int = NUM_FRAMES) -> np.ndarray:
    """
    フレーム数をtarget_framesに正規化する（線形補間）— ベクトル化版

    Args:
        keypoints: (T, V, 2) ← 元のフレーム数・17関節・xy
        scores:    (T, V)    ← 信頼度
        target_frames: 正規化後のフレーム数

    Returns:
        (C, T, V) = (3, target_frames, 17) ← ST-GCN入力形式
    """
    T, V, _ = keypoints.shape

    old_idx = np.linspace(0, 1, T)
    new_idx = np.linspace(0, 1, target_frames)

    # (T, V, 3) の配列を作成: x, y, score を結合
    arr = np.concatenate([keypoints, scores[:, :, None]], axis=2)  # (T, V, 3)

    # (V, 3, T) に転置して各関節・チャネルの時系列を行として扱う
    arr_VCT = arr.transpose(1, 2, 0)  # (V, 3, T)

    # numpy の interp は1Dのみなので V*3 個を一括処理
    # arr_VCT.reshape(V*3, T) → 各行を補間 → (V*3, target_frames)
    flat = arr_VCT.reshape(V * NUM_CHANNELS, T)  # (V*C, T)
    flat_new = np.array([np.interp(new_idx, old_idx, row) for row in flat], dtype=np.float32)
    # (V*C, target_frames) → (V, C, target_frames) → (C, target_frames, V)
    result = flat_new.reshape(V, NUM_CHANNELS, target_frames).transpose(1, 2, 0)

    return result  # (C, T, V)


def augment_sequence(x: np.ndarray, noise_std: float = 0.005,
                     time_flip_prob: float = 0.3,
                     scale_jitter: float = 0.05) -> np.ndarray:
    """
    データ拡張（学習時のみ使用）

    Args:
        x: (C, T, V) の骨格シーケンス
        noise_std: ガウスノイズの標準偏差
        time_flip_prob: 時間反転の確率
        scale_jitter: スケールジッタの最大値

    Returns:
        (C, T, V) 拡張後のシーケンス
    """
    x = x.copy()

    # ① ガウスノイズ（座標にのみ適用、信頼度スコアには適用しない）
    if noise_std > 0:
        noise = np.random.randn(*x[:2].shape).astype(np.float32) * noise_std
        x[:2] += noise

    # ② 時間反転（特定確率でシーケンスを逆順にする）
    if np.random.random() < time_flip_prob:
        x = x[:, ::-1, :].copy()

    # ③ スケールジッタ（全体を微小に拡大縮小）
    if scale_jitter > 0:
        scale = 1.0 + np.random.uniform(-scale_jitter, scale_jitter)
        x[:2] *= scale  # xy座標にのみ適用

    return x


class MuscleMapDataset(Dataset):
    """
    MuscleMap骨格データセット（改善版）

    Args:
        labeled_pkl_path: musclemap_labeled.pklのパス
        skl_dir: musclemap136_skl/ディレクトリのパス
        num_classes: 筋肉クラス数（デフォルト20）
        augment: データ拡張を使用するか（学習時はTrue, 検証/テスト時はFalse）
    """

    def __init__(self, labeled_pkl_path: str, skl_dir: str,
                 num_classes: int = 20, augment: bool = False):
        self.skl_dir = Path(skl_dir)
        self.num_classes = num_classes
        self.augment = augment

        # ラベル対応表を読み込む
        with open(labeled_pkl_path, "rb") as f:
            self.samples = pickle.load(f)

        print(f"サンプル数: {len(self.samples)}, augment={augment}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx: int):
        sample = self.samples[idx]
        filename = sample["file"]           # "MuscleMap136_test_seen_sample_0.mp4"
        muscle_labels = sample["muscle_labels"]  # [2, 13, 14, ...]

        # .mp4 → .pkl に変換してsklファイルを読み込む
        skl_filename = filename.replace(".mp4", ".pkl")
        skl_path = self.skl_dir / skl_filename

        with open(skl_path, "rb") as f:
            skl_data = pickle.load(f)

        # 人物1人目だけ使う (10, 90, 17, 2) → (90, 17, 2)
        keypoints = skl_data["keypoint"][0]       # (T, V, 2)
        scores = skl_data["keypoint_score"][0]    # (T, V)

        # フレーム数を30に正規化 → (3, 30, 17) ★ベクトル化版
        x = normalize_frames(keypoints, scores)

        # データ拡張（学習時のみ）
        if self.augment:
            x = augment_sequence(x)

        # マルチラベルをone-hotに変換 [2,13,14] → [0,0,1,0,...,1,0,1,...]
        label = np.zeros(self.num_classes, dtype=np.float32)
        for muscle_id in muscle_labels:
            if 0 <= muscle_id < self.num_classes:
                label[muscle_id] = 1.0

        return torch.tensor(x, dtype=torch.float32), torch.tensor(label)


if __name__ == "__main__":
    # 動作確認
    dataset = MuscleMapDataset(
        labeled_pkl_path="backend/data/processed/musclemap_labeled.pkl",
        skl_dir="backend/data/raw/musclemap_benchmark/musclemap136_skl",
        augment=True,
    )

    x, label = dataset[0]
    print(f"入力テンソル shape: {x.shape}")   # torch.Size([3, 30, 17])
    print(f"ラベル shape: {label.shape}")      # torch.Size([20])
    print(f"アクティブな筋肉: {label.nonzero().squeeze().tolist()}")
