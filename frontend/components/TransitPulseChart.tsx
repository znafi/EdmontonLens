"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PerformancePoint } from "@/types";

const COLORS = ["#1d4ed8", "#16a34a", "#ea580c", "#9333ea", "#0891b2"];

interface Props {
  data: PerformancePoint[];
}

// Pivot the flat performance points into one series per route, by date.
function pivot(data: PerformancePoint[]) {
  const routeTotals = new Map<string, number>();
  data.forEach((d) => routeTotals.set(d.route_id, (routeTotals.get(d.route_id) ?? 0) + 1));
  const topRoutes = [...routeTotals.keys()].slice(0, 5);

  const byDate = new Map<string, Record<string, number | string>>();
  data.forEach((d) => {
    if (!topRoutes.includes(d.route_id)) return;
    const row = byDate.get(d.service_date) ?? { date: d.service_date };
    row[d.route_id] = Math.round(d.on_time_rate * 100);
    byDate.set(d.service_date, row);
  });

  const rows = [...byDate.values()].sort((a, b) =>
    String(a.date).localeCompare(String(b.date)),
  );
  return { rows, topRoutes };
}

export default function TransitPulseChart({ data }: Props) {
  const { rows, topRoutes } = pivot(data);

  if (rows.length === 0) {
    return <p className="text-sm text-slate-500">No performance data yet. Run the ETL pipeline.</p>;
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
          <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v) => `${v}%`} />
          <Legend />
          {topRoutes.map((route, i) => (
            <Line
              key={route}
              type="monotone"
              dataKey={route}
              name={`Route ${route}`}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
