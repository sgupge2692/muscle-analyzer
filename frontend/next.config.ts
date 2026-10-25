import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // キャッシュ・パフォーマンス設定
  cacheComponents: true,
  partialPrefetching: true,

  // Turbopack設定（Next.js 16+）
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },

  // セキュリティヘッダー
  // ブラウザに「このページをどう扱うか」を指示する
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          // XSS攻撃対策：JavaScriptを注入されても実行させない
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          // クリックジャッキング対策：iframeに埋め込めなくする
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          // リファラ情報を制限（どこから来たかを外部サイトに知らせない）
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          // ブラウザの機能を制限（カメラ・マイクへの不正アクセスを防ぐ）
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
