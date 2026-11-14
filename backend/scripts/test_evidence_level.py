"""
evidence_level の最小単体テスト（文献較正パイプラインの正式成果物）

実行方法（backend ディレクトリで）:
    ../.venv/bin/python scripts/test_evidence_level.py
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

from anatomy.evidence_level import evidence_level  # noqa: E402


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


if __name__ == "__main__":
    test_evidence_level()
    print("test_evidence_level: OK")
    print("全テスト成功")
