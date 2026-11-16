import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Muscle Analyzer — 筋肉活動を、データで見る。",
    template: "%s | Muscle Analyzer",
  },
  description:
    "筋トレ動画をアップロードするだけで、骨格検出・関節角度解析・文献較正済みの筋肉活動推定を自動実行。エビデンスレベルつきのヒートマップで信頼できるデータを確認できます。",
  openGraph: {
    title: "Muscle Analyzer — 筋肉活動を、データで見る。",
    description:
      "文献較正済みの筋肉活動推定とフォーム診断。動画をアップロードするだけで解析します。",
    type: "website",
    locale: "ja_JP",
    siteName: "Muscle Analyzer",
  },
  twitter: {
    card: "summary_large_image",
    title: "Muscle Analyzer — 筋肉活動を、データで見る。",
    description: "文献較正済みの筋肉活動推定とフォーム診断。",
  },
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#080808",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ja"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
