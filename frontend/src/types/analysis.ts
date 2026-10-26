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

export type AnalyzeResult = {
  exercise: string;
  total_reps: number;
  activations: Record<string, ActivationMap>;
  form_feedback: Record<string, FormIssue[]>;
  ml_available: boolean;
  landmarks_3d: FrameLandmarks3D[];  // world座標の時系列（3Dビューア用）
};
