"""
ST-GCN訓練スクリプト（改善版）
実行: python3 backend/src/ml/train_stgcn.py

改善点:
  - Early stopping（patience=20）
  - Gradient clipping（max_norm=1.0）
  - DataAugmentationをtrainセットに適用
  - BATCH_SIZE=64に拡大
  - EPOCHS=300に延長
  - LR=5e-4に調整（ST-GCNは複雑なのでやや小さめ）
  - NUM_WORKERS=0に変更（2026-11-16。macOSでnum_workers=4×persistent_workersの
    2loader構成がデッドロックし1エポックも完了しなかったため。データは
    8,701件のpickleで小規模であり，単一プロセス読み込みで十分な速度）
  - 再開機能（2026-11-17追加）。毎エポック後に全状態（モデル＋optimizer＋
    scheduler＋進捗）を last_stgcn_full.pt に保存し，存在すればそこから厳密に
    再開する。last_stgcn_full.pt が無くてログだけある場合（本機能導入前に中断
    した2026-11-16実行が該当）は，ログから最終エポック・best val_F1・patience
    を復元し，best_stgcn.pt の重みのみでウォーム再開する
"""

from pathlib import Path

import torch
import torch.nn as nn
from dataset import MuscleMapDataset
from stgcn import STGCN
from torch.utils.data import DataLoader, Subset

# ─── 設定 ───────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent.parent
LABELED_PKL  = BASE_DIR / "data/processed/musclemap_labeled.pkl"
SKL_DIR      = BASE_DIR / "data/raw/musclemap_benchmark/musclemap136_skl"
OUTPUT_DIR   = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
FULL_CKPT    = OUTPUT_DIR / "last_stgcn_full.pt"
LOG_PATH     = OUTPUT_DIR / "train_stgcn_20261116.log"  # 中断済み実行のログ

BATCH_SIZE   = 64
EPOCHS       = 300
LR           = 5e-4
THRESHOLD    = 0.5   # マルチラベルの閾値
PATIENCE     = 20    # Early stopping
NUM_WORKERS  = 0     # 単一プロセス読み込み（macOSのmulti-loaderデッドロック回避）
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


def recover_progress_from_log(log_path: Path):
    """中断済み実行のログから (最終完了エポック, best val_F1, patience数) を復元する。

    ログが無い/読めない場合は (0, 0.0, 0) を返す（最初から訓練）。
    patience数 = bestエポックから最終エポックまでの経過エポック数。
    """
    if not log_path.exists():
        return 0, 0.0, 0
    epoch_f1: list[tuple[int, float]] = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("Epoch ") and "val_F1:" in line:
            try:
                e = int(line.split()[1].split("/")[0])
                f1 = float(line.rsplit("val_F1:", 1)[1].strip())
                epoch_f1.append((e, f1))
            except (ValueError, IndexError):
                continue
    if not epoch_f1:
        return 0, 0.0, 0
    last_epoch = max(e for e, _ in epoch_f1)
    best_epoch, best_f1 = max(epoch_f1, key=lambda x: x[1])
    patience_cnt = last_epoch - best_epoch
    return last_epoch, best_f1, patience_cnt


def train():
    print(f"デバイス: {DEVICE}")

    # データセット・分割（trainのみaugment=True）
    train_dataset = MuscleMapDataset(LABELED_PKL, SKL_DIR, augment=True)
    eval_dataset  = MuscleMapDataset(LABELED_PKL, SKL_DIR, augment=False)

    train_idx, val_idx, test_idx = split_indices(train_dataset)
    print(f"train: {len(train_idx)}, val: {len(val_idx)}, test: {len(test_idx)}")

    # num_workers=4で並列プリフェッチ
    train_loader = DataLoader(
        Subset(train_dataset, train_idx),
        batch_size=BATCH_SIZE, shuffle=True,
        num_workers=NUM_WORKERS, persistent_workers=NUM_WORKERS > 0,
        prefetch_factor=2 if NUM_WORKERS > 0 else None,
    )
    val_loader = DataLoader(
        Subset(eval_dataset, val_idx),
        batch_size=BATCH_SIZE, shuffle=False,
        num_workers=NUM_WORKERS, persistent_workers=NUM_WORKERS > 0,
        prefetch_factor=2 if NUM_WORKERS > 0 else None,
    )
    test_loader = DataLoader(
        Subset(eval_dataset, test_idx),
        batch_size=BATCH_SIZE, shuffle=False,
        num_workers=NUM_WORKERS, persistent_workers=NUM_WORKERS > 0,
        prefetch_factor=2 if NUM_WORKERS > 0 else None,
    )

    # モデル・損失・オプティマイザ
    model = STGCN().to(DEVICE)
    criterion = nn.BCEWithLogitsLoss()   # マルチラベル用（内部でSigmoid）
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_f1  = 0.0
    patience_cnt = 0
    start_epoch  = 1

    # ── 再開処理 ──
    if FULL_CKPT.exists():
        ck = torch.load(FULL_CKPT, map_location=DEVICE, weights_only=False)
        model.load_state_dict(ck["model"])
        optimizer.load_state_dict(ck["optimizer"])
        scheduler.load_state_dict(ck["scheduler"])
        start_epoch  = int(ck["epoch"]) + 1
        best_val_f1  = float(ck["best_val_f1"])
        patience_cnt = int(ck["patience_cnt"])
        print(f"→ last_stgcn_full.pt から厳密再開: epoch {start_epoch} から続行 "
              f"(best_val_F1={best_val_f1:.4f}, patience={patience_cnt})")
    else:
        last_epoch, log_best_f1, log_patience = recover_progress_from_log(LOG_PATH)
        if last_epoch > 0 and (OUTPUT_DIR / "best_stgcn.pt").exists():
            model.load_state_dict(
                torch.load(OUTPUT_DIR / "best_stgcn.pt", map_location=DEVICE, weights_only=True))
            best_val_f1  = log_best_f1
            patience_cnt = log_patience
            start_epoch  = last_epoch + 1
            for _ in range(last_epoch):   # schedulerを中断時点まで進める
                scheduler.step()
            print(f"→ ログからウォーム再開: epoch {start_epoch} から続行 "
                  f"(best_val_F1={best_val_f1:.4f}, patience={patience_cnt}, "
                  f"optimizer状態は初期化)")

    for epoch in range(start_epoch, EPOCHS + 1):
        # ── 訓練 ──
        model.train()
        train_loss = 0.0
        for x, label in train_loader:
            x, label = x.to(DEVICE), label.to(DEVICE)
            optimizer.zero_grad()
            out  = model(x)
            loss = criterion(out, label)
            loss.backward()
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
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

        print(f"Epoch {epoch:03d}/{EPOCHS} | loss: {train_loss/len(train_loader):.4f} | val_F1: {val_f1:.4f}")

        # ベストモデル保存
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            patience_cnt = 0
            torch.save(model.state_dict(), OUTPUT_DIR / "best_stgcn.pt")
            print(f"  → ベストモデル更新 (val_F1={val_f1:.4f})")
        else:
            patience_cnt += 1
            if patience_cnt >= PATIENCE:
                torch.save({
                    "model": model.state_dict(),
                    "optimizer": optimizer.state_dict(),
                    "scheduler": scheduler.state_dict(),
                    "epoch": epoch,
                    "best_val_f1": best_val_f1,
                    "patience_cnt": patience_cnt,
                }, FULL_CKPT)
                print(f"  → Early stopping (patience={PATIENCE})")
                break

        # 全状態チェックポイント（中断時の厳密再開用）
        torch.save({
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "epoch": epoch,
            "best_val_f1": best_val_f1,
            "patience_cnt": patience_cnt,
        }, FULL_CKPT)

    # ── テスト ──
    print("\n--- テスト評価 ---")
    model.load_state_dict(torch.load(OUTPUT_DIR / "best_stgcn.pt", weights_only=True))
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
    print("RF baseline:    0.916")


if __name__ == "__main__":
    train()
