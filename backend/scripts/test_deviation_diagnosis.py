"""
deviation_diagnosis / velocity_metrics の最小単体テスト（合成データ）

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/test_deviation_diagnosis.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

from anatomy.deviation_diagnosis import diagnose_peak_angle_deviation, evidence_level  # noqa: E402
from anatomy.velocity_metrics import (  # noqa: E402
    estimate_1rm_two_point, filter_form_valid_reps, rep_angular_velocities, velocity_loss,
)


def test_evidence_level():
    lv = evidence_level("Squats", "Quadriceps")
    assert lv["level"] == 2 and lv["label"] == "literature_validated", lv
    lv2 = evidence_level("Deadlift", "Quadriceps")
    assert lv2["level"] == 2 and lv2["label"] == "literature_validated", lv2
    lv2b = evidence_level("Deadlift", "Gluteus")
    # Deadlift/Gluteus は文献に角度別定量値がなく data_points=null → 文献参照のみ
    assert lv2b["level"] == 0 and lv2b["label"] == "literature_referenced", lv2b
    lv3 = evidence_level("Squats", "Biceps")
    assert lv3["level"] == 0 and lv3["label"] == "model_estimate", lv3


def test_peak_angle_deviation():
    # 膝角度: 解剖学的角度 160°→90°（屈曲方向）→160°
    # 活動ピークを浅い角度（解剖学的150°＝屈曲30°）に置く
    frames = list(range(10))
    angles = pd.Series([160, 150, 140, 130, 110, 90, 100, 120, 140, 160], index=frames)
    act = pd.DataFrame({
        "Quadriceps": [0.3, 0.5, 0.4, 0.6, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2],
        "Hamstring": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
    }, index=frames)
    issues = diagnose_peak_angle_deviation(act, angles, "Squats")
    q = [d for d in issues if d["muscle"] == "Quadriceps"]
    assert len(q) == 1, issues
    # ピークフレームは角度110°（屈曲70°）→ 文献90°（屈曲90°）に対し-20°ずれ→ watch
    assert q[0]["severity"] == "watch", q[0]
    assert q[0]["deviation_deg"] == -20.0, q[0]
    # Hamstring はピーク角度未定義（null）なので診断対象外
    assert all(d["muscle"] != "Hamstring" for d in issues), issues


def test_velocity_loss():
    angles = pd.Series([160, 90, 100, 110, 120, 160, 90, 100, 105, 115])
    reps = [
        {"rep": 1, "start": 0, "bottom": 1, "end": 4, "min_angle": 90},
        {"rep": 2, "start": 4, "bottom": 6, "end": 9, "min_angle": 90},
    ]
    vels = rep_angular_velocities(angles, reps)
    assert len(vels) == 2, vels
    assert vels[0]["mean_concentric_velocity_deg_per_frame"] == 10.0, vels
    assert vels[1]["mean_concentric_velocity_deg_per_frame"] == 8.3333, vels
    vl = velocity_loss(vels)
    assert vl is not None and "per_rep" in vl, vl
    # rep2 の速度が rep1 より遅い → 正の loss
    assert vl["per_rep"][0]["velocity_loss_pct"] == 16.7, vl


def test_form_filter():
    reps = [{"rep": 1}, {"rep": 2}, {"rep": 3}]
    valid, excluded = filter_form_valid_reps(reps, {"rep_2": ["knee"]})
    assert excluded == [2] and len(valid) == 2, (valid, excluded)


def test_1rm():
    r = estimate_1rm_two_point([(60, 0.8), (100, 0.4)], v1rm=None)
    assert r["estimated_1rm_kg"] is None  # v1RM 未確定の間は推定不可
    r2 = estimate_1rm_two_point([(60, 0.8), (100, 0.4)], v1rm=0.3)
    # v = a + b·L: a=1.4, b=-0.01 → 1RM=(0.3-1.4)/(-0.01)=110
    assert r2["estimated_1rm_kg"] == 110.0, r2


if __name__ == "__main__":
    test_evidence_level()
    print("test_evidence_level: OK")
    test_peak_angle_deviation()
    print("test_peak_angle_deviation: OK")
    test_velocity_loss()
    print("test_velocity_loss: OK")
    test_form_filter()
    print("test_form_filter: OK")
    test_1rm()
    print("test_1rm: OK")
    print("全テスト成功")
