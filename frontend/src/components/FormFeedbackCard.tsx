import { FormIssue } from "@/types/analysis";

const JOINT_NAMES_JA: Record<string, string> = {
  right_knee:     "右膝",
  left_knee:      "左膝",
  right_hip:      "右股関節",
  left_hip:       "左股関節",
  spine_tilt:     "体幹",
  right_elbow:    "右肘",
  left_elbow:     "左肘",
  right_shoulder: "右肩",
  left_shoulder:  "左肩",
};

function IssueRow({ issue }: { issue: FormIssue }) {
  const isError = issue.severity === "error";
  const accentColor = isError ? "text-red-400" : "text-yellow-400";
  const borderColor = isError ? "border-red-900/40" : "border-yellow-900/30";
  const bgColor     = isError ? "bg-red-950/10"     : "bg-yellow-950/10";
  const dotColor    = isError ? "bg-red-500"         : "bg-yellow-500";

  return (
    <div className={`flex items-start gap-3 rounded-xl p-3.5 border ${bgColor} ${borderColor}`}>
      {/* アイコン */}
      <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${dotColor}`} />
      <div className="flex-1 min-w-0">
        {/* ヘッダー行 */}
        <div className="flex items-center justify-between gap-4 mb-1">
          <span className={`text-xs font-bold ${accentColor}`}>
            {JOINT_NAMES_JA[issue.joint] ?? issue.joint}
          </span>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span className="text-[10px] text-[#444] font-mono">
              実測 {issue.actual_deg}°
            </span>
            <span className="text-[10px] text-[#333]">→</span>
            <span className="text-[10px] text-[#555] font-mono">
              理想 {issue.ideal_range[0]}°〜{issue.ideal_range[1]}°
            </span>
          </div>
        </div>
        {/* メッセージ */}
        <p className="text-xs text-[#888] leading-relaxed">{issue.message}</p>
        {/* 角度バー */}
        <div className="mt-2.5 relative h-1 bg-[#141414] rounded-full overflow-visible">
          {/* 理想範囲ゾーン */}
          <div
            className="absolute h-full bg-green-900/40 rounded-full"
            style={{
              left: `${(issue.ideal_range[0] / 180) * 100}%`,
              width: `${((issue.ideal_range[1] - issue.ideal_range[0]) / 180) * 100}%`,
            }}
          />
          {/* 実測値マーカー */}
          <div
            className={`absolute w-2 h-2 rounded-full -top-0.5 -translate-x-1/2 ${dotColor}`}
            style={{ left: `${Math.min((issue.actual_deg / 180) * 100, 100)}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-[#222]">0°</span>
          <span className="text-[9px] text-[#222]">180°</span>
        </div>
      </div>
    </div>
  );
}

type Props = {
  repKey: string;
  issues: FormIssue[];
};

export function FormFeedbackCard({ repKey, issues }: Props) {
  if (!issues || issues.length === 0) {
    return (
      <div className="flex items-center gap-2.5 bg-[#0a120a] border border-green-900/30 rounded-2xl p-4">
        <div className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
        <p className="text-xs text-green-400 font-medium">
          {repKey.replace("_", " ").toUpperCase()} — フォームに問題は検出されませんでした
        </p>
      </div>
    );
  }

  const errors   = issues.filter(i => i.severity === "error");
  const warnings = issues.filter(i => i.severity === "warning");

  return (
    <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-2xl overflow-hidden">
      {/* ヘッダー */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#141414]">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold tracking-[0.25em] text-[#666666]">
            FORM CHECK — {repKey.replace("_", " ").toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {errors.length > 0 && (
            <span className="flex items-center gap-1.5 text-[10px] text-red-400">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" />
              エラー {errors.length}件
            </span>
          )}
          {warnings.length > 0 && (
            <span className="flex items-center gap-1.5 text-[10px] text-yellow-400">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 inline-block" />
              警告 {warnings.length}件
            </span>
          )}
        </div>
      </div>
      {/* 問題リスト */}
      <div className="p-4 space-y-2.5">
        {/* エラー優先で表示 */}
        {[...errors, ...warnings].map((issue, i) => (
          <IssueRow key={`${issue.joint}-${i}`} issue={issue} />
        ))}
      </div>
    </div>
  );
}
