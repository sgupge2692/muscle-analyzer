export function RepAlert({ detected, declared }: { detected: number; declared: number | null }) {
  if (!declared || detected >= declared) return null;
  const missed = declared - detected;
  return (
    <div className="flex items-start gap-3 bg-[#1a0f0f] border border-red-900/40 rounded-2xl p-4 mb-6">
      <svg className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
      <div>
        <p className="text-red-400 text-sm font-medium">
          {missed}回が目標深度に届いていない可能性があります
        </p>
        <p className="text-[#555] text-xs mt-1">
          申告: {declared}回 / 検出: {detected}回 ─ 膝の角度が目標に届かなかったレップはカウントされていません
        </p>
      </div>
    </div>
  );
}
