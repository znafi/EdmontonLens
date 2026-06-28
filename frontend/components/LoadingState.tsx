"use client";

import { useEffect, useState } from "react";

interface Props {
  label?: string;
  className?: string;
  /** Rough cold-start estimate in seconds, used for the countdown. */
  estimateSeconds?: number;
}

/**
 * Friendly loading indicator. After a couple of seconds it reveals a progress
 * bar and an estimated time remaining, so a long first load (the free backend
 * waking up) reads as intentional progress rather than a frozen screen.
 */
export default function LoadingState({
  label = "Loading...",
  className = "",
  estimateSeconds = 55,
}: Props) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const slow = elapsed >= 2;
  const remaining = Math.max(0, estimateSeconds - elapsed);
  // Cap the bar below 100% so it never looks "done" before the data arrives.
  const progress = Math.min(96, Math.round((elapsed / estimateSeconds) * 100));

  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-10 text-center text-slate-400 ${className}`}
    >
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-brand" />
      <p className="text-sm">{label}</p>

      {slow && (
        <div className="flex w-full max-w-xs flex-col items-center gap-2">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-brand transition-all duration-1000 ease-linear"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs font-medium text-slate-500">
            {remaining > 0
              ? `About ${remaining}s remaining`
              : "Almost there, finishing up..."}
          </p>
          <p className="max-w-xs text-xs text-slate-400">
            The server sleeps when it&apos;s idle, so the first load can take up to a
            minute. This only happens once.
          </p>
        </div>
      )}
    </div>
  );
}
