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

export type Landmark3D = {
  x: number;
  y: number;
  z: number;
};

export type FrameLandmarks3D = {
  frame: number;
  landmarks: Record<string, Landmark3D>;
};

export type EvidenceLevelInfo = {
  level: 0 | 1 | 2;
  label: string;
  source: string | null;
  note: string | null;
};

export type DeviationDiagnosisItem = {
  muscle: string;
  observed_flexion_deg: number;
  literature_flexion_deg: number;
  deviation_deg: number;
  severity: "normal" | "watch" | "fix";
  proposal: string | null;
  source: string | null;
  evidence: string;
};

export type VelocityLoss = {
  reference_rep: number;
  per_rep: { rep: number; velocity_loss_pct: number }[];
  final_loss_pct: number;
  definition: string;
  literature: string;
  note: string;
};

export type VelocityMetrics = {
  per_rep_velocities: {
    rep: number;
    mean_concentric_velocity_deg_per_frame: number;
    frames: number;
  }[];
  velocity_loss: VelocityLoss | null;
  form_filtered?: {
    excluded_reps: number[];
    velocity_loss: VelocityLoss | null;
    note: string;
  };
};

export type AnalyzeResult = {
  exercise: string;
  total_reps: number;
  activations: Record<string, ActivationMap>;
  form_feedback: Record<string, FormIssue[]>;
  ml_available: boolean;
  landmarks_3d?: FrameLandmarks3D[];  // world座標の時系列（3Dビューア用、オプショナル）
  deviation_diagnosis?: DeviationDiagnosisItem[];  // 文献理想曲線に対する逸脱診断
  evidence_levels?: Record<string, EvidenceLevelInfo>;  // 筋群ごとの文献検証状況
  velocity_metrics?: VelocityMetrics | null;  // velocity loss・フォーム妥当性フィルタ
};
