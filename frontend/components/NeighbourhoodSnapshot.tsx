"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
import { client } from "@/lib/api";
import LoadingState from "@/components/LoadingState";
import type { NeighbourhoodSnapshot as Snapshot, TrendPoint } from "@/types";

interface Props {
  neighbourhoodId: string | null;
}

export default function NeighbourhoodSnapshot({ neighbourhoodId }: Props) {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!neighbourhoodId) return;
    setLoading(true);
    Promise.all([client.snapshot(neighbourhoodId), client.trend(neighbourhoodId)])
      .then(([s, t]) => {
        setSnap(s);
        setTrend([...t].reverse());
      })
      .catch(() => {
        setSnap(null);
        setTrend([]);
      })
      .finally(() => setLoading(false));
  }, [neighbourhoodId]);

  if (!neighbourhoodId) {
    return (
      <div className="grid h-full place-items-center text-center text-slate-400">
        <p>Tap a neighbourhood on the map and you&apos;ll see the numbers here.</p>
      </div>
    );
  }

  if (loading || !snap) {
    return (
      <div className="grid h-full place-items-center">
        <LoadingState label="Grabbing the numbers..." />
      </div>
    );
  }

  const score = snap.overall_score ?? 0;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">
          {snap.neighbourhood_name ?? snap.neighbourhood_id}
        </h2>
        <p className="text-sm text-slate-500">Snapshot from {snap.snapshot_date ?? "today"}</p>
      </div>

      <div className="flex items-center gap-6 rounded-xl border border-slate-200 bg-white p-5">
        <ProgressRing value={score} max={10} />
        <div>
          <p className="kpi-label">Overall score</p>
          <p className="kpi-value">{score.toFixed(1)}/10</p>
          <p className="text-sm text-slate-500">
            Transit {snap.transit_score?.toFixed(1) ?? "-"} · Parks{" "}
            {snap.park_score?.toFixed(1) ?? "-"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <KpiCard label="Bus stops nearby" value={snap.transit_stop_count ?? 0} />
        <KpiCard
          label="Buses running on time"
          value={`${Math.round((snap.avg_route_on_time ?? 0) * 100)}%`}
        />
        <KpiCard label="Parks in this area" value={snap.park_count ?? 0} />
        <KpiCard
          label="Total green space"
          value={`${Math.round((snap.total_park_area_sqm ?? 0) / 1000)}k m\u00B2`}
        />
        <KpiCard label="Waste pickups per month" value={snap.waste_pickup_days ?? 0} />
        <KpiCard label="Parks score" value={(snap.park_score ?? 0).toFixed(1)} />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <p className="kpi-label mb-2">How the transit score has changed over the last year</p>
        {trend.length > 0 ? (
          <div className="h-24 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#1d4ed8" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#1d4ed8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="snapshot_date" hide />
                <Tooltip formatter={(v) => `${v}`} />
                <Area
                  type="monotone"
                  dataKey="transit_score"
                  stroke="#1d4ed8"
                  fill="url(#spark)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-slate-400">Not enough history yet. Check back after more pipeline runs.</p>
        )}
      </div>
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="kpi-label">{label}</p>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

function ProgressRing({ value, max }: { value: number; max: number }) {
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(1, value / max);
  const offset = circumference * (1 - pct);
  const color = value >= 7 ? "#15803d" : value >= 4 ? "#eab308" : "#dc2626";
  return (
    <svg width="88" height="88" viewBox="0 0 88 88">
      <circle cx="44" cy="44" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="8" />
      <circle
        cx="44"
        cy="44"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 44 44)"
      />
      <text x="44" y="49" textAnchor="middle" className="fill-slate-900 text-lg font-bold">
        {value.toFixed(1)}
      </text>
    </svg>
  );
}
