export type ActivationMap = Record<string, number>;

export type AnalyzeResult = {
  exercise: string;
  total_reps: number;
  activations: Record<string, ActivationMap>;
};
