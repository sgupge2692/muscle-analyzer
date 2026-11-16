"use client";

import { useEffect, useState } from "react";
import {
  HistoryEntry,
  getHistory,
  deleteHistory,
  TokenStore,
} from "@/lib/api";

const EXERCISE_JA: Record<string, string> = {
  Squats:            "スクワット",
  Deadlift:          "デッドリフト",
  Romanian_Deadlift: "ルーマニアンDL",
  Lunges:            "ランジ",
  Push_ups:          "プッシュアップ",
  Bench_Press:       "ベンチプレス",
  Squat_Hold:        "スクワットホールド",
};

const EVIDENCE_JA: Record<number, string> = {
  2: "文献較正済み",
  1: "文献値より導出",
  0: "未検証",
};

function fmtDate(unix: number): string {
  return new Date(unix * 1000).toLocaleString("ja-JP", {
    year:  "numeric",
    month: "2-digit",
    day:   "2-digit",
    hour:  "2-digit",
    minute: "2-digit",
  });
}

function topMuscles(entry: HistoryEntry, n = 3): [string, number][] {
  return Object.entries(entry.muscles)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}

export function HistoryPanel({ refreshKey }: { refreshKey: number }) {
  const [entries, setEntries]     = useState<HistoryEntry[] | null>(null);
  const [error, setError]         = useState<string | null>(null);
  const [expanded, setExpanded]   = useState<string | null>(null);
  const [deleting, setDeleting]   = useState<string | null>(null);

  useEffect(() => {
    const token = TokenStore.get();
    if (!token || !TokenStore.isValid(token)) {
      setEntries(null);
      return;
    }
    let alive = true;
    getHistory(token)
      .then((list) => { if (alive) setEntries(list); })
      .catch((e) => { if (alive) setError(String(e)); });
    return () => { alive = false; };
  }, [refreshKey]);

  async function handleDelete(id: string) {
    const token = TokenStore.get();
    if (!token) return;
    setDeleting(id);
    try {
      await deleteHistory(token, id);
      setEntries((prev) => prev?.filter((e) => e.id !== id) ?? null);
    } catch (e) {
      setError(String(e));
    } finally {
      setDeleting(null);
    }
  }

  if (!entries && !error) return null;
  if (error) {
    return (
      <p className="text-xs text-[#555] px-4 max-w-2xl mx-auto mt-4">
        履歴の取得に失敗しました（{error}）
      </p>
    );
  }

  return (
    <section className="w-full max-w-2xl mx-auto px-4 mt-16 mb-24">
      <div className="flex items-baseline justify-between mb-5">
        <h2 className="text-[11px] font-bold tracking-[0.25em] text-[#666]">
          解析履歴
        </h2>
        <span className="text-[10px] text-[#2a2a2a]">{entries!.length} 件</span>
      </div>

      {entries!.length === 0 ? (
        <p className="text-xs text-[#444] py-6">
          まだ履歴がありません。動画を解析すると、ログイン中のアカウントに自動保存されます。
        </p>
      ) : (
        <ul className="space-y-2">
          {entries!.map((entry) => {
            const top = topMuscles(entry);
            return (
              <li key={entry.id}
                className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-2xl overflow-hidden">
                <button
                  onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                  className="w-full flex items-center justify-between px-4 py-3.5 text-left
                    hover:bg-[#0f0f0f] transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-white font-medium">
                      {EXERCISE_JA[entry.exercise] ?? entry.exercise}
                      <span className="text-[#555] text-xs ml-3">{entry.total_reps} レップ</span>
                    </p>
                    <p className="text-[10px] text-[#444] mt-1">{fmtDate(entry.saved_at)}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-4">
                    {top.slice(0, 2).map(([name, v]) => (
                      <span key={name}
                        className="text-[10px] text-[#666] bg-[#111] border border-[#1a1a1a]
                          px-2 py-1 rounded-lg whitespace-nowrap">
                        {name} {(v * 100).toFixed(0)}%
                      </span>
                    ))}
                  </div>
                </button>

                {expanded === entry.id && (
                  <div className="border-t border-[#1a1a1a] px-4 py-4 space-y-3">
                    <div className="grid grid-cols-1 gap-1.5">
                      {top.map(([name, v]) => (
                        <div key={name} className="flex items-center gap-3">
                          <span className="text-[11px] text-[#888] w-32 truncate">{name}</span>
                          <div className="flex-1 h-[4px] bg-[#111] rounded-full overflow-hidden">
                            <div className="h-full bg-red-600/70 rounded-full"
                              style={{ width: `${Math.min(100, v * 100)}%` }} />
                          </div>
                          <span className="text-[11px] font-mono text-[#666] w-12 text-right">
                            {(v * 100).toFixed(1)}%
                          </span>
                          {entry.evidence_levels[name] !== undefined && (
                            <span className="text-[9px] text-[#444] border border-[#1a1a1a] px-1.5 py-0.5 rounded">
                              {EVIDENCE_JA[entry.evidence_levels[name]] ?? "—"}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="pt-2 border-t border-[#111] flex justify-end">
                      <button
                        onClick={() => handleDelete(entry.id)}
                        disabled={deleting === entry.id}
                        className="text-[10px] text-[#444] hover:text-red-500 transition-colors"
                      >
                        {deleting === entry.id ? "削除中..." : "この履歴を削除"}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
