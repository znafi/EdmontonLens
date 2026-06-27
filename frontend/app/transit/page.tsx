"use client";

import { useCallback, useEffect, useState } from "react";
import TransitPulseChart from "@/components/TransitPulseChart";
import DelayBarChart from "@/components/DelayBarChart";
import MLPredictionBadge from "@/components/MLPredictionBadge";
import { client, clsx } from "@/lib/api";
import type { PerformancePoint, StopDelay, TransitRoute } from "@/types";

const REFRESH_MS = 5 * 60 * 1000;

export default function TransitPage() {
  const [performance, setPerformance] = useState<PerformancePoint[]>([]);
  const [delays, setDelays] = useState<StopDelay[]>([]);
  const [routes, setRoutes] = useState<TransitRoute[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<string>("");
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const [perf, dly, rts] = await Promise.all([
        client.transit(),
        client.delays(),
        client.routes(),
      ]);
      setPerformance(perf);
      setDelays(dly);
      setRoutes(rts);
      if (!selectedRoute && rts.length > 0) setSelectedRoute(rts[0].route_id);
      setUpdatedAt(new Date());
    } catch {
      /* keep last good data */
    }
  }, [selectedRoute]);

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  const today = todayCityWide(performance);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Transit</h1>
          <p className="text-sm text-slate-500">
            ETS buses and LRT, refreshed every 5 minutes
            {updatedAt && ` · last updated ${updatedAt.toLocaleTimeString()}`}
          </p>
        </div>
        <OnTimeBadge value={today} />
      </div>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">
          How often buses ran on time this month (top 5 routes)
        </h2>
        <TransitPulseChart data={performance} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">
            Stops where buses are most often late
          </h2>
          <DelayBarChart data={delays} />
        </div>

        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">
            Delay risk for tomorrow morning
          </h2>
          <label className="mb-2 block text-sm text-slate-600">Pick a route</label>
          <select
            value={selectedRoute}
            onChange={(e) => setSelectedRoute(e.target.value)}
            className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {routes.map((r) => (
              <option key={r.route_id} value={r.route_id}>
                {r.route_short_name ?? r.route_id} - {r.route_long_name ?? ""}
              </option>
            ))}
          </select>
          {selectedRoute && <MLPredictionBadge routeId={selectedRoute} hour={8} day={0} />}
          <p className="mt-4 text-xs text-slate-400">
            This comes from a RandomForest model trained on 30 days of performance
            data. It&apos;s estimating Monday morning rush, 8am.
          </p>
        </div>
      </div>
    </div>
  );
}

function todayCityWide(perf: PerformancePoint[]): number | null {
  if (perf.length === 0) return null;
  const latest = perf.reduce((acc, p) => (p.service_date > acc ? p.service_date : acc), perf[0].service_date);
  const todays = perf.filter((p) => p.service_date === latest);
  if (todays.length === 0) return null;
  return todays.reduce((s, p) => s + p.on_time_rate, 0) / todays.length;
}

function OnTimeBadge({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <div className="rounded-xl bg-slate-100 px-6 py-4 text-slate-400">
        Nothing here yet. Run the pipeline to load data.
      </div>
    );
  }
  const pct = Math.round(value * 100);
  const tone =
    pct >= 80 ? "bg-green-50 text-green-700" : pct >= 65 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700";
  return (
    <div className={clsx("rounded-xl px-6 py-4 text-right", tone)}>
      <p className="text-xs font-medium uppercase tracking-wide">Buses running on time today</p>
      <p className="text-4xl font-bold">{pct}%</p>
    </div>
  );
}
