import { AnalyzeResult } from "@/types/analysis";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function analyzeVideo(
  file: File,
  exercise: string,
  targetAngle: number,
  mlMode: boolean = false,
  bodyScale: number = 1.0,
): Promise<AnalyzeResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("exercise", exercise);
  formData.append("target_angle", String(targetAngle));
  formData.append("ml_mode", String(mlMode));
  formData.append("body_scale", String(bodyScale));

  const res = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`サーバーエラー: ${res.status}${body ? ` — ${body}` : ""}`);
  }
  return res.json();
}

export type BodyEstimation = {
  shoulder_width_cm: number;
  hip_width_cm:      number;
  torso_ratio:       number;
  leg_ratio:         number;
  body_scale:        number;
  height_cm:         number;
  note:              string;
};

export async function estimateBody(
  frontImage: File,
  heightCm: number,
  sideImage?: File,
): Promise<BodyEstimation> {
  const formData = new FormData();
  formData.append("front_image", frontImage);
  formData.append("height_cm", String(heightCm));
  if (sideImage) formData.append("side_image", sideImage);

  const res = await fetch(`${API_URL}/estimate_body`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`体型推定エラー: ${res.status}${body ? ` — ${body}` : ""}`);
  }
  return res.json();
}
