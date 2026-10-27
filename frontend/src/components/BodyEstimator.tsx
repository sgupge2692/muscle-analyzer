"use client";
import { useState, useRef } from "react";
import { estimateBody, BodyEstimation } from "@/lib/api";

export function BodyEstimator({ onEstimated }: { onEstimated?: (data: BodyEstimation) => void }) {
  const [frontFile, setFrontFile]   = useState<File | null>(null);
  const [sideFile,  setSideFile]    = useState<File | null>(null);
  const [heightCm,  setHeightCm]    = useState<number>(170);
  const [result,    setResult]      = useState<BodyEstimation | null>(null);
  const [loading,   setLoading]     = useState(false);
  const [error,     setError]       = useState<string | null>(null);
  const frontRef = useRef<HTMLInputElement>(null);
  const sideRef  = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!frontFile) { setError("正面写真を選択してください"); return; }
    setLoading(true); setError(null);
    try {
      const data = await estimateBody(frontFile, heightCm, sideFile ?? undefined);
      setResult(data);
      onEstimated?.(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  const ImageDropZone = ({
    label, file, inputRef, onChange,
  }: {
    label: string;
    file: File | null;
    inputRef: React.RefObject<HTMLInputElement | null>;
    onChange: (f: File) => void;
  }) => (
    <div
      className="flex-1 border border-dashed border-[#2a2a2a] rounded-2xl p-6 flex flex-col items-center
        justify-center gap-3 cursor-pointer hover:border-[#444] transition-colors min-h-[140px]"
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={e => e.target.files?.[0] && onChange(e.target.files[0])}
      />
      {file ? (
        <>
          <div className="w-8 h-8 rounded-full bg-green-600/20 flex items-center justify-center">
            <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-xs text-[#888] text-center">{file.name}</p>
        </>
      ) : (
        <>
          <svg className="w-6 h-6 text-[#444]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-[10px] text-[#444] tracking-wider">{label}</p>
          <p className="text-[9px] text-[#333]">JPG / PNG / WebP</p>
        </>
      )}
    </div>
  );

  return (
    <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-3xl p-6 lg:p-8 space-y-6">
      <div>
        <p className="text-[10px] tracking-[0.3em] text-[#333] font-bold mb-1">BODY ESTIMATION</p>
        <h3 className="text-lg font-black">体型パラメータ推定</h3>
        <p className="text-[11px] text-[#444] mt-1">
          全身写真から骨格比率を推定し、筋肉活動の精度を向上させます
        </p>
      </div>

      {/* 身長入力 */}
      <div className="flex items-center gap-4">
        <label className="text-xs text-[#555] tracking-wider w-16">身長</label>
        <input
          type="number" min={100} max={220} step={1}
          value={heightCm}
          onChange={e => setHeightCm(Number(e.target.value))}
          className="w-24 bg-[#111] border border-[#222] rounded-xl px-3 py-2 text-sm
            text-white font-mono focus:outline-none focus:border-[#444] transition-colors"
        />
        <span className="text-xs text-[#444]">cm</span>
      </div>

      {/* 写真アップロード */}
      <div className="flex gap-3">
        <ImageDropZone
          label="正面写真（必須）"
          file={frontFile}
          inputRef={frontRef}
          onChange={setFrontFile}
        />
        <ImageDropZone
          label="側面写真（任意）"
          file={sideFile}
          inputRef={sideRef}
          onChange={setSideFile}
        />
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-950/30 border border-red-900/30 rounded-xl px-4 py-2.5">
          {error}
        </p>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading || !frontFile}
        className="w-full py-3 rounded-2xl text-xs font-bold tracking-[0.2em]
          transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed
          bg-white text-black hover:bg-[#e0e0e0] active:scale-[0.99]"
      >
        {loading ? "推定中..." : "体型を推定する"}
      </button>

      {/* 結果表示 */}
      {result && (
        <div className="border-t border-[#111] pt-6 space-y-4">
          <p className="text-[10px] tracking-[0.2em] text-[#444] font-bold">RESULT</p>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "肩幅",     value: `${result.shoulder_width_cm} cm`, icon: "↔" },
              { label: "骨盤幅",   value: `${result.hip_width_cm} cm`,      icon: "↔" },
              { label: "上半身比", value: `${(result.torso_ratio * 100).toFixed(1)}%`, icon: "📐" },
              { label: "脚長比",   value: `${(result.leg_ratio * 100).toFixed(1)}%`,  icon: "📐" },
              { label: "体格スケール", value: `×${result.body_scale}`,        icon: "⚖" },
            ].map(({ label, value, icon }) => (
              <div key={label} className="bg-[#0f0f0f] border border-[#1a1a1a] rounded-2xl p-4">
                <p className="text-[10px] text-[#444] mb-1">{icon} {label}</p>
                <p className="text-white font-mono font-bold text-sm">{value}</p>
              </div>
            ))}
          </div>
          <p className="text-[9px] text-[#333] leading-relaxed">{result.note}</p>
        </div>
      )}
    </div>
  );
}
