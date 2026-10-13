import colorsys
from pathlib import Path
from typing import Dict

MUSCLE_PATHS = {
    "Quadriceps":  '<ellipse cx="75" cy="270" rx="22" ry="45" id="quad_l" class="muscle"/>'
                   '<ellipse cx="125" cy="270" rx="22" ry="45" id="quad_r" class="muscle"/>',
    "Hamstring":   '<ellipse cx="75" cy="275" rx="18" ry="38" id="ham_l" class="muscle" opacity="0.6"/>'
                   '<ellipse cx="125" cy="275" rx="18" ry="38" id="ham_r" class="muscle" opacity="0.6"/>',
    "Gluteus":     '<ellipse cx="75" cy="205" rx="28" ry="22" id="glute_l" class="muscle"/>'
                   '<ellipse cx="125" cy="205" rx="28" ry="22" id="glute_r" class="muscle"/>',
    "Lower_Back":  '<rect x="82" y="155" width="10" height="35" rx="5" id="lback_l" class="muscle"/>'
                   '<rect x="108" y="155" width="10" height="35" rx="5" id="lback_r" class="muscle"/>',
    "Inner_Thigh": '<ellipse cx="90" cy="265" rx="10" ry="35" id="ith_l" class="muscle" opacity="0.7"/>'
                   '<ellipse cx="110" cy="265" rx="10" ry="35" id="ith_r" class="muscle" opacity="0.7"/>',
    "Gastrocnemius": '<ellipse cx="75" cy="355" rx="12" ry="28" id="gastro_l" class="muscle"/>'
                     '<ellipse cx="125" cy="355" rx="12" ry="28" id="gastro_r" class="muscle"/>',
    "Core":        '<ellipse cx="100" cy="175" rx="22" ry="18" id="core" class="muscle"/>',
}

BODY_OUTLINE = """
  <ellipse cx="100" cy="45" rx="28" ry="32" fill="#ddd" stroke="#aaa" stroke-width="1.5"/>
  <rect x="90" y="74" width="20" height="18" rx="4" fill="#ddd" stroke="#aaa" stroke-width="1"/>
  <path d="M60,90 L55,185 L65,232 L135,232 L145,185 L140,90 Z" fill="#ddd" stroke="#aaa" stroke-width="1.5"/>
  <path d="M60,95 L38,165 L42,235" fill="none" stroke="#ddd" stroke-width="18" stroke-linecap="round"/>
  <path d="M140,95 L162,165 L158,235" fill="none" stroke="#ddd" stroke-width="18" stroke-linecap="round"/>
  <path d="M75,230 L68,325 L72,395" fill="none" stroke="#ddd" stroke-width="36" stroke-linecap="round"/>
  <path d="M125,230 L132,325 L128,395" fill="none" stroke="#ddd" stroke-width="36" stroke-linecap="round"/>
"""

def activation_to_color(v: float) -> str:
    v = max(0.0, min(1.0, v))
    r, g, b = colorsys.hsv_to_rgb(0.667 * (1 - v), 0.85, 0.95)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def render(activations: Dict[str, float], title: str, output: str):
    muscles_svg = ""
    legend_html = ""

    for name, val in sorted(activations.items(), key=lambda x: -x[1]):
        if name not in MUSCLE_PATHS:
            continue
        color = activation_to_color(val)
        muscles_svg += MUSCLE_PATHS[name].replace(
            'class="muscle"', f'fill="{color}" class="muscle" data-name="{name}" data-val="{val:.3f}"'
        ) + "\n"
        legend_html += f'<div class="leg"><span class="dot" style="background:{color}"></span>{name}: {val*100:.1f}%</div>\n'

    html = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><title>{title}</title>
<style>
  body{{font-family:sans-serif;background:#1a1a2e;color:#eee;display:flex;gap:40px;padding:40px;align-items:flex-start}}
  h2{{color:#a0cfff;margin:0 0 12px}}
  .leg{{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:14px}}
  .dot{{width:14px;height:14px;border-radius:3px;flex-shrink:0}}
  .muscle{{transition:opacity .2s;cursor:pointer}}
  .muscle:hover{{opacity:.6}}
  #tip{{position:fixed;top:16px;right:16px;background:rgba(0,0,0,.85);
        color:#fff;padding:8px 14px;border-radius:8px;display:none;font-size:13px}}
  .grad{{width:160px;height:16px;border-radius:4px;
         background:linear-gradient(to right,#0055ff,#ffff00,#ff2200);margin-top:16px}}
  .grad-label{{display:flex;justify-content:space-between;font-size:11px;color:#aaa}}
</style></head><body>
<div>
  <h2>{title}</h2>
  <svg viewBox="0 0 200 420" xmlns="http://www.w3.org/2000/svg" width="280" height="588"
       style="background:#2a2a3e;border-radius:12px">
    {BODY_OUTLINE}
    {muscles_svg}
  </svg>
</div>
<div>
  <h2>活動強度</h2>
  {legend_html}
  <div class="grad"></div>
  <div class="grad-label"><span>低</span><span>高</span></div>
  <p style="margin-top:20px;font-size:11px;color:#888">※ルールベース推定値</p>
</div>
<div id="tip"></div>
<script>
document.querySelectorAll('.muscle').forEach(el=>{{
  el.addEventListener('mouseenter',()=>{{
    const t=document.getElementById('tip');
    t.textContent=el.dataset.name+': '+(parseFloat(el.dataset.val)*100).toFixed(1)+'%';
    t.style.display='block';
  }});
  el.addEventListener('mouseleave',()=>document.getElementById('tip').style.display='none');
}});
</script>
</body></html>"""

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(html, encoding="utf-8")
    print(f"保存: {output}")
