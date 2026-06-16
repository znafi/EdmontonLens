"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StopDelay } from "@/types";

interface Props {
  data: StopDelay[];
}

function colorFor(mins: number): string {
  if (mins >= 12) return "#dc2626";
  if (mins >= 7) return "#ea580c";
  return "#f59e0b";
}

function shortLabel(name: string | null | undefined, id: string): string {
  const raw = (name && name.trim()) || id;
  return raw.length > 22 ? raw.slice(0, 21) + "\u2026" : raw;
}

export default function DelayBarChart({ data }: Props) {
  const rows = [...data]
    .sort((a, b) => b.avg_delay_mins - a.avg_delay_mins)
    .slice(0, 10)
    .map((d) => ({
      stop: shortLabel(d.stop_name, d.stop_id),
      full: d.stop_name ?? d.stop_id,
      delay: Math.round(d.avg_delay_mins * 10) / 10,
    }));

  if (rows.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No delay data here yet. Run the pipeline to load some.
      </p>
    );
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis type="number" unit="m" tick={{ fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="stop"
            tick={{ fontSize: 11 }}
            width={150}
          />
          <Tooltip
            formatter={(v) => `${v} min`}
            labelFormatter={(_l, payload) =>
              payload && payload[0] ? String(payload[0].payload.full) : ""
            }
          />
          <Bar dataKey="delay" radius={[0, 4, 4, 0]}>
            {rows.map((r) => (
              <Cell key={r.stop} fill={colorFor(r.delay)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
