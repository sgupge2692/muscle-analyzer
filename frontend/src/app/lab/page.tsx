import type { Metadata } from "next";
import ClientInferenceLab from "@/components/ClientInferenceLab";

export const metadata: Metadata = {
  title: "クライアント側推論プロトタイプ",
};

export default function LabPage() {
  return (
    <div className="min-h-screen bg-[#080808] text-white px-6 py-12">
      <div className="max-w-2xl mx-auto space-y-6">
        <header className="space-y-2">
          <h1 className="text-lg font-bold tracking-wide">
            クライアント側推論プロトタイプ（市場化準備レポート 優先アクション4）
          </h1>
          <p className="text-xs text-[#888] leading-relaxed">
            リアルタイム解析の骨格検出を，サーバーではなくブラウザ内（MediaPipe Tasks Vision JS）で実行する可行性の検証用ページです。カメラ映像は端末内でのみ処理され，サーバーには送信されません。
          </p>
        </header>
        <div className="text-[10px] text-[#555] border border-[#1a1a1a] rounded-xl px-4 py-3 bg-[#0a0a0a] leading-relaxed">
          プロトタイプ検証用。関節角度の計算方式はサーバー側（websocket_stream.py の2Dベクトル内積法）と同一に揃えていますが，完全な実運用機能ではありません。正式実装時には，精度比較（サーバー側との一致性）・セルフホスト化（WASM/モデルのCDN依存の解消）・エビデンスレベルの統合が残課題です。
        </div>
        <ClientInferenceLab />
      </div>
    </div>
  );
}
