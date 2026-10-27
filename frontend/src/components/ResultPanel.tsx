"use client";
import { useState } from "react";
import { AnalyzeResult } from "@/types/analysis";
import { MuscleHeatmap } from "./MuscleHeatmap";
import { FormFeedbackCard } from "./FormFeedbackCard";
import { AvatarViewer3D } from "./AvatarViewer3D";

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

type Tab = "muscles" | "form" | "avatar3d";

export function ResultPanel({
  result,
  targetAngle,
  declaredReps,
  onReset,
}: {
  result: AnalyzeResult;
  targetAngle: number;
  declaredReps: number | null;
  onReset: () => void;
}) {
  const repKeys    = Object.keys(result.activations);
  const [activeRep, setActiveRep] = useState(0);
  const [tab, setTab]             = useState<Tab>("muscles");

  const repKey    = repKeys[activeRep] ?? "rep_1";
  const act       = result.activations[repKey] ?? {};
  const issues    = result.form_feedback?.[repKey] ?? [];
  const sorted    = Object.entries(act).sort((a, b) => b[1] - a[1]);
  const topMuscle = sorted[0];
  const errorCount   = issues.filter(i => i.severity === "error").length;
  const warningCount = issues.filter(i => i.severity === "warning").length;
  const has3D = (result.landmarks_3d ?? []).length > 0;

  return (
    <section className="w-full max-w-7xl mx-auto px-4 sm:px-8 pb-32">

      {/* ── ヘッダー ── */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8 pt-20 border-t border-[#0f0f0f]">
        <div>
          <p className="text-[10px] tracking-[0.3em] text-[#333] font-bold mb-1.5">ANALYSIS RESULT</p>
          <h2 className="text-3xl sm:text-4xl font-black tracking-tight">
            {result.exercise.replace(/_/g, " ")}
          </h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            {declaredReps && declaredReps !== result.total_reps ? (
              <div className="flex items-end gap-2">
                <span className="text-2xl font-black text-[#333] line-through">{declaredReps}</span>
                <span className="text-5xl font-black text-red-500 leading-none">{result.total_reps}</span>
              </div>
            ) : (
              <span className="text-5xl font-black text-red-500 leading-none">{result.total_reps}</span>
            )}
            <p className="text-[10px] tracking-[0.2em] text-[#444] mt-0.5">REPS DETECTED</p>
          </div>
          <button
            onClick={onReset}
            className="flex items-center gap-2 text-xs text-[#555] border border-[#1a1a1a]
              px-4 py-2.5 rounded-xl hover:border-[#333] hover:text-[#888] transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            再解析
          </button>
        </div>
      </div>

      {/* ── REPタブ ── */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {repKeys.map((key, i) => {
          const repIssues = result.form_feedback?.[key] ?? [];
          const hasError  = repIssues.some(x => x.severity === "error");
          const hasWarn   = repIssues.some(x => x.severity === "warning");
          return (
            <button
              key={key}
              onClick={() => { setActiveRep(i); setTab("muscles"); }}
              className={`flex-shrink-0 flex items-center gap-2.5 px-5 py-3 rounded-2xl border
                text-sm font-bold tracking-wide transition-all duration-200
                ${activeRep === i
                  ? "bg-red-600/15 border-red-600/40 text-white"
                  : "bg-[#0a0a0a] border-[#1a1a1a] text-[#555] hover:border-[#2a2a2a] hover:text-[#888]"
                }`}
            >
              <span className="font-mono text-[11px]">{key.replace("_", " ").toUpperCase()}</span>
              {hasError && <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />}
              {!hasError && hasWarn && <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 flex-shrink-0" />}
              {!hasError && !hasWarn && repIssues.length === 0 && (
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
              )}
            </button>
          );
        })}
      </div>

      {/* ── メインカード ── */}
      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-3xl overflow-hidden">
        <div className="flex flex-col lg:flex-row">

          {/* 左：ヒートマップ */}
          <div className="lg:w-64 xl:w-72 flex-shrink-0 bg-[#080808] border-b lg:border-b-0 lg:border-r border-[#111]
            flex flex-col items-center justify-center p-6 lg:p-8">
            {topMuscle && (
              <div className="flex items-center gap-2 mb-6 bg-[#0f0f0f] border border-[#1a1a1a] rounded-full px-3 py-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                <span className="text-[10px] text-[#666]">主動筋</span>
                <span className="text-[10px] text-white font-bold">
                  {MUSCLE_NAMES_JA[topMuscle[0]] ?? topMuscle[0]}
                </span>
              </div>
            )}
            <div className="w-full max-w-[180px] lg:max-w-none">
              <MuscleHeatmap activations={act} />
            </div>
            <div className="mt-6 flex items-center gap-2 text-[10px] text-[#444]">
              <span className="tracking-wider">目標</span>
              <span className="font-mono text-[#666]">{targetAngle}°</span>
            </div>
          </div>

          {/* 右：タブコンテンツ */}
          <div className="flex-1 min-w-0">
            {/* タブヘッダー */}
            <div className="flex border-b border-[#111]">
              <button
                onClick={() => setTab("muscles")}
                className={`flex-1 flex items-center justify-center gap-2 py-4 text-xs font-bold
                  tracking-[0.15em] transition-all border-b-2
                  ${tab === "muscles"
                    ? "text-white border-red-500"
                    : "text-[#444] border-transparent hover:text-[#666]"
                  }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                筋肉活動
              </button>
              <button
                onClick={() => setTab("form")}
                className={`flex-1 flex items-center justify-center gap-2 py-4 text-xs font-bold
                  tracking-[0.15em] transition-all border-b-2
                  ${tab === "form"
                    ? "text-white border-red-500"
                    : "text-[#444] border-transparent hover:text-[#666]"
                  }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                フォームチェック
                {(errorCount > 0 || warningCount > 0) && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full
                    ${errorCount > 0 ? "bg-red-600/20 text-red-400" : "bg-yellow-600/20 text-yellow-400"}`}>
                    {errorCount + warningCount}
                  </span>
                )}
              </button>
              {has3D && (
                <button
                  onClick={() => setTab("avatar3d")}
                  className={`flex-1 flex items-center justify-center gap-2 py-4 text-xs font-bold
                    tracking-[0.15em] transition-all border-b-2
                    ${tab === "avatar3d"
                      ? "text-white border-red-500"
                      : "text-[#444] border-transparent hover:text-[#666]"
                    }`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
                  </svg>
                  3Dアバター
                  <span className="text-[9px] text-red-500 font-bold">NEW</span>
                </button>
              )}
            </div>

            {/* タブコンテンツ */}
            <div className="p-6 lg:p-8">
              {tab === "muscles" && (
                <div className="space-y-4">
                  {sorted.map(([name, val], i) => (
                    <div key={name} className="group">
                      <div className="flex justify-between items-baseline mb-1.5">
                        <span className={`text-sm transition-colors
                          ${i === 0 ? "text-white font-semibold" : "text-[#555] group-hover:text-[#888]"}`}>
                          {MUSCLE_NAMES_JA[name] ?? name}
                        </span>
                        <span className={`font-mono font-bold tabular-nums
                          ${i === 0 ? "text-white text-base" : "text-[#3a3a3a] text-sm"}`}>
                          {(val * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-1 bg-[#111] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${val * 100}%`,
                            background: i === 0
                              ? "linear-gradient(90deg, #7f1d1d, #ef4444)"
                              : i === 1
                              ? "linear-gradient(90deg, #1c1c1c, #3f3f3f)"
                              : "linear-gradient(90deg, #141414, #222)",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {tab === "form" && (
                <FormFeedbackCard repKey={repKey} issues={issues} />
              )}

              {tab === "avatar3d" && has3D && (
                <div className="flex flex-col items-center gap-4">
                  <p className="text-[10px] tracking-[0.2em] text-[#444] font-bold">3D MOTION VIEWER</p>
                  <AvatarViewer3D
                    frames={result.landmarks_3d ?? []}
                    activations={act}
                  />
                  <p className="text-[#333] text-[10px] text-center">
                    筋肉活動強度に応じてボーンが赤くハイライトされます
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
