"use client";
import { useState } from "react";
import { login, register, AuthToken, TokenStore } from "@/lib/api";

type Mode = "login" | "register";

type Props = {
  onSuccess: (token: AuthToken) => void;
};

export function AuthModal({ onSuccess }: Props) {
  const [mode,     setMode]     = useState<Mode>("login");
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [name,     setName]     = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!email || !password) { setError("メールアドレスとパスワードを入力してください"); return; }
    setLoading(true);
    setError(null);
    try {
      const token = mode === "login"
        ? await login(email, password)
        : await register(email, password, name);
      TokenStore.set(token.access_token);
      onSuccess(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-3xl p-8 w-full max-w-md mx-auto space-y-6">
      {/* タブ */}
      <div className="flex bg-[#080808] border border-[#1a1a1a] rounded-2xl p-1">
        {(["login", "register"] as const).map(m => (
          <button key={m} onClick={() => { setMode(m); setError(null); }}
            className={`flex-1 py-2 rounded-xl text-xs font-bold tracking-[0.15em] transition-all
              ${mode === m ? "bg-[#1a1a1a] text-white" : "text-[#444] hover:text-[#666]"}`}>
            {m === "login" ? "ログイン" : "新規登録"}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {mode === "register" && (
          <div>
            <label className="text-[10px] text-[#555] tracking-wider block mb-1.5">名前（任意）</label>
            <input
              type="text" value={name} onChange={e => setName(e.target.value)}
              placeholder="田中 太郎"
              className="w-full bg-[#111] border border-[#222] rounded-xl px-4 py-3 text-sm
                text-white placeholder:text-[#333] focus:outline-none focus:border-[#444] transition-colors"
            />
          </div>
        )}

        <div>
          <label className="text-[10px] text-[#555] tracking-wider block mb-1.5">メールアドレス</label>
          <input
            type="email" value={email} onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            onKeyDown={e => e.key === "Enter" && handleSubmit()}
            className="w-full bg-[#111] border border-[#222] rounded-xl px-4 py-3 text-sm
              text-white placeholder:text-[#333] focus:outline-none focus:border-[#444] transition-colors"
          />
        </div>

        <div>
          <label className="text-[10px] text-[#555] tracking-wider block mb-1.5">パスワード</label>
          <input
            type="password" value={password} onChange={e => setPassword(e.target.value)}
            placeholder={mode === "register" ? "8文字以上、英数字を含む" : "••••••••"}
            onKeyDown={e => e.key === "Enter" && handleSubmit()}
            className="w-full bg-[#111] border border-[#222] rounded-xl px-4 py-3 text-sm
              text-white placeholder:text-[#333] focus:outline-none focus:border-[#444] transition-colors"
          />
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-950/30 border border-red-900/30 rounded-xl px-4 py-2.5">
          {error}
        </p>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full py-3 rounded-2xl bg-white text-black text-xs font-bold
          tracking-[0.2em] hover:bg-[#e0e0e0] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? "処理中..." : mode === "login" ? "ログイン" : "アカウントを作成"}
      </button>

      <p className="text-[10px] text-[#333] text-center">
        パスワードはbcryptで安全にハッシュ化されます
      </p>
    </div>
  );
}
