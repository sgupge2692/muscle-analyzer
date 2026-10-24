"use client";

import { useState, useRef } from "react";
import { AnalyzeResult } from "@/types/analysis";
import { analyzeVideo } from "@/lib/api";
import { MuscleHeatmap } from "@/components/MuscleHeatmap";
import { RepCard } from "@/components/RepCard";
import { RepAlert } from "@/components/RepAlert";
import { FormFeedbackCard } from "@/components/FormFeedbackCard";

const PROGRESS_STEPS = [
  { pct: 10, label: "動画を受信中..." },
  { pct: 25, label: "骨格を検出中..." },
  { pct: 55, label: "関節角度を計算中..." },
  { pct: 70, label: "レップを検出中..." },
  { pct: 85, label: "筋肉活動を推定中..." },
  { pct: 95, label: "結果をまとめています..." },
];

const TECH_STACK = ["MediaPipe", "FastAPI", "NumPy", "scikit-learn"];

const EXERCISE_OPTIONS = [
  { value: "Squats",             label: "スクワット" },
  { value: "Deadlift",           label: "デッドリフト" },
  { value: "Romanian_Deadlift",  label: "ルーマニアンDL" },
  { value: "Lunges",             label: "ランジ" },
  { value: "Push_ups",           label: "プッシュアップ" },
  { value: "Bench_Press",        label: "ベンチプレス" },
  { value: "Squat_Hold",         label: "スクワットホールド" },
];

export default function Home() {
  const [file, setFile]           = useState<File | null>(null);
  const [loading, setLoading]     = useState(false);
  const [pct, setPct]             = useState(0);
  const [stepLabel, setStepLabel] = useState("");
  const [result, setResult]       = useState<AnalyzeResult | null>(null);
  const [activeRep, setActiveRep] = useState(0);
  const [error, setError]         = useState<string | null>(null);
  const [dragOver, setDragOver]   = useState(false);
  const [targetAngle, setTargetAngle]   = useState(110);
  const [declaredReps, setDeclaredReps] = useState<number | null>(null);
  const [exercise, setExercise]         = useState("Squats");
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  function startFakeProgress() {
    timerRef.current.forEach(clearTimeout);
    timerRef.current = [];
    const delays = [0, 2000, 8000, 40000, 50000, 58000];
    PROGRESS_STEPS.forEach((step, i) => {
      const t = setTimeout(() => { setPct(step.pct); setStepLabel(step.label); }, delays[i]);
      timerRef.current.push(t);
    });
  }

  function clearFakeProgress() {
    timerRef.current.forEach(clearTimeout);
    timerRef.current = [];
  }

  async function handleSubmit(f?: File) {
    const target = f ?? file;
    if (!target) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setActiveRep(0);
    setPct(0);
    startFakeProgress();
    try {
      const data = await analyzeVideo(target, exercise, targetAngle);
      clearFakeProgress();
      setPct(100);
      setStepLabel("解析完了");
      setResult(data);
    } catch (e) {
      clearFakeProgress();
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) { setFile(f); handleSubmit(f); }
  }

  const repKeys = result ? Object.keys(result.activations) : [];

  return (
    <div className="min-h-screen bg-[#080808] text-white">
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-5
        border-b border-white/[0.04] bg-[#080808]/90 backdrop-blur-xl">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-sm font-bold tracking-[0.15em]">MUSCLE ANALYZER</span>
        </div>
        <span className="text-[10px] text-[#2a2a2a] tracking-[0.3em] font-medium">BETA</span>
      </nav>

      <section className="min-h-screen flex items-center pt-20">
        <div className="w-full max-w-7xl mx-auto px-8 grid grid-cols-2 gap-20 items-center">

          {/* 左カラム */}
          <div>
            <p className="text-[11px] font-bold tracking-[0.3em] text-red-500 mb-6">POWERED BY MEDIAPIPE</p>
            <h1 className="text-6xl font-black tracking-tight leading-[1.1] mb-6">
              筋肉活動を、<br />
              <span className="text-red-500">データで見る。</span>
            </h1>
            <p className="text-[#888888] text-base leading-relaxed mb-10 max-w-sm">
              筋トレ動画をアップロードするだけで、骨格検出・関節角度解析・筋肉活動推定を自動で実行します。
            </p>
            <div className="flex flex-wrap gap-2 mb-12">
              {TECH_STACK.map(t => (
                <span key={t} className="text-[11px] text-[#666666] border border-[#1a1a1a] px-3 py-1.5 rounded-full tracking-wider">
                  {t}
                </span>
              ))}
            </div>
            <div className="flex gap-10 pt-10 border-t border-[#111]">
              {[["137", "対応種目"], ["20", "筋群"], ["38", "特徴量"]].map(([n, l]) => (
                <div key={l}>
                  <p className="text-3xl font-black">{n}</p>
                  <p className="text-[11px] text-[#666666] mt-1 tracking-wider">{l}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 右カラム */}
          <div className="space-y-4">
            {/* 設定パネル */}
            <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-2xl p-6">
              <p className="text-[11px] font-bold tracking-[0.25em] text-[#666666] mb-5">ANALYSIS SETTINGS</p>

              {/* 種目選択 */}
              <div className="mb-6">
                <span className="text-xs text-[#555] block mb-3">種目</span>
                <div className="flex flex-wrap gap-2">
                  {EXERCISE_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => setExercise(opt.value)}
                      className={`text-[11px] px-3 py-1.5 rounded-xl border transition-all
                        ${exercise === opt.value
                          ? "bg-red-600/20 border-red-600/50 text-red-400"
                          : "bg-transparent border-[#1a1a1a] text-[#555] hover:border-[#2a2a2a] hover:text-[#888]"
                        }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mb-6">
                <div className="flex justify-between items-baseline mb-3">
                  <span className="text-xs text-[#555]">目標スクワット深度（膝角度）</span>
                  <span className="text-sm font-mono font-bold text-white">{targetAngle}°</span>
                </div>
                <input type="range" min={70} max={160} value={targetAngle}
                  onChange={(e) => setTargetAngle(Number(e.target.value))}
                  className="w-full h-[2px] bg-[#1a1a1a] rounded-full appearance-none cursor-pointer
                    [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4
                    [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:bg-red-500 [&::-webkit-slider-thumb]:cursor-pointer" />
                <div className="flex justify-between mt-1.5">
                  <span className="text-[10px] text-[#222]">深い 70°</span>
                  <span className="text-[10px] text-[#222]">浅い 160°</span>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-baseline mb-3">
                  <span className="text-xs text-[#555]">実施回数（自己申告）</span>
                  <span className="text-[10px] text-[#666666]">未入力の場合は検出値を使用</span>
                </div>
                <div className="flex items-center gap-3">
                  <input type="number" min={1} max={99} placeholder="—"
                    value={declaredReps ?? ""}
                    onChange={(e) => setDeclaredReps(e.target.value ? Number(e.target.value) : null)}
                    className="w-20 bg-[#111] border border-[#1a1a1a] rounded-xl px-3 py-2
                      text-white text-sm font-mono text-center focus:outline-none
                      focus:border-red-600/50 transition-colors" />
                  <span className="text-xs text-[#666666]">回</span>
                </div>
              </div>
            </div>

            {/* アップロードエリア */}
            <div onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              className={`rounded-3xl border-2 border-dashed transition-all duration-300
                ${dragOver ? "border-red-500/60 bg-red-500/5" : "border-[#1a1a1a] bg-[#0a0a0a]"}`}>

              {!loading && !result && (
                <div className="p-10 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-[#0f0f0f] border border-[#1a1a1a]
                    flex items-center justify-center mx-auto mb-5">
                    <svg className="w-6 h-6 text-[#2a2a2a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                    </svg>
                  </div>
                  {file ? (
                    <div className="mb-5">
                      <p className="text-white font-medium text-sm">{file.name}</p>
                      <p className="text-[#666666] text-xs mt-1">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                    </div>
                  ) : (
                    <div className="mb-2">
                      <p className="text-[#666666] text-sm mb-1">動画をドラッグ＆ドロップ</p>
                      <p className="text-[#1a1a1a] text-[11px] mt-2">MP4 / MOV  最大100MB</p>
                    </div>
                  )}
                  <label className="block mt-5 mb-3 cursor-pointer">
                    <input type="file" accept="video/*" className="hidden"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                    <span className="inline-block text-xs text-[#666666] border border-[#1a1a1a]
                      px-4 py-2 rounded-xl hover:border-[#2a2a2a] hover:text-[#555] transition-colors">
                      ファイルを選択
                    </span>
                  </label>
                  <button onClick={() => handleSubmit()} disabled={!file}
                    className="w-full py-3.5 mt-1 bg-red-600 hover:bg-red-500
                      disabled:bg-[#0f0f0f] disabled:text-[#222] disabled:cursor-not-allowed
                      text-white font-bold text-sm tracking-[0.1em] rounded-2xl transition-all duration-200">
                    解析する
                  </button>
                </div>
              )}

              {loading && (
                <div className="p-10 text-center">
                  <div className="w-10 h-10 rounded-full border-2 border-red-600 border-t-transparent
                    animate-spin mx-auto mb-6" />
                  <p className="text-white text-sm font-medium mb-1">{stepLabel}</p>
                  <p className="text-[#222] text-xs font-mono mb-6">{pct}%</p>
                  <div className="h-[1px] bg-[#0f0f0f] rounded-full overflow-hidden mb-4">
                    <div className="h-full bg-gradient-to-r from-red-900 to-red-500 rounded-full
                      transition-all duration-1000" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="flex gap-1">
                    {PROGRESS_STEPS.map((s, i) => (
                      <div key={i} className={`flex-1 h-[2px] rounded-full transition-all duration-500
                        ${pct >= s.pct ? "bg-red-600" : "bg-[#111]"}`} />
                    ))}
                  </div>
                </div>
              )}

              {!loading && result && (
                <div className="p-10 text-center">
                  <div className="w-10 h-10 rounded-full border border-red-500/30
                    flex items-center justify-center mx-auto mb-4">
                    <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-white text-sm font-medium mb-1">解析完了</p>
                  <p className="text-[#666666] text-xs mb-5">{result.total_reps} レップ検出</p>
                  <button onClick={() => { setResult(null); setFile(null); setPct(0); setDeclaredReps(null); }}
                    className="text-xs text-[#666666] hover:text-[#666] transition-colors">
                    別の動画を解析する →
                  </button>
                </div>
              )}
            </div>

            {error && (
              <div className="border border-red-900/40 bg-red-950/10 rounded-2xl p-4 text-red-500 text-sm">
                {error}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 結果セクション */}
      {result && (
        <section className="max-w-7xl mx-auto px-8 pb-32">
          <div className="border-t border-[#0f0f0f] pt-20">
            <div className="flex items-end justify-between mb-12">
              <div>
                <p className="text-[11px] tracking-[0.3em] text-[#222] font-bold mb-2">ANALYSIS RESULT</p>
                <h2 className="text-4xl font-black">{result.exercise.replace(/_/g, " ")}</h2>
              </div>
              <div className="text-right">
                {declaredReps && declaredReps !== result.total_reps ? (
                  <div>
                    <div className="flex items-end gap-3 justify-end">
                      <span className="text-[#666666] text-2xl font-black line-through">{declaredReps}</span>
                      <span className="text-7xl font-black text-red-500 leading-none">{result.total_reps}</span>
                    </div>
                    <p className="text-[11px] tracking-[0.2em] text-[#666666] mt-1">DETECTED / DECLARED</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-7xl font-black text-red-500 leading-none">{result.total_reps}</p>
                    <p className="text-[11px] tracking-[0.2em] text-[#666666] mt-1">REPS DETECTED</p>
                  </div>
                )}
              </div>
            </div>

            <RepAlert detected={result.total_reps} declared={declaredReps} />

            <div className="flex gap-4 mb-8">
              <div className="flex items-center gap-2 bg-[#0f0f0f] border border-[#1a1a1a] rounded-xl px-3 py-2">
                <span className="text-[10px] text-[#666666] tracking-wider">目標深度</span>
                <span className="text-xs font-mono text-white">{targetAngle}°</span>
              </div>
              {declaredReps && (
                <div className="flex items-center gap-2 bg-[#0f0f0f] border border-[#1a1a1a] rounded-xl px-3 py-2">
                  <span className="text-[10px] text-[#666666] tracking-wider">申告</span>
                  <span className="text-xs font-mono text-white">{declaredReps}回</span>
                </div>
              )}
            </div>

            <div className="flex gap-6 mb-8 border-b border-[#0f0f0f]">
              {repKeys.map((key, i) => (
                <button key={key} onClick={() => setActiveRep(i)}
                  className={`pb-3 text-xs font-mono tracking-[0.2em] transition-all
                    ${activeRep === i
                      ? "text-white border-b-2 border-red-500 -mb-[1px]"
                      : "text-[#666666] hover:text-[#666]"}`}>
                  {key.replace("_", " ").toUpperCase()}
                </button>
              ))}
            </div>

            {repKeys[activeRep] && (
              <RepCard
                key={repKeys[activeRep]}
                repKey={repKeys[activeRep]}
                act={result.activations[repKeys[activeRep]]}
              />
            )}

            {/* フォーム診断 */}
            {repKeys[activeRep] && (
              <div className="mt-6">
                <FormFeedbackCard
                  key={`form-${repKeys[activeRep]}`}
                  repKey={repKeys[activeRep]}
                  issues={result.form_feedback?.[repKeys[activeRep]] ?? []}
                />
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
