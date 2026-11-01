"""
ST-GCN (Spatial Temporal Graph Convolutional Network) — 改善版
論文: Yan et al., 2018 "Spatial Temporal Graph Convolutional Networks for Skeleton-Based Action Recognition"
入力: (N, C, T, V) = (バッチ, 3, 30フレーム, 17関節)
出力: (N, 20) = 20筋肉のマルチラベル確率

改善点:
  - ブロック数: 3→5 (64→64→128→128→256)
  - TCN kernel_sizeを後半ほど細かく (9,9,7,7,5)
  - 各ブロック末尾にSE-style Channel Attention追加
  - 各ブロック末尾にDropout(0.1)追加（過学習抑制）
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
# torch_geometric不要の自前GCN実装\uff08Kipf & Welling 2017\uff09
class GCNConv(nn.Module):
    """スパースグラフ畳み込み層\uff08torch_geometric不要版\uff09"""
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.linear = nn.Linear(in_channels, out_channels, bias=True)
        nn.init.xavier_uniform_(self.linear.weight)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        N = x.size(0)
        row, col = edge_index[0], edge_index[1]
        deg = torch.zeros(N, device=x.device).scatter_add(0, row, torch.ones(row.size(0), device=x.device))
        deg_inv_sqrt = deg.pow(-0.5).clamp(max=10.0)
        norm = deg_inv_sqrt[row] * deg_inv_sqrt[col]
        agg = torch.zeros_like(x)
        agg.scatter_add_(0, col.unsqueeze(1).expand(-1, x.size(1)), x[row] * norm.unsqueeze(1))
        return self.linear(agg + x)
import numpy as np


# COCO17の隣接行列（骨格グラフ）
COCO17_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),    # 顔
    (5, 6),                              # 肩
    (5, 7), (7, 9),                      # 左腕
    (6, 8), (8, 10),                     # 右腕
    (5, 11), (6, 12),                    # 体幹
    (11, 12),                            # 腰
    (11, 13), (13, 15),                  # 左脚
    (12, 14), (14, 16),                  # 右脚
]


def build_edge_index(num_nodes: int = 17) -> torch.Tensor:
    """双方向エッジのedge_indexを生成 shape: (2, E*2)"""
    src, dst = zip(*COCO17_EDGES)
    # 双方向にする
    edge_index = torch.tensor(
        [src + dst, dst + src], dtype=torch.long
    )
    return edge_index


class SEBlock(nn.Module):
    """
    Squeeze-and-Excitation チャネルアテンション
    重要なチャネルを強調・不要なチャネルを抑制する
    """

    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(channels, max(channels // reduction, 4)),
            nn.ReLU(),
            nn.Linear(max(channels // reduction, 4), channels),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (N, C, T, V)
        Returns:
            (N, C, T, V) — チャネル方向に重み付け
        """
        # グローバル平均プーリングでチャネル統計量を計算
        w = x.mean(dim=[2, 3])       # (N, C)
        w = self.fc(w)               # (N, C) → Sigmoid
        return x * w.unsqueeze(-1).unsqueeze(-1)  # ブロードキャスト


class STGCNBlock(nn.Module):
    """
    ST-GCNの基本ブロック（改善版）
    空間方向：GCN（関節間の関係）
    時間方向：1D Conv（フレーム間の変化）
    追加: SE Attention + Dropout
    """

    def __init__(self, in_channels: int, out_channels: int,
                 stride: int = 1, tcn_kernel: int = 9, dropout: float = 0.1):
        super().__init__()

        # 空間方向のGCN
        self.gcn = GCNConv(in_channels, out_channels)

        # 時間方向の1D Conv
        padding = tcn_kernel // 2
        self.tcn = nn.Sequential(
            nn.BatchNorm1d(out_channels),
            nn.ReLU(),
            nn.Conv1d(
                out_channels, out_channels,
                kernel_size=tcn_kernel, stride=stride, padding=padding
            ),
            nn.BatchNorm1d(out_channels),
        )

        # SE Attention（チャネルアテンション）
        self.se = SEBlock(out_channels)

        # Dropout（ブロック末尾）
        self.dropout = nn.Dropout(dropout)

        # 残差接続
        if in_channels != out_channels or stride != 1:
            self.residual = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1, stride=stride),
                nn.BatchNorm1d(out_channels),
            )
        else:
            self.residual = nn.Identity()

        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (N, C, T, V)
            edge_index: (2, E)
        Returns:
            (N, out_channels, T', V)
        """
        N, C, T, V = x.shape

        # 残差用に保存
        res = x  # (N, C, T, V)

        # GCN：時間フレームごとに空間グラフを処理
        # (N, C, T, V) → (N*T, V, C) → GCN → (N*T, V, out_C)
        x = x.permute(0, 2, 3, 1).reshape(N * T, V, C)  # (N*T, V, C)

        # GCNConvは (num_nodes, C) を期待するので flatten
        x = x.reshape(N * T * V, C)
        # edge_indexをバッチ分オフセットして展開
        batch_edge = self._expand_edge_index(edge_index, N * T, V)
        x = self.gcn(x, batch_edge)                      # (N*T*V, out_C)
        out_C = x.shape[-1]

        x = x.reshape(N, T, V, out_C)
        x = x.permute(0, 3, 1, 2)                        # (N, out_C, T, V)

        # TCN：関節ごとに時間方向を処理
        # (N, out_C, T, V) → (N*V, out_C, T) → TCN → (N*V, out_C, T')
        x = x.permute(0, 3, 1, 2).reshape(N * V, out_C, T)
        x = self.tcn(x)                                   # (N*V, out_C, T')
        T_new = x.shape[-1]
        x = x.reshape(N, V, out_C, T_new).permute(0, 2, 3, 1)  # (N, out_C, T', V)

        # SE Attention
        x = self.se(x)

        # 残差接続
        res = res.permute(0, 3, 1, 2).reshape(N * V, C, T)
        res = self.residual(res)
        res = res.reshape(N, V, out_C, T_new).permute(0, 2, 3, 1)

        x = self.relu(x + res)

        # Dropout
        x = self.dropout(x)

        return x

    @staticmethod
    def _expand_edge_index(edge_index: torch.Tensor, num_graphs: int, num_nodes: int) -> torch.Tensor:
        """バッチ内の各グラフのedge_indexにオフセットを加算"""
        offsets = torch.arange(num_graphs, device=edge_index.device) * num_nodes
        offsets = offsets.repeat_interleave(edge_index.shape[1])
        edge_index_expanded = edge_index.repeat(1, num_graphs)
        edge_index_expanded = edge_index_expanded + offsets.unsqueeze(0)
        return edge_index_expanded


class STGCN(nn.Module):
    """
    ST-GCN本体（改善版）
    5層のSTGCNBlockで特徴抽出 → Global Average Pooling → 分類
    """

    def __init__(self, in_channels: int = 3, num_classes: int = 20, num_joints: int = 17):
        super().__init__()

        self.edge_index = build_edge_index(num_joints)

        # 入力正規化
        self.bn = nn.BatchNorm2d(in_channels)

        # ST-GCNブロック（チャネルを段階的に増やす）
        # TCNカーネルは後半ほど小さくして受容野を調整
        self.blocks = nn.ModuleList([
            STGCNBlock(in_channels,  64,  tcn_kernel=9, dropout=0.1),
            STGCNBlock(64,           64,  tcn_kernel=9, dropout=0.1),
            STGCNBlock(64,           128, tcn_kernel=7, dropout=0.1),
            STGCNBlock(128,          128, tcn_kernel=7, dropout=0.1),
            STGCNBlock(128,          256, tcn_kernel=5, dropout=0.1),
        ])

        # 分類ヘッド
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (N, C, T, V) = (バッチ, 3, 30, 17)
        Returns:
            (N, 20)
        """
        N = x.shape[0]
        edge_index = self.edge_index.to(x.device)

        x = self.bn(x)

        for block in self.blocks:
            x = block(x, edge_index)          # (N, C', T, V)

        # Global Average Pooling（時間・関節方向を平均）
        x = x.mean(dim=[2, 3])               # (N, 256)

        return self.classifier(x)             # (N, 20)


if __name__ == "__main__":
    model = STGCN()
    dummy = torch.randn(4, 3, 30, 17)
    out = model(dummy)
    print(f"入力: {dummy.shape}")
    print(f"出力: {out.shape}")               # torch.Size([4, 20])
    print(f"パラメータ数: {sum(p.numel() for p in model.parameters()):,}")
