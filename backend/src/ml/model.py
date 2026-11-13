"""
1D-CNN筋肉活動分類モデル
入力: (N, 3, 30, 17) = (バッチ, xyz, フレーム, 関節)
出力: (N, 20) = 20筋肉のマルチラベル確率

注意（2026-11-13）:
  このクラスは output/best_1dcnn.pt（test_F1=0.957 の学習済み重み）と
  アーキテクチャが一致する版である。コミット 93bba09 で強化版アーキテクチャ
  （3層Conv・kernel 3/5/7・SE風構成）が書かれたが再学習はされておらず、
  このままだと学習済みチェックポイントがロードできず、本番のPyTorch推論も
  暗黙に失敗していた。強化版は model_evo.py（MuscleClassifier1DCNNEvo）に
  退避した。強化版で再学習して best_1dcnn.pt を差し替えた後に、本クラスを
  強化版へ置き換えること。
"""

import torch
import torch.nn as nn


class MuscleClassifier1DCNN(nn.Module):
    """
    設計思想：
    - 関節ごとに時間方向の特徴を抽出（1D Conv）
    - 全関節の特徴を統合してマルチラベル分類
    """

    def __init__(self, num_joints: int = 17, num_frames: int = 30, num_classes: int = 20):
        super().__init__()

        # ① 時間方向の特徴抽出（関節ごと）
        # 入力: (N, 3, 30, 17) → (N*17, 3, 30) に reshape して処理
        self.temporal_conv = nn.Sequential(
            nn.Conv1d(in_channels=3, out_channels=32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(in_channels=32, out_channels=64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),  # (N*17, 64, 30) → (N*17, 64, 1)
        )

        # ② 全関節の特徴を統合して分類
        self.classifier = nn.Sequential(
            nn.Linear(64 * num_joints, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
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

        # 時間方向の畳み込み
        x = self.temporal_conv(x)            # (N*V, 64, 1)
        x = x.squeeze(-1)                    # (N*V, 64)

        # 関節方向に戻して結合
        x = x.reshape(N, V * 64)            # (N, V*64) = (N, 17*64)

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
