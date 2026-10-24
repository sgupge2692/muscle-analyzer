"""
1D-CNN訓練スクリプト
実行: python3 backend/src/ml/train.py
"""

import pickle
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from pathlib import Path
import numpy as np

from dataset import MuscleMapDataset
from stgcn import STGCN

# ─── 設定 ───────────────────────────────────────────
LABELED_PKL  = "../../data/processed/musclemap_labeled.pkl"
SKL_DIR      = "../../data/raw/musclemap_benchmark/musclemap136_skl"
OUTPUT_DIR   = Path("../../output")
OUTPUT_DIR.mkdir(exist_ok=True)

BATCH_SIZE   = 32
EPOCHS       = 200
LR           = 1e-3
THRESHOLD    = 0.5   # マルチラベルの閾値
DEVICE       = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
# ────────────────────────────────────────────────────


def split_indices(dataset: MuscleMapDataset):
    """ファイル名のsplitキーワードでtrain/val/testに分ける"""
    train_idx, val_idx, test_idx = [], [], []
    for i, s in enumerate(dataset.samples):
        f = s["file"]
        if "train" in f:
            train_idx.append(i)
        elif "val_seen" in f:
            val_idx.append(i)
        elif "test_seen" in f:
            test_idx.append(i)
    return train_idx, val_idx, test_idx


def f1_score_multilabel(preds: torch.Tensor, labels: torch.Tensor, threshold: float = THRESHOLD):
    """マルチラベルF1スコア（micro）を計算"""
    preds_bin = (preds > threshold).float()
    tp = (preds_bin * labels).sum()
    fp = (preds_bin * (1 - labels)).sum()
    fn = ((1 - preds_bin) * labels).sum()
    precision = tp / (tp + fp + 1e-8)
    recall    = tp / (tp + fn + 1e-8)
    f1 = 2 * precision * recall / (precision + recall + 1e-8)
    return f1.item()


def train():
    print(f"デバイス: {DEVICE}")

    # データセット・分割
    dataset = MuscleMapDataset(LABELED_PKL, SKL_DIR)
    train_idx, val_idx, test_idx = split_indices(dataset)
    print(f"train: {len(train_idx)}, val: {len(val_idx)}, test: {len(test_idx)}")

    train_loader = DataLoader(Subset(dataset, train_idx), batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(Subset(dataset, val_idx),   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader  = DataLoader(Subset(dataset, test_idx),  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # モデル・損失・オプティマイザ
    model = STGCN().to(DEVICE)
    criterion = nn.BCEWithLogitsLoss()   # マルチラベル用（内部でSigmoid）
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_f1 = 0.0

    for epoch in range(1, EPOCHS + 1):
        # ── 訓練 ──
        model.train()
        train_loss = 0.0
        for x, label in train_loader:
            x, label = x.to(DEVICE), label.to(DEVICE)
            optimizer.zero_grad()
            out  = model(x)
            loss = criterion(out, label)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        scheduler.step()

        # ── 検証 ──
        model.eval()
        val_preds, val_labels = [], []
        with torch.no_grad():
            for x, label in val_loader:
                x = x.to(DEVICE)
                out = torch.sigmoid(model(x))
                val_preds.append(out.cpu())
                val_labels.append(label)

        val_preds  = torch.cat(val_preds)
        val_labels = torch.cat(val_labels)
        val_f1 = f1_score_multilabel(val_preds, val_labels)

        print(f"Epoch {epoch:02d}/{EPOCHS} | loss: {train_loss/len(train_loader):.4f} | val_F1: {val_f1:.4f}")

        # ベストモデル保存
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            torch.save(model.state_dict(), OUTPUT_DIR / "best_stgcn.pt")
            print(f"  → ベストモデル更新 (val_F1={val_f1:.4f})")

    # ── テスト ──
    print("\n--- テスト評価 ---")
    model.load_state_dict(torch.load(OUTPUT_DIR / "best_stgcn.pt"))
    model.eval()
    test_preds, test_labels = [], []
    with torch.no_grad():
        for x, label in test_loader:
            x = x.to(DEVICE)
            out = torch.sigmoid(model(x))
            test_preds.append(out.cpu())
            test_labels.append(label)

    test_preds  = torch.cat(test_preds)
    test_labels = torch.cat(test_labels)
    test_f1 = f1_score_multilabel(test_preds, test_labels)
    print(f"test_F1 (seen): {test_f1:.4f}")
    print(f"RF baseline:    0.916")


if __name__ == "__main__":
    train()