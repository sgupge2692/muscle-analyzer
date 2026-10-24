import { AnalyzeResult } from "@/types/analysis";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function analyzeVideo(
  file: File,
  exercise: string,
  targetAngle: number,
  mlMode: boolean = false,
): Promise<AnalyzeResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("exercise", exercise);
  formData.append("target_angle", String(targetAngle));
  formData.append("ml_mode", String(mlMode));

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
