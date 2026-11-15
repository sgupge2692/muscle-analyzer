import Link from "next/link";

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#080808] text-white">
      <nav className="border-b border-white/[0.04] px-6 sm:px-8 py-5 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-sm font-bold tracking-[0.15em]">MUSCLE ANALYZER</span>
        </Link>
        <Link href="/" className="text-[10px] text-[#444] hover:text-white transition-colors tracking-wider">
          アプリへ戻る
        </Link>
      </nav>
      <article className="max-w-2xl mx-auto px-6 py-16 space-y-8">{children}</article>
    </div>
  );
}

