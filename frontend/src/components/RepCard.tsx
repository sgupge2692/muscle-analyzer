import { ActivationMap } from "@/types/analysis";
import { MuscleHeatmap } from "./MuscleHeatmap";

const MUSCLE_NAMES_JA: Record<string, string> = {
  Quadriceps:  "大腿四頭筋",
  Hamstring:   "ハムストリング",
  Gluteus:     "大臀筋",
  Lower_Back:  "脊柱起立筋",
  Inner_Thigh: "内転筋",
};

export function RepCard({ repKey, act }: { repKey: string; act: ActivationMap }) {
  const sorted = Object.entries(act).sort((a, b) => b[1] - a[1]);
  const topMuscle = sorted[0];
  return (
    <div className="bg-[#0d0d0d] border border-[#1e1e1e] rounded-3xl overflow-hidden">
      <div className="grid grid-cols-[auto_1fr]">
        <div className="bg-[#0a0a0a] p-8 flex items-center justify-center min-w-[220px]">
          <MuscleHeatmap activations={act} />
        </div>
        <div className="p-8">
          <div className="flex items-center justify-between mb-6">
            <span className="text-[11px] font-bold tracking-[0.25em] text-[#666666] uppercase">
              {repKey.replace("_", " ")}
            </span>
            {topMuscle && (
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                <span className="text-xs text-[#666]">
                  主動筋: <span className="text-white">{MUSCLE_NAMES_JA[topMuscle[0]] ?? topMuscle[0]}</span>
                </span>
              </div>
            )}
          </div>
          <div className="space-y-5">
            {sorted.map(([name, val], i) => (
              <div key={name}>
                <div className="flex justify-between items-baseline mb-2">
                  <span className={`text-sm ${i === 0 ? "text-white font-medium" : "text-[#555]"}`}>
                    {MUSCLE_NAMES_JA[name] ?? name}
                  </span>
                  <span className={`font-mono font-bold ${i === 0 ? "text-white text-lg" : "text-[#444] text-sm"}`}>
                    {(val * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-1.5 bg-[#141414] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-1000"
                    style={{
                      width: `${val * 100}%`,
                      background: i === 0
                        ? "linear-gradient(90deg, #991b1b, #ef4444)"
                        : "linear-gradient(90deg, #1f1f1f, #3f3f3f)"
                    }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
