import type { NextConfig } from "next";

// API オリジン（Cookie送受信・fetch先）。デフォルトはローカル開発用
const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Content-Security-Policy（S9）
// - script-src の 'unsafe-inline'/'unsafe-eval' は Next.js のハイドレーションに必要。
//   緩和措置であり、nonce ベース CSP への移行は残課題（open_questions Q12）
// - MediaPipe クライアント側推論プロトタイプ（/lab）のため CDN・WASM を許可
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self' ${API_ORIGIN} https://storage.googleapis.com`,
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
  "form-action 'self'",
].join("; ");

const nextConfig: NextConfig = {
  // セキュリティヘッダー
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options",  value: "nosniff" },
          { key: "X-Frame-Options",          value: "DENY" },
          { key: "Referrer-Policy",          value: "strict-origin-when-cross-origin" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          {
            // camera=(self): リアルタイム解析・クライアント側推論プロトタイプで
            // カメラAPIを使うため self を許可（() だと getUserMedia が拒否される）
            key: "Permissions-Policy",
            value: "camera=(self), microphone=(), geolocation=()",
          },
          { key: "Content-Security-Policy",  value: CSP },
        ],
      },
    ];
  },
};

export default nextConfig;
