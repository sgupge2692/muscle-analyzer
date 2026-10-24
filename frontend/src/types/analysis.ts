export type ActivationMap = Record<string, number>;

export type FormIssue = {
  joint: string;
  actual_deg: number;
  ideal_range: [number, number];
  deviation_deg: number;
  direction: "too_small" | "too_large";
  severity: "warning" | "error";
  message: string;
};

export type AnalyzeResult = {
  exercise: string;
  total_reps: number;
  activations: Record<string, ActivationMap>;
  form_feedback: Record<string, FormIssue[]>;  // ← 追加
  ml_available: boolean;
};
