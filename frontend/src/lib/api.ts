import { AnalyzeResult } from "@/types/analysis";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function analyzeVideo(
  file: File,
  exercise: string,
  targetAngle: number
): Promise<AnalyzeResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("exercise", exercise);
  formData.append("target_angle", String(targetAngle));

  const res = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) throw new Error(`サーバーエラー: ${res.status}`);
  return res.json();
}
