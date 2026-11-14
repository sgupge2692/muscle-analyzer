"use client";

import { useState } from "react";

const STORAGE_KEY = "ma_onboarded";

const SLIDES = [
  {
    title: "筋肉活動を、データで見る。",
    body: "筋トレ動画をアップロードするだけで、骨格検出・関節角度解析・筋肉活動推定を自動で実行します。まずは1種目、1〜3レップの動画から試してみてください。",
  },
  {
    title: "ヒートマップの色は信頼度つき",
    body: "各筋の推定値にはエビデンスレベルが付いています。「文献較正済み」は学術文献と定量一致を確認した筋、「文献値より導出」は文献データからの推定、「未検証」はモデル参考値です。濃い色ほど確度が高い値を示します。",
  },
  {
    title: "プライバシー",
    body: "アップロードされた動画は解析処理にのみ使用し、サーバーには保存されません。ログインすると解析結果の数値だけが履歴に保存され、後から振り返ることができます。動画自体は履歴に残りません。",
  },
];

export function OnboardingModal() {
  const [step, setStep] = useState<number | null>(() => {
    if (typeof window === "undefined" || localStorage.getItem(STORAGE_KEY)) return null;
    return 0;
  });
  if (step === null) return null;

  const slide = SLIDES[step];
  const last = step === SLIDES.length - 1;

  function close() {
    localStorage.setItem(STORAGE_KEY, "1");
    setStep(null);
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-[#0a0a0a] border border-[#1a1a1a] rounded-3xl p-8">
        <p className="text-[10px] font-bold tracking-[0.3em] text-red-500 mb-4">
          {step + 1} / {SLIDES.length}
        </p>
        <h3 className="text-lg font-bold text-white leading-snug mb-3">{slide.title}</h3>
        <p className="text-[#888] text-xs leading-relaxed mb-8">{slide.body}</p>

        <div className="flex gap-1 mb-6">
          {SLIDES.map((_, i) => (
            <div key={i}
              className={`h-[3px] flex-1 rounded-full ${i <= step ? "bg-red-600" : "bg-[#1a1a1a]"}`} />
          ))}
        </div>

        <div className="flex items-center justify-between">
          <button onClick={close}
            className="text-[10px] text-[#444] hover:text-[#666] transition-colors">
            スキップ
          </button>
          <button
            onClick={() => (last ? close() : setStep(step + 1))}
            className="bg-red-600 hover:bg-red-500 text-white text-xs font-bold
              px-6 py-2.5 rounded-xl transition-colors tracking-wider"
          >
            {last ? "始める" : "次へ"}
          </button>
        </div>
      </div>
    </div>
  );
}
