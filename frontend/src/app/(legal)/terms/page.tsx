import type { Metadata } from "next";
import { LegalHeading, LegalNote } from "../legal-parts";

export const metadata: Metadata = {
  title: "利用規約",
};

export default function TermsPage() {
  return (
    <>
      <header className="space-y-2">
        <h1 className="text-lg font-bold tracking-wide">利用規約</h1>
        <p className="text-[10px] text-[#555]">制定日: 2026年11月15日</p>
      </header>

      <LegalNote>
        この文面はドラフトであり，公開前の弁護士レビューは未実施です。提供者側の名称・連絡先は確定後に補う必要があります。
      </LegalNote>

      <section className="space-y-3">
        <LegalHeading>第1条（適用）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          本規約は，Muscle Analyzer（以下「本サービス」）の利用条件を定めるものです。本サービスを利用するすべての方（以下「利用者」）は，本サービスを利用した時点で本規約に同意したものとみなされます。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第2条（サービスの性質）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          本サービスは，トレーニング動画の骨格検出・関節角度解析に基づき，筋肉の活動度を推定して可視化するフィットネス支援ツールです。
        </p>
        <p className="text-xs text-[#888] leading-relaxed">
          本サービスは医療機器ではなく，医学的な診断・治療・リハビリテーションの代替となるものではありません。筋活動の推定値は文献に基づく較正を施した統計的な推定であり，生体の実測値を保証するものではありません。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第3条（免責・責任制限）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          トレーニングの実施とその強度・方法の判断は，利用者自身の責任において行うものとします。本サービスの解析結果を参考にトレーニングを行い，利用者に生じた怪我・健康被害・その他の損害について，提供者は故意または重過失がある場合を除き責任を負いません。
        </p>
        <p className="text-xs text-[#888] leading-relaxed">
          既往歴・痛み・怪我のある方は，本サービスを利用せず，医師や専門家に相談してください。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第4条（アカウント）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          解析履歴の保存等の一部機能は，アカウント登録（メールアドレスとパスワードの登録）をした利用者のみが利用できます。登録情報の管理は利用者が行い，第三者に貸与・譲渡してはなりません。
        </p>
        <p className="text-xs text-[#888] leading-relaxed">
          利用者はいつでもアカウントの削除を申請できます。削除方法はプライバシーポリシーに定めます。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第5条（利用者が投稿するデータ）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          利用者が解析のためにアップロードする動画・画像は，解析処理にのみ使用するためのものです。利用者は，アップロードする映像について，その撮影者・被写体本人から適切な同意を得ていることを表明し，保証します。
        </p>
        <p className="text-xs text-[#888] leading-relaxed">
          アップロードされた動画ファイルは解析完了後に破棄されます。解析履歴としてサーバーに保存されるのは，解析結果の数値（筋活動・関節角度等）のみです。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第6条（禁止行為）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          次の行為を禁止します。同意なく第三者の映像をアップロードすること／本サービスの解析結果を，医学的効果・治療効果の主張に利用すること／提供者の意図しない方法による大量アクセス・サーバー負荷の掛け込み／その他，法令または公序良俗に反する行為。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第7条（サービスの変更・停止）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          提供者は，予告なく本サービスの内容を変更し，または提供を終了することがあります。研究目的の実証実験として提供している期間においては，機能・精度・可用性について予告なく変動する場合があります。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第8条（規約の変更）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          提供者は，本規約を変更できるものとします。変更後の規約は，本ページに掲載した時点から効力を生じるものとします。
        </p>
      </section>

      <section className="space-y-3">
        <LegalHeading>第9条（準拠法・管轄）</LegalHeading>
        <p className="text-xs text-[#888] leading-relaxed">
          本規約は日本法に準拠し，本サービスの利用に関して生じた紛争については，提供者の所在地を管轄する裁判所を第一審の専属的合意管轄とします。
        </p>
      </section>

      <LegalNote>
        課金（サブスク等）の導入時には，特定商取引法に基づく表示（解約手続き・返金規定）を本規約に追加する必要があります。現時点では有料プランは存在しません。
      </LegalNote>
    </>
  );
}
