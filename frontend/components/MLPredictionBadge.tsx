"use client";

import { useEffect, useState } from "react";
import { client, clsx } from "@/lib/api";

interface Props {
  routeId: string;
  hour?: number;
  day?: number;
}

export default function MLPredictionBadge({ routeId, hour = 8, day = 0 }: Props) {
  const [prob, setProb] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!routeId) return;
    let cancelled = false;
    setLoading(true);
    client
      .predict(routeId, hour, day)
      .then((r) => {
        if (!cancelled) setProb(r.delay_probability);
      })
      .catch(() => {
        if (!cancelled) setProb(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [routeId, hour, day]);

  const pct = prob !== null ? Math.round(prob * 100) : null;
  const tone =
    pct === null
      ? "bg-slate-100 text-slate-500"
      : pct >= 70
        ? "bg-red-100 text-red-700"
        : pct >= 40
          ? "bg-amber-100 text-amber-700"
          : "bg-green-100 text-green-700";

  return (
    <div className={clsx("inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold", tone)}>
      <span className="h-2 w-2 rounded-full bg-current" />
      {loading
        ? "Checking the model..."
        : pct === null
          ? `Route ${routeId}: couldn't load a prediction`
          : `Route ${routeId}: ${pct}% chance of delays`}
    </div>
  );
}
