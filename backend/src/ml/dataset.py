"""
MuscleMap骨格データセット
ST-GCN入力形式 (N, C, T, V) = (サンプル数, 3, 30フレーム, 17関節) に変換する
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
    フレーム数をtarget_framesに正規化する（線形補間）
    
    Args:
        keypoints: (T, V, 2) ← 元のフレーム数・17関節・xy
        scores:    (T, V)    ← 信頼度
        target_frames: 正規化後のフレーム数
    
    Returns:
        (C, T, V) = (3, target_frames, 17) ← ST-GCN入力形式
    """
    T, V, _ = keypoints.shape

    # x座標・y座標・信頼度を別々に補間
    result = np.zeros((NUM_CHANNELS, target_frames, V), dtype=np.float32)

    for v in range(V):
        for c, src in enumerate([keypoints[:, v, 0], keypoints[:, v, 1], scores[:, v]]):
            # 元のフレームインデックスを0〜1に正規化して補間
            old_idx = np.linspace(0, 1, T)
            new_idx = np.linspace(0, 1, target_frames)
            result[c, :, v] = np.interp(new_idx, old_idx, src)

    return result


class MuscleMapDataset(Dataset):
    """
    MuscleMap骨格データセット
    
    Args:
        labeled_pkl_path: musclemap_labeled.pklのパス
        skl_dir: musclemap136_skl/ディレクトリのパス
        num_classes: 筋肉クラス数（デフォルト20）
    """

    def __init__(self, labeled_pkl_path: str, skl_dir: str, num_classes: int = 20):
        self.skl_dir = Path(skl_dir)
        self.num_classes = num_classes

        # ラベル対応表を読み込む
        with open(labeled_pkl_path, "rb") as f:
            self.samples = pickle.load(f)

        print(f"サンプル数: {len(self.samples)}")

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

        # フレーム数を30に正規化 → (3, 30, 17)
        x = normalize_frames(keypoints, scores)

        # マルチラベルをone-hotに変換 [2,13,14] → [0,0,1,0,...,1,0,1,...]
        label = np.zeros(self.num_classes, dtype=np.float32)
        for muscle_id in muscle_labels:
            if 0 <= muscle_id < self.num_classes:
                label[muscle_id] = 1.0

        return torch.tensor(x), torch.tensor(label)


if __name__ == "__main__":
    # 動作確認
    dataset = MuscleMapDataset(
        labeled_pkl_path="backend/data/processed/musclemap_labeled.pkl",
        skl_dir="backend/data/raw/musclemap_benchmark/musclemap136_skl",
    )

    x, label = dataset[0]
    print(f"入力テンソル shape: {x.shape}")   # torch.Size([3, 30, 17])
    print(f"ラベル shape: {label.shape}")      # torch.Size([20])
    print(f"アクティブな筋肉: {label.nonzero().squeeze().tolist()}")