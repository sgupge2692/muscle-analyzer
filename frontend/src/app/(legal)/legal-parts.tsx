export function LegalHeading({ children }: { children: React.ReactNode }) {
  return <h2 className="text-sm font-bold tracking-[0.2em] text-white mt-12">{children}</h2>;
}

export function LegalNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] text-[#555] border border-[#1a1a1a] rounded-xl px-4 py-3 bg-[#0a0a0a]">
      {children}
    </p>
  );
}
