import { ActivationMap } from "@/types/analysis";

const MUSCLE_NAMES_JA: Record<string, string> = {
  Quadriceps:   "大腿四頭筋",
  Hamstring:    "ハムストリング",
  Gluteus:      "大臀筋",
  Lower_Back:   "脊柱起立筋",
  Inner_Thigh:  "内転筋",
  Outer_Thigh:  "外転筋",
  Calves:       "下腿三頭筋",
  Upper_Back:   "僧帽筋",
  Latissimus:   "広背筋",
  Chest:        "大胸筋",
  Shoulder:     "三角筋",
  Triceps:      "上腕三頭筋",
  Biceps:       "上腕二頭筋",
  Obliques:     "腹斜筋",
  Upper_Abs:    "腹直筋（上部）",
  Lower_Abs:    "腹直筋（下部）",
  Forearms:     "前腕",
  Feet_Ankles:  "足首",
};

// SVG座標系 viewBox="0 0 200 480"
// 人体シルエットに合わせた解剖学的に正確な位置
const MUSCLE_SHAPES: Record<string, Array<{
  cx: number; cy: number; rx: number; ry: number; opacity?: number
}>> = {
  // ── 胸・肩 ──────────────────────────────
  Chest:       [{ cx: 100, cy: 105, rx: 26, ry: 18 }],
  Shoulder:    [{ cx: 58,  cy: 100, rx: 12, ry: 10 }, { cx: 142, cy: 100, rx: 12, ry: 10 }],

  // ── 上腕 ────────────────────────────────
  Biceps:      [{ cx: 46,  cy: 135, rx: 8,  ry: 18 }, { cx: 154, cy: 135, rx: 8,  ry: 18 }],
  Triceps:     [{ cx: 44,  cy: 138, rx: 7,  ry: 18, opacity: 0.7 }, { cx: 156, cy: 138, rx: 7, ry: 18, opacity: 0.7 }],
  Forearms:    [{ cx: 42,  cy: 175, rx: 7,  ry: 18 }, { cx: 158, cy: 175, rx: 7,  ry: 18 }],

  // ── 背中 ────────────────────────────────
  Upper_Back:  [{ cx: 84,  cy: 100, rx: 10, ry: 14 }, { cx: 116, cy: 100, rx: 10, ry: 14 }],
  Latissimus:  [{ cx: 72,  cy: 130, rx: 9,  ry: 22 }, { cx: 128, cy: 130, rx: 9,  ry: 22 }],
  Lower_Back:  [{ cx: 86,  cy: 195, rx: 10, ry: 18 }, { cx: 114, cy: 195, rx: 10, ry: 18 }],

  // ── 腹部 ────────────────────────────────
  Upper_Abs:   [{ cx: 100, cy: 135, rx: 14, ry: 16 }],
  Lower_Abs:   [{ cx: 100, cy: 165, rx: 13, ry: 14 }],
  Obliques:    [{ cx: 76,  cy: 155, rx: 9,  ry: 20 }, { cx: 124, cy: 155, rx: 9,  ry: 20 }],

  // ── 臀部 ────────────────────────────────
  // 大臀筋：骨盤後部・臀部（cy=230付近）
  Gluteus:     [{ cx: 76,  cy: 233, rx: 22, ry: 20 }, { cx: 124, cy: 233, rx: 22, ry: 20 }],

  // ── 大腿部 ──────────────────────────────
  // 大腿四頭筋：大腿前面（cy=280）
  Quadriceps:  [{ cx: 76,  cy: 282, rx: 17, ry: 40 }, { cx: 124, cy: 282, rx: 17, ry: 40 }],
  // ハムストリング：大腿後面（同じy座標だが後ろ側・opacity低め）
  Hamstring:   [{ cx: 76,  cy: 282, rx: 14, ry: 38, opacity: 0.6 }, { cx: 124, cy: 282, rx: 14, ry: 38, opacity: 0.6 }],
  // 内転筋：大腿内側（cx が中央寄り）
  Inner_Thigh: [{ cx: 87,  cy: 278, rx: 8,  ry: 32 }, { cx: 113, cy: 278, rx: 8,  ry: 32 }],
  // 外転筋：大腿外側
  Outer_Thigh: [{ cx: 64,  cy: 278, rx: 8,  ry: 32 }, { cx: 136, cy: 278, rx: 8,  ry: 32 }],

  // ── 下腿部 ──────────────────────────────
  // 下腿三頭筋：ふくらはぎ（cy=365）
  Calves:      [{ cx: 76,  cy: 365, rx: 13, ry: 32 }, { cx: 124, cy: 365, rx: 13, ry: 32 }],
  Feet_Ankles: [{ cx: 76,  cy: 420, rx: 10, ry: 10 }, { cx: 124, cy: 420, rx: 10, ry: 10 }],
};

function activationToColor(value: number, opacity: number = 1): string {
  const r = Math.round(80 + value * 175);
  const g = Math.round(80 - value * 70);
  const b = Math.round(80 - value * 70);
  return `rgba(${r},${g},${b},${opacity})`;
}

export function MuscleHeatmap({ activations }: { activations: ActivationMap }) {
  return (
    <svg viewBox="0 0 200 460" className="w-full h-auto">
      {/* ── 人体シルエット ── */}
      {/* 頭 */}
      <ellipse cx="100" cy="38" rx="26" ry="30" fill="#2a2a2a" />
      {/* 首 */}
      <rect x="92" y="66" width="16" height="16" rx="4" fill="#2a2a2a" />
      {/* 胴体 */}
      <path d="M62,82 L58,215 L82,240 L118,240 L142,215 L138,82 Z" fill="#2a2a2a" />
      {/* 左腕 */}
      <path d="M62,90 L40,150 L38,200" fill="none" stroke="#2a2a2a" strokeWidth="18" strokeLinecap="round" />
      {/* 右腕 */}
      <path d="M138,90 L160,150 L162,200" fill="none" stroke="#2a2a2a" strokeWidth="18" strokeLinecap="round" />
      {/* 左脚 */}
      <path d="M82,238 L74,335 L72,430" fill="none" stroke="#2a2a2a" strokeWidth="34" strokeLinecap="round" />
      {/* 右脚 */}
      <path d="M118,238 L126,335 L128,430" fill="none" stroke="#2a2a2a" strokeWidth="34" strokeLinecap="round" />

      {/* ── 筋肉ヒートマップ ── */}
      {Object.entries(activations).map(([name, value]) => {
        const shapes = MUSCLE_SHAPES[name];
        if (!shapes || value < 0.01) return null;
        return shapes.map((s, i) => (
          <ellipse
            key={name + i}
            cx={s.cx} cy={s.cy} rx={s.rx} ry={s.ry}
            fill={activationToColor(value, s.opacity ?? 0.9)}
          >
            <title>{MUSCLE_NAMES_JA[name] ?? name}: {(value * 100).toFixed(1)}%</title>
          </ellipse>
        ));
      })}
    </svg>
  );
}
