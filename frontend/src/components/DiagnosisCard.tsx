"use client";
import type {
  AnalyzeResult,
  DeviationDiagnosisItem,
  EvidenceLevelInfo,
  VelocityMetrics,
} from "@/types/analysis";

const MUSCLE_NAMES_JA: Record<string, string> = {
  Quadriceps:  "大腿四頭筋", Hamstring:   "ハムストリング",
  Gluteus:     "大臀筋",     Lower_Back:  "脊柱起立筋",
  Inner_Thigh: "内転筋",     Outer_Thigh: "外転筋",
  Calves:      "下腿三頭筋", Upper_Back:  "僧帽筋",
  Latissimus:  "広背筋",     Chest:       "大胸筋",
  Shoulder:    "三角筋",     Triceps:     "上腕三頭筋",
  Biceps:      "上腕二頭筋", Obliques:    "腹斜筋",
  Upper_Abs:   "腹直筋（上部）", Lower_Abs: "腹直筋（下部）",
  Forearms:    "前腕",       Feet_Ankles: "足首", Wrists: "手首",
};

const SEVERITY_LABEL = {
  normal: "正常範囲",
  watch:  "要観察",
  fix:    "修正推奨",
} as const;

const SEVERITY_STYLE = {
  normal: "bg-green-600/15 text-green-400 border-green-600/30",
  watch:  "bg-yellow-600/15 text-yellow-400 border-yellow-600/30",
  fix:    "bg-red-600/20 text-red-400 border-red-600/40",
} as const;

const EVIDENCE_LABEL: Record<string, string> = {
  literature_validated: "文献検証済み",
  literature_derived:   "文献派生",
  literature_referenced: "文献参照",
  model_estimate:       "モデル推定のみ",
};

function EvidenceChip({ info }: { info: EvidenceLevelInfo }) {
  const style =
    info.level === 2
      ? "bg-green-600/15 text-green-400 border-green-600/30"
      : info.level === 1
      ? "bg-sky-600/15 text-sky-400 border-sky-600/30"
      : "bg-[#141414] text-[#555] border-[#222]";
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${style}`}>
      {EVIDENCE_LABEL[info.label] ?? info.label}
    </span>
  );
}

function SectionTitle({ children }: { children: string }) {
  return (
    <p className="text-[10px] tracking-[0.25em] text-[#555] font-bold mb-3">
      {children}
    </p>
  );
}

function DeviationSection({ items }: { items: DeviationDiagnosisItem[] }) {
  if (items.length === 0) {
    return (
      <div>
        <SectionTitle>文献逸脱診断（活動ピーク角度）</SectionTitle>
        <p className="text-xs text-[#444]">
          この種目には文献のピーク角度データがないため，診断対象の筋はありません
        </p>
      </div>
    );
  }
  return (
    <div>
      <SectionTitle>文献逸脱診断（活動ピーク角度）</SectionTitle>
      <div className="space-y-2.5">
        {items.map((d) => (
          <div
            key={d.muscle}
            className="bg-[#0d0d0d] border border-[#1a1a1a] rounded-2xl p-4"
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-sm font-semibold text-white">
                {MUSCLE_NAMES_JA[d.muscle] ?? d.muscle}
              </span>
              <span
                className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${
                  SEVERITY_STYLE[d.severity]
                }`}
              >
                {SEVERITY_LABEL[d.severity]}
              </span>
            </div>
            <div className="flex items-baseline gap-4 font-mono text-xs text-[#666] mb-1">
              <span>
                実測 <span className="text-[#aaa]">{d.observed_flexion_deg}°</span>
              </span>
              <span>
                文献 <span className="text-[#aaa]">{d.literature_flexion_deg}°</span>
              </span>
              <span className={d.deviation_deg === 0 ? "" : Math.abs(d.deviation_deg) > 0 ? "text-red-400" : ""}>
                ずれ {d.deviation_deg > 0 ? "+" : ""}{d.deviation_deg}°
              </span>
            </div>
            {d.proposal && (
              <p className="text-xs text-[#777] mt-1.5 leading-relaxed">{d.proposal}</p>
            )}
            {d.source && (
              <p className="text-[10px] text-[#3f3f3f] mt-1.5">出典: {d.source}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidenceSection({ levels }: { levels: Record<string, EvidenceLevelInfo> }) {
  const entries = Object.entries(levels);
  if (entries.length === 0) return null;
  return (
    <div>
      <SectionTitle>エビデンスレベル（文献との検証状況）</SectionTitle>
      <div className="flex flex-wrap gap-2">
        {entries.map(([muscle, info]) => (
          <div
            key={muscle}
            className="flex items-center gap-2 bg-[#0d0d0d] border border-[#1a1a1a] rounded-full pl-3 pr-2.5 py-1.5"
          >
            <span className="text-xs text-[#bbb]">
              {MUSCLE_NAMES_JA[muscle] ?? muscle}
            </span>
            <EvidenceChip info={info} />
          </div>
        ))}
      </div>
      <p className="text-[10px] text-[#3f3f3f] mt-2 leading-relaxed">
        文献検証済み = 公表EMG文献の角度別定量値で検証 / 文献派生 = 文献由来パラメータのみ / モデル推定のみ = 文献の定量値なし
      </p>
    </div>
  );
}

function VelocitySection({ vm }: { vm: VelocityMetrics }) {
  const vels = vm.per_rep_velocities;
  const maxV = Math.max(...vels.map((v) => v.mean_concentric_velocity_deg_per_frame), 0.0001);
  const loss = vm.velocity_loss;
  return (
    <div>
      <SectionTitle>疲労指標（velocity loss・角速度プロキシ）</SectionTitle>
      {vels.length === 0 ? (
        <p className="text-xs text-[#444]">速度を計算できるレップがありませんでした</p>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            {vels.map((v) => (
              <div
                key={v.rep}
                className="bg-[#0d0d0d] border border-[#1a1a1a] rounded-2xl p-3 text-center"
              >
                <p className="text-[10px] text-[#444] mb-1">REP {v.rep}</p>
                <p className="font-mono font-bold text-white text-sm">
                  {(v.mean_concentric_velocity_deg_per_frame * 30).toFixed(0)}
                  <span className="text-[9px] text-[#555]"> °/s*</span>
                </p>
                <div className="h-1 bg-[#111] rounded-full overflow-hidden mt-2">
                  <div
                    className="h-full bg-gradient-to-r from-[#7f1d1d] to-[#ef4444] rounded-full"
                    style={{
                      width: `${(v.mean_concentric_velocity_deg_per_frame / maxV) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          {loss && (
            <div className="bg-[#0d0d0d] border border-[#1a1a1a] rounded-2xl p-4 mb-3">
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-xs text-[#666]">
                  velocity loss（初回レップ基準）
                </span>
                <span className="font-mono font-black text-2xl text-red-500">
                  {loss.final_loss_pct.toFixed(1)}
                  <span className="text-sm">%</span>
                </span>
              </div>
              <div className="space-y-1">
                {loss.per_rep.map((p) => {
                  const color =
                    p.velocity_loss_pct >= 40
                      ? "bg-red-500"
                      : p.velocity_loss_pct >= 20
                      ? "bg-yellow-500"
                      : "bg-green-500";
                  return (
                    <div key={p.rep} className="flex items-center gap-2">
                      <span className="text-[10px] text-[#444] w-10 shrink-0">
                        REP {p.rep}
                      </span>
                      <div className="flex-1 h-1.5 bg-[#111] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${color}`}
                          style={{ width: `${Math.min(p.velocity_loss_pct, 100)}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-[#666] w-12 text-right">
                        {p.velocity_loss_pct.toFixed(1)}%
                      </span>
                    </div>
                  );
                })}
              </div>
              <p className="text-[10px] text-[#3f3f3f] mt-2 leading-relaxed">
                {loss.note}（{loss.literature}）
              </p>
            </div>
          )}
          {vm.form_filtered && (
            <div className="bg-[#0d0d0d] border border-[#1a1a1a] rounded-2xl p-4">
              <p className="text-xs text-[#666] mb-1.5">フォーム妥当性フィルタ</p>
              <p className="text-xs text-[#888] leading-relaxed">
                逸脱レップ
                <span className="text-red-400 font-bold mx-1">
                  {vm.form_filtered.excluded_reps.join(", ")}
                </span>
                を除外した velocity loss:
                <span className="font-mono text-white font-bold ml-1">
                  {vm.form_filtered.velocity_loss
                    ? `${vm.form_filtered.velocity_loss.final_loss_pct.toFixed(1)}%`
                    : "算出不能"}
                </span>
              </p>
              <p className="text-[10px] text-[#3f3f3f] mt-1.5 leading-relaxed">
                {vm.form_filtered.note}
              </p>
            </div>
          )}
          <p className="text-[10px] text-[#3f3f3f] mt-2">
            * 膝関節角速度のプロキシ値（30fps想定で°/sに換算。バーベル速度ではありません）
          </p>
        </>
      )}
    </div>
  );
}

export function DiagnosisCard({ result }: { result: AnalyzeResult }) {
  const diagnosis = result.deviation_diagnosis ?? [];
  const evidence = result.evidence_levels ?? {};
  const velocity = result.velocity_metrics ?? null;
  const hasAny =
    diagnosis.length > 0 || Object.keys(evidence).length > 0 || velocity != null;
  if (!hasAny) {
    return (
      <p className="text-xs text-[#444]">
        この種目には診断用の文献データが整備されていません
      </p>
    );
  }
  return (
    <div className="space-y-6">
      <DeviationSection items={diagnosis} />
      <EvidenceSection levels={evidence} />
      {velocity && <VelocitySection vm={velocity} />}
    </div>
  );
}
