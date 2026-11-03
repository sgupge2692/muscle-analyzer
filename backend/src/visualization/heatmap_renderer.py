"""
heatmap_renderer.py
筋肉活動強度をSVG人体図にレンダリングしてHTMLとして出力する

筋肉名は muscle_mapping.json の muscle_groups と完全一致させること。
フロントの MuscleHeatmap.tsx と同じSVGパスを使用。
"""
import colorsys
from pathlib import Path
from typing import Dict


# ── 人体SVGパス（200×420 viewBox、全20筋群対応） ──────────────────
# muscle_mapping.json の筋群名と完全一致させること
MUSCLE_SHAPES: Dict[str, str] = {
    # ── 下半身（前面） ──
    "Quadriceps":  (
        '<ellipse cx="72" cy="268" rx="21" ry="44" />'
        '<ellipse cx="128" cy="268" rx="21" ry="44" />'
    ),
    "Inner_Thigh": (
        '<ellipse cx="88" cy="263" rx="10" ry="34" opacity="0.8"/>'
        '<ellipse cx="112" cy="263" rx="10" ry="34" opacity="0.8"/>'
    ),
    "Outer_Thigh": (
        '<ellipse cx="58" cy="260" rx="10" ry="34" opacity="0.7"/>'
        '<ellipse cx="142" cy="260" rx="10" ry="34" opacity="0.7"/>'
    ),
    "Calves": (
        '<ellipse cx="73" cy="352" rx="11" ry="27" />'
        '<ellipse cx="127" cy="352" rx="11" ry="27" />'
    ),
    "Feet_Ankles": (
        '<ellipse cx="73" cy="395" rx="12" ry="10" />'
        '<ellipse cx="127" cy="395" rx="12" ry="10" />'
    ),
    # ── 下半身（後面） ──
    "Gluteus": (
        '<ellipse cx="78" cy="207" rx="26" ry="21" />'
        '<ellipse cx="122" cy="207" rx="26" ry="21" />'
    ),
    "Hamstring": (
        '<ellipse cx="73" cy="272" rx="17" ry="38" opacity="0.65"/>'
        '<ellipse cx="127" cy="272" rx="17" ry="38" opacity="0.65"/>'
    ),
    # ── 体幹 ──
    "Lower_Back": (
        '<rect x="83" y="157" width="10" height="34" rx="5" />'
        '<rect x="107" y="157" width="10" height="34" rx="5" />'
    ),
    "Upper_Abs": (
        '<ellipse cx="100" cy="155" rx="18" ry="14" />'
    ),
    "Lower_Abs": (
        '<ellipse cx="100" cy="178" rx="16" ry="14" />'
    ),
    "Obliques": (
        '<ellipse cx="77" cy="165" rx="10" ry="22" opacity="0.8"/>'
        '<ellipse cx="123" cy="165" rx="10" ry="22" opacity="0.8"/>'
    ),
    # ── 上半身 ──
    "Chest": (
        '<ellipse cx="83" cy="118" rx="17" ry="22" />'
        '<ellipse cx="117" cy="118" rx="17" ry="22" />'
    ),
    "Upper_Back": (
        '<ellipse cx="83" cy="118" rx="15" ry="20" opacity="0.7"/>'
        '<ellipse cx="117" cy="118" rx="15" ry="20" opacity="0.7"/>'
    ),
    "Latissimus": (
        '<ellipse cx="68" cy="140" rx="13" ry="30" opacity="0.8"/>'
        '<ellipse cx="132" cy="140" rx="13" ry="30" opacity="0.8"/>'
    ),
    "Shoulder": (
        '<ellipse cx="57" cy="96" rx="16" ry="14" />'
        '<ellipse cx="143" cy="96" rx="16" ry="14" />'
    ),
    # ── 腕 ──
    "Biceps": (
        '<ellipse cx="49" cy="135" rx="9" ry="22" />'
        '<ellipse cx="151" cy="135" rx="9" ry="22" />'
    ),
    "Triceps": (
        '<ellipse cx="49" cy="140" rx="8" ry="22" opacity="0.7"/>'
        '<ellipse cx="151" cy="140" rx="8" ry="22" opacity="0.7"/>'
    ),
    "Forearms": (
        '<ellipse cx="43" cy="185" rx="7" ry="24" />'
        '<ellipse cx="157" cy="185" rx="7" ry="24" />'
    ),
    "Wrists": (
        '<ellipse cx="40" cy="225" rx="6" ry="8" />'
        '<ellipse cx="160" cy="225" rx="6" ry="8" />'
    ),
    # ── 頭部（予約枠） ──
    "Neck_Head_reserved": '<ellipse cx="100" cy="47" rx="24" ry="29" opacity="0.4"/>',
}

# 人体アウトライン（グレー）
BODY_OUTLINE = """
  <!-- 頭 -->
  <ellipse cx="100" cy="47" rx="27" ry="31" fill="#2a2a2a" stroke="#3a3a3a" stroke-width="1.5"/>
  <!-- 首 -->
  <rect x="93" y="76" width="14" height="16" rx="4" fill="#2a2a2a" stroke="#3a3a3a" stroke-width="1"/>
  <!-- 胴体 -->
  <path d="M62,92 L57,187 L67,232 L133,232 L143,187 L138,92 Z"
        fill="#2a2a2a" stroke="#3a3a3a" stroke-width="1.5"/>
  <!-- 左腕 -->
  <path d="M62,97 L40,168 L44,238" fill="none" stroke="#2a2a2a"
        stroke-width="18" stroke-linecap="round"/>
  <!-- 右腕 -->
  <path d="M138,97 L160,168 L156,238" fill="none" stroke="#2a2a2a"
        stroke-width="18" stroke-linecap="round"/>
  <!-- 左脚 -->
  <path d="M77,232 L70,328 L74,398" fill="none" stroke="#2a2a2a"
        stroke-width="34" stroke-linecap="round"/>
  <!-- 右脚 -->
  <path d="M123,232 L130,328 L126,398" fill="none" stroke="#2a2a2a"
        stroke-width="34" stroke-linecap="round"/>
"""

# 日本語表示名
MUSCLE_NAMES_JA: Dict[str, str] = {
    "Quadriceps":          "大腿四頭筋",
    "Hamstring":           "ハムストリング",
    "Gluteus":             "大臀筋",
    "Lower_Back":          "脊柱起立筋",
    "Inner_Thigh":         "内転筋",
    "Outer_Thigh":         "外転筋",
    "Calves":              "下腿三頭筋",
    "Upper_Back":          "僧帽筋",
    "Latissimus":          "広背筋",
    "Chest":               "大胸筋",
    "Shoulder":            "三角筋",
    "Triceps":             "上腕三頭筋",
    "Biceps":              "上腕二頭筋",
    "Obliques":            "腹斜筋",
    "Upper_Abs":           "腹直筋（上部）",
    "Lower_Abs":           "腹直筋（下部）",
    "Forearms":            "前腕",
    "Feet_Ankles":         "足首",
    "Wrists":              "手首",
    "Neck_Head_reserved":  "頸部（予約）",
}


def activation_to_color(v: float, alpha: float = 1.0) -> str:
    """
    活動強度（0〜1）を色に変換する。
    低活動: 暗いグレー → 高活動: 鮮やかな赤
    """
    v = max(0.0, min(1.0, v))
    if v < 0.05:
        return f"rgba(45,45,45,{alpha})"
    r = int(80  + v * 175)
    g = int(80  - v * 70)
    b = int(80  - v * 70)
    return f"rgba({r},{g},{b},{alpha})"


def render_svg(activations: Dict[str, float]) -> str:
    """
    筋肉活動マップをSVG文字列として返す（APIレスポンス・フロント埋め込み用）
    """
    shapes_svg = ""
    for name, shape in MUSCLE_SHAPES.items():
        v     = activations.get(name, 0.0)
        color = activation_to_color(v)
        shapes_svg += (
            shape
            .replace("<ellipse", f'<ellipse fill="{color}" data-muscle="{name}" data-val="{v:.4f}"')
            .replace("<rect",    f'<rect fill="{color}" data-muscle="{name}" data-val="{v:.4f}"')
            + "\n"
        )
    return (
        f'''<svg viewBox="0 0 200 420" xmlns="http://www.w3.org/2000/svg">'''
        + BODY_OUTLINE
        + shapes_svg
        + "</svg>"
    )


def render_html(
    activations: Dict[str, float],
    title: str = "筋肉活動ヒートマップ",
    output: str = "output/heatmap.html",
) -> None:
    """
    筋肉活動マップをインタラクティブHTMLとして出力する（CLI用）
    """
    # 凡例（活動強度順にソート）
    legend_rows = ""
    for name, v in sorted(activations.items(), key=lambda x: -x[1]):
        color   = activation_to_color(v)
        ja_name = MUSCLE_NAMES_JA.get(name, name)
        legend_rows += (
            f'''<div class="leg">'''
            f'''<span class="dot" style="background:{color}"></span>'''
            f'''{ja_name}: {v*100:.1f}%</div>\n'''
        )

    svg = render_svg(activations)
    html = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><title>{title}</title>
<style>
  body{{font-family:sans-serif;background:#080808;color:#ededed;
       display:flex;gap:40px;padding:40px;align-items:flex-start}}
  h2{{color:#ef4444;margin:0 0 12px;font-size:16px;letter-spacing:.1em}}
  .leg{{display:flex;align-items:center;gap:8px;margin:4px 0;font-size:13px}}
  .dot{{width:12px;height:12px;border-radius:2px;flex-shrink:0}}
  svg [data-muscle]{{transition:opacity .15s;cursor:pointer}}
  svg [data-muscle]:hover{{opacity:.5}}
  #tip{{position:fixed;top:16px;right:16px;background:rgba(0,0,0,.9);
        color:#fff;padding:8px 14px;border-radius:8px;display:none;font-size:13px;
        border:1px solid #2a2a2a}}
  .grad{{width:160px;height:12px;border-radius:4px;
         background:linear-gradient(to right,#2d2d2d,#991b1b,#ef4444);margin-top:16px}}
  .grad-label{{display:flex;justify-content:space-between;font-size:11px;color:#555;margin-top:4px}}
</style></head><body>
<div>
  <h2>{title}</h2>
  {svg}
</div>
<div>
  <h2>活動強度（上位順）</h2>
  {legend_rows}
  <div class="grad"></div>
  <div class="grad-label"><span>低</span><span>高</span></div>
  <p style="margin-top:20px;font-size:11px;color:#444">※ルールベース + 深層学習ハイブリッド推定値</p>
</div>
<div id="tip"></div>
<script>
const NAMES = {json.dumps(MUSCLE_NAMES_JA, ensure_ascii=False)};
document.querySelectorAll('[data-muscle]').forEach(el => {{
  el.addEventListener('mouseenter', () => {{
    const t = document.getElementById('tip');
    const ja = NAMES[el.dataset.muscle] || el.dataset.muscle;
    t.textContent = ja + ': ' + (parseFloat(el.dataset.val)*100).toFixed(1) + '%';
    t.style.display = 'block';
  }});
  el.addEventListener('mouseleave', () => document.getElementById('tip').style.display = 'none');
}});
</script>
</body></html>"""

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(html, encoding="utf-8")
    print(f"保存: {output}")


if __name__ == "__main__":
    # テスト用ダミーデータ
    test_activations = {
        "Quadriceps": 0.85, "Gluteus": 0.72, "Hamstring": 0.61,
        "Lower_Back": 0.45, "Calves":  0.30, "Inner_Thigh": 0.25,
        "Obliques":   0.15, "Upper_Abs": 0.10,
    }
    render_html(test_activations, "スクワット筋肉活動ヒートマップ", "output/heatmap_test.html")
    print("SVG文字列の長さ:", len(render_svg(test_activations)))
