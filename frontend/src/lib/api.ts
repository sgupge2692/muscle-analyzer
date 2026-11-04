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

// ── 認証API ────────────────────────────────────────────────

export type AuthToken = {
  access_token: string;
  token_type:   string;
  expires_in:   number;
};

export type UserProfile = {
  id:    string;
  email: string;
  name:  string;
};

export async function register(
  email: string,
  password: string,
  name: string = "",
): Promise<AuthToken> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail ?? `登録エラー: ${res.status}`);
  }
  return res.json();
}

export async function login(
  email: string,
  password: string,
): Promise<AuthToken> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail ?? `ログインエラー: ${res.status}`);
  }
  return res.json();
}

export async function getMe(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("認証が必要です");
  return res.json();
}

export async function refreshToken(token: string): Promise<AuthToken> {
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("トークン更新失敗");
  return res.json();
}

export async function changePassword(
  token: string,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const res = await fetch(`${API_URL}/auth/change-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password:     newPassword,
    }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail ?? "パスワード変更失敗");
  }
}

// トークンをlocalStorageで管理するユーティリティ
export const TokenStore = {
  get:    ()          => localStorage.getItem("ma_token"),
  set:    (t: string) => localStorage.setItem("ma_token", t),
  clear:  ()          => localStorage.removeItem("ma_token"),
  isValid: (token: string | null): boolean => {
    if (!token) return false;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.exp * 1000 > Date.now() + 60_000; // 1分の余裕
    } catch {
      return false;
    }
  },
};
