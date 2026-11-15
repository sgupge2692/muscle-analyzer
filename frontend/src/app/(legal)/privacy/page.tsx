import type { Metadata } from "next";
import { LegalHeading, LegalNote } from "../legal-parts";

export const metadata: Metadata = {
  title: "プライバシーポリシー",
};

export default function PrivacyPage() {
  return (
    <>
      <header className="space-y-2">
        <h1 className="text-lg font-bold tracking-wide">プライバシーポリシー</h1>
        <p className="text-[10px] text-[#555]">制定日: 2026年11月15日</p>
      </header>

      <LegalNote>
        この文面はドラフトであり，公開前の弁護士レビューは未実施です。外国国際搬送（個人情報保護法第28条）の届出・同意取得フローの要否は確定後に確認する必要があります。
      </LegalNote>

      <section className="space-y-3">
        <LegalHeading>1. 個人情報の管理者</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          本サービスで取得する個人情報の管理者は，本サービスの提供者です。連絡先は本ページ末尾に記載します。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>2. 取得する情報</LegalHeading>
        <ul className="text-xs text-[#888] leading-relaxed list-disc pl-5 space-y-1.5">
          <li>アカウント情報: メールアドレス，パスワード（不可逆ハッシュ化して保存）</li>
          <li>解析履歴: 解析の入力条件（種目・回数等）と解析結果の数値（筋活動推定値・関節角度・診断メッセージ等）</li>
          <li>動画ファイル: 解析のために一時的にサーバーへ送信されますが，解析処理完了後はただちに削除され，保存されません</li>
          <li>リアルタイム解析: カメラ映像をフレーム画像に変換して解析処理へ送ります。フレームは解析にのみ使用し，永続保存しません</li>
          <li>体型推定（任意入力）: 肩幅・身長等の入力値。解析精度の向上にのみ使用します</li>
        </ul>
      </section>

      <section className="space-y-3">
        <LegalHeading>3. 利用目的</LegalHeading>
        <ul className="text-xs text-[#888] leading-relaxed list-disc pl-5 space-y-1.5">
          <li>トレーニング動画の解析と，その結果の表示・履歴保存のため</li>
          <li>アカウントの認証・管理のため</li>
          <li>不正利用・サーバーへの攻撃の検知と防御のため（IPアドレス等）</li>
          <li>本サービスの品質改善・研究のため（個人を特定できない統計値に加工した場合を含む）</li>
        </ul>
      </section>

      <section className="space-y-3">
        <LegalHeading>4. 第三者提供・外部委託</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          本サービスは，インフラの一部を外部サービスに委託しています。委託に伴い，利用者情報が国外（アメリカ合衆国）のサーバーに保存・処理される場合があります。
        </p>
        <ul className="text-xs text-[#888] leading-relaxed list-disc pl-5 space-y-1.5">
          <li>アプリ本体・APIホスティング: Vercel, Inc.（米国）／Railway Technologies, Inc.（米国）</li>
          <li>アカウント情報の保存: Supabase, Inc.（米国）※本サービスのデータベース構成による</li>
        </ul>
        <p className="text-xs text-[#888] leading-relaxed">
          上記を除き，本人の同意なく個人情報を第三者に提供することはありません。法令に基づく場合を除きます。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>5. 保存期間・削除</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          解析履歴は，利用者がアカウントを保持している間，利用者の便宜のために保存します。
        </p>
        <p className="text-xs text-[#888] leading-relaxed">
          利用者は，アプリ内のアカウント削除操作により，アカウント情報および関連する解析履歴の削除を請求できます。削除請求に基づくデータの消去は，法令が保存を義務付ける場合を除き，遅滞なく行います。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>6. 安全管理措置</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          パスワードは不可逆なハッシュ関数で保存し，通信は暗号化（HTTPS/TLS）します。認証トークンは期限付きのものを利用し，取り扱いに関する規程に従い管理します。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>7. Cookie・端末情報の利用</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          本サービスはログイン状態の維持のため，ブラウザのローカルストレージに認証トークンを保存します。広告目的のトラッキングCookieは使用していません。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>8. 開示・訂正・利用停止等の請求</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          利用者は，個人情報保護法に基づき，保有個人データの開示・訂正・削除・利用停止の請求を行えます。請求は本ページ末尾の連絡先までご連絡ください。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>9. ポリシーの変更</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          本ポリシーは予告なく変更されることがあります。重要な変更については，本ページへの掲載によりお知らせします。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>10. お問い合わせ</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          個人情報の取り扱いに関する連絡先は，確定後に記載します。
        </p>
      </section>
    </>
  );
}
