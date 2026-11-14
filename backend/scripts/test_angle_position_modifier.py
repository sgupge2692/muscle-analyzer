"""
_angle_position_modifier と文献EMGカーブ適用ロジックの最小単体テスト

実行方法:
    ../.venv/bin/python src/../scripts/test_angle_position_modifier.py   # 単体実行
    ../.venv/bin/python -m pytest scripts/                               # pytest利用時
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anatomy.muscle_activation import (  # noqa: E402
    _angle_position_modifier,
    _literature_position_modifier,
    estimate_activation,
)


def test_modifier_peaks_at_reported_angle():
    # ピーク角度で1.0になる
    assert abs(_angle_position_modifier(90, 90, 35) - 1.0) < 1e-9


def test_modifier_is_symmetric():
    # ガウス型なので左右対称
    assert abs(_angle_position_modifier(55, 90, 35) - _angle_position_modifier(125, 90, 35)) < 1e-9


def test_modifier_decays_with_distance():
    # ピークから離れるほど単調に減衰し、常に0以上
    values = [_angle_position_modifier(a, 90, 35) for a in (90, 100, 125, 160, 180)]
    assert all(v > 0 for v in values)
    assert values == sorted(values, reverse=True)


def test_squats_quadriceps_applies_position_modifier():
    # Squats/Quadriceps は文献カーブ定義済み → 膝90°で変調が最大(1.0)になる
    features = pd.DataFrame({
        "right_knee": [90.0, 90.0], "left_knee": [90.0, 90.0],
        "right_knee_vel": [0.0, 0.0], "left_knee_vel": [0.0, 0.0],
    })
    mod = _literature_position_modifier(features, "Squats", "Quadriceps")
    assert mod is not None
    assert abs(mod.iloc[0] - 1.0) < 1e-9


def test_uncalibrated_pair_returns_none():
    # Deadlift/Gluteus はカーブ未定義（null）→ None で既存ロジックにフォールバック
    features = pd.DataFrame({"right_knee": [90.0], "left_knee": [90.0]})
    assert _literature_position_modifier(features, "Deadlift", "Gluteus") is None


def test_deadlift_calibrated_pairs_apply_position_modifier():
    # Deadlift の Quadriceps/Hamstring/Lower_Back は文献カーブ定義済み → 変調値を返す
    features = pd.DataFrame({"right_knee": [95.0], "left_knee": [95.0]})
    for muscle in ("Quadriceps", "Lower_Back"):
        mod = _literature_position_modifier(features, "Deadlift", muscle)
        assert mod is not None
        assert abs(mod.iloc[0] - 1.0) < 1e-9  # リフトオフ位置(膝95°)が両筋のピーク
    mod_bf = _literature_position_modifier(features, "Deadlift", "Hamstring")
    assert mod_bf is not None  # Hamstring のピークは150°なので95°では最大ではないが変調は返る


def test_unknown_muscle_returns_none():
    # 文献カーブJSONに存在しない筋群は None
    features = pd.DataFrame({"right_knee": [90.0], "left_knee": [90.0]})
    assert _literature_position_modifier(features, "Squats", "Chest") is None


def test_missing_knee_column_returns_none():
    # 膝角度列がない入力では変調を適用できない → None（フォールバック）
    features = pd.DataFrame({"right_hip": [90.0], "left_hip": [90.0]})
    assert _literature_position_modifier(features, "Squats", "Quadriceps") is None


def test_estimate_activation_shape_is_backward_compatible():
    # 出力形式（列・行数・値域）が従来どおりであることの確認
    n = 30
    features = pd.DataFrame(index=range(n))
    features["right_knee"] = [120 - 0.8 * i for i in range(n)]
    features["left_knee"] = features["right_knee"]
    features["right_hip"] = features["right_knee"] - 20
    features["left_hip"] = features["right_hip"]
    for c in ("right_knee", "left_knee", "right_hip", "left_hip"):
        features[f"{c}_vel"] = [1.0] * n

    activations = estimate_activation(features, ["Quadriceps", "Gluteus"], exercise="Squats")
    assert list(activations.columns) == ["Quadriceps", "Gluteus"]
    assert len(activations) == n
    assert activations.notna().all().all()
    assert (activations > 0).all().all()


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL {name}: {e}")
    if failed:
        raise SystemExit(f"{failed}件のテストが失敗")
    print("すべてのテストに合格")
