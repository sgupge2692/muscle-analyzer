import { ActivationMap } from "@/types/analysis";

const MUSCLE_NAMES_JA: Record<string, string> = {
  Quadriceps:  "大腿四頭筋",
  Hamstring:   "ハムストリング",
  Gluteus:     "大臀筋",
  Lower_Back:  "脊柱起立筋",
  Inner_Thigh: "内転筋",
};

const MUSCLE_SHAPES: Record<string, Array<{ cx: number; cy: number; rx: number; ry: number }>> = {
  Quadriceps:  [{ cx: 74, cy: 292, rx: 15, ry: 38 }, { cx: 126, cy: 292, rx: 15, ry: 38 }],
  Hamstring:   [{ cx: 74, cy: 292, rx: 13, ry: 36 }, { cx: 126, cy: 292, rx: 13, ry: 36 }],
  Gluteus:     [{ cx: 74, cy: 238, rx: 20, ry: 16 }, { cx: 126, cy: 238, rx: 20, ry: 16 }],
  Inner_Thigh: [{ cx: 84, cy: 290, rx: 7,  ry: 30 }, { cx: 116, cy: 290, rx: 7,  ry: 30 }],
  Lower_Back:  [{ cx: 87, cy: 202, rx: 8,  ry: 16 }, { cx: 113, cy: 202, rx: 8,  ry: 16 }],
};

function activationToColor(value: number): string {
  const r = Math.round(80 + value * 175);
  const g = Math.round(80 - value * 70);
  const b = Math.round(80 - value * 70);
  return `rgb(${r},${g},${b})`;
}

export function MuscleHeatmap({ activations }: { activations: ActivationMap }) {
  return (
    <svg viewBox="0 0 200 420" className="w-full h-auto">
      <ellipse cx="100" cy="45" rx="28" ry="32" fill="#2a2a2a" />
      <rect x="90" y="74" width="20" height="18" rx="4" fill="#2a2a2a" />
      <path d="M60,90 L55,185 L65,232 L135,232 L145,185 L140,90 Z" fill="#2a2a2a" />
      <path d="M60,95 L38,165 L42,235" fill="none" stroke="#2a2a2a" strokeWidth="18" strokeLinecap="round" />
      <path d="M140,95 L162,165 L158,235" fill="none" stroke="#2a2a2a" strokeWidth="18" strokeLinecap="round" />
      <path d="M75,230 L68,325 L72,395" fill="none" stroke="#2a2a2a" strokeWidth="36" strokeLinecap="round" />
      <path d="M125,230 L132,325 L128,395" fill="none" stroke="#2a2a2a" strokeWidth="36" strokeLinecap="round" />
      {Object.entries(activations).map(([name, value]) => {
        const shapes = MUSCLE_SHAPES[name];
        if (!shapes) return null;
        return shapes.map((s, i) => (
          <ellipse key={name + i} cx={s.cx} cy={s.cy} rx={s.rx} ry={s.ry}
            fill={activationToColor(value)} opacity={0.95}>
            <title>{MUSCLE_NAMES_JA[name] ?? name}: {(value * 100).toFixed(1)}%</title>
          </ellipse>
        ));
      })}
    </svg>
  );
}
