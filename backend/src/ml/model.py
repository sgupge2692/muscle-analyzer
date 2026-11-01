"""
1D-CNN筋肉活動分類モデル（改善版）
入力: (N, 3, 30, 17) = (バッチ, xyz, フレーム, 関節)
出力: (N, 20) = 20筋肉のマルチラベル確率

改善点:
  - Conv層を2層→3層に増加 (32→64→128ch)
  - kernel_sizeを3/5の2段構成で受容野を拡大
  - Classifier: 256→512→256の2段MLP
  - BatchNormをLinear前にも追加
  - Dropout率を0.5→0.4に調整
"""

import torch
import torch.nn as nn


class MuscleClassifier1DCNN(nn.Module):
    """
    設計思想：
    - 関節ごとに時間方向の特徴を抽出（1D Conv × 3層）
    - SE-style Channel Attentionで重要チャネルを強調
    - 全関節の特徴を統合してマルチラベル分類
    """

    def __init__(self, num_joints: int = 17, num_frames: int = 30, num_classes: int = 20):
        super().__init__()

        # ① 時間方向の特徴抽出（関節ごと）
        # 入力: (N, 3, 30, 17) → (N*17, 3, 30) に reshape して処理
        self.temporal_conv = nn.Sequential(
            # 第1層: 細粒度の特徴（kernel=3）
            nn.Conv1d(in_channels=3, out_channels=32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            # 第2層: 中粒度の特徴（kernel=5）
            nn.Conv1d(in_channels=32, out_channels=64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            # 第3層: 粗粒度の特徴（kernel=7）
            nn.Conv1d(in_channels=64, out_channels=128, kernel_size=7, padding=3),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),  # (N*17, 128, 30) → (N*17, 128, 1)
        )

        # ② 全関節の特徴を統合して分類
        in_features = 128 * num_joints  # 128 * 17 = 2176
        self.classifier = nn.Sequential(
            nn.BatchNorm1d(in_features),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.BatchNorm1d(512),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(256, num_classes),
            # Sigmoidはloss関数側で処理するのでここでは不要
        )

        self.num_joints = num_joints

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (N, C, T, V) = (バッチ, 3, 30, 17)
        Returns:
            (N, 20)
        """
        N, C, T, V = x.shape

        # (N, C, T, V) → (N*V, C, T): 関節をバッチ方向に展開
        x = x.permute(0, 3, 1, 2)          # (N, V, C, T)
        x = x.reshape(N * V, C, T)          # (N*V, C, T)

        # 時間方向の畳み込み（3層）
        x = self.temporal_conv(x)            # (N*V, 128, 1)
        x = x.squeeze(-1)                    # (N*V, 128)

        # 関節方向に戻して結合
        x = x.reshape(N, V * 128)            # (N, V*128) = (N, 17*128)

        # 分類
        x = self.classifier(x)              # (N, 20)
        return x


if __name__ == "__main__":
    # 動作確認
    model = MuscleClassifier1DCNN()
    dummy = torch.randn(4, 3, 30, 17)      # バッチサイズ4のダミーデータ
    out = model(dummy)
    print(f"入力: {dummy.shape}")
    print(f"出力: {out.shape}")             # torch.Size([4, 20])
    print(f"パラメータ数: {sum(p.numel() for p in model.parameters()):,}")
