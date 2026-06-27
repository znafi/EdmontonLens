"use client";

import { useEffect, useState } from "react";

interface Props {
  label?: string;
  className?: string;
}

/**
 * Friendly loading indicator. After a few seconds it explains that the free
 * backend may be waking up, so a long first load reads as intentional rather
 * than broken.
 */
export default function LoadingState({ label = "Loading...", className = "" }: Props) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setSlow(true), 4000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-10 text-center text-slate-400 ${className}`}
    >
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-brand" />
      <p className="text-sm">{label}</p>
      {slow && (
        <p className="max-w-xs text-xs text-slate-400">
          The server goes to sleep when it&apos;s not being used, so the first load can
          take up to a minute. Hang tight, this only happens once.
        </p>
      )}
    </div>
  );
}
