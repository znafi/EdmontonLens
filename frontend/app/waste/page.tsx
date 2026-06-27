"use client";

import { useEffect, useMemo, useState } from "react";
import { client, clsx } from "@/lib/api";
import type { DiversionRate, Neighbourhood, WasteSchedule } from "@/types";

const TYPE_COLORS: Record<string, string> = {
  garbage: "bg-slate-100 text-slate-700",
  recycling: "bg-blue-100 text-blue-700",
  organics: "bg-green-100 text-green-700",
};

const DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function WastePage() {
  const [schedules, setSchedules] = useState<WasteSchedule[]>([]);
  const [neighbourhoods, setNeighbourhoods] = useState<Neighbourhood[]>([]);
  const [diversion, setDiversion] = useState<DiversionRate | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([client.waste(), client.neighbourhoods(), client.diversion()])
      .then(([w, n, d]) => {
        setSchedules(w);
        setNeighbourhoods(n);
        setDiversion(d);
      })
      .catch(() => {
        setSchedules([]);
        setNeighbourhoods([]);
        setDiversion(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const nameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const n of neighbourhoods) {
      map.set(n.neighbourhood_id, n.neighbourhood_name ?? n.neighbourhood_id);
    }
    return map;
  }, [neighbourhoods]);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return schedules
      .map((s) => ({
        ...s,
        neighbourhood_name: nameById.get(s.neighbourhood_id ?? "") ?? s.neighbourhood_id ?? "",
      }))
      .filter((s) => {
        if (typeFilter !== "all" && s.waste_type !== typeFilter) return false;
        if (!q) return true;
        const hay = `${s.neighbourhood_name} ${s.pickup_day} ${s.waste_type}`.toLowerCase();
        return hay.includes(q);
      })
      .sort((a, b) => {
        const nameCmp = (a.neighbourhood_name ?? "").localeCompare(b.neighbourhood_name ?? "");
        if (nameCmp !== 0) return nameCmp;
        return DAY_ORDER.indexOf(a.pickup_day ?? "") - DAY_ORDER.indexOf(b.pickup_day ?? "");
      });
  }, [schedules, nameById, search, typeFilter]);

  const types = useMemo(() => {
    const set = new Set<string>();
    schedules.forEach((s) => s.waste_type && set.add(s.waste_type));
    return Array.from(set).sort();
  }, [schedules]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Waste</h1>
        <p className="text-sm text-slate-500">
          Pickup days for every neighbourhood. Search by name or filter by what gets collected.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard
          label="Pickup routes loaded"
          value={schedules.length}
          hint="across all neighbourhoods"
        />
        <KpiCard
          label="Recycling and organics share"
          value={diversion ? `${Math.round(diversion.diversion_rate * 100)}%` : "-"}
          hint={
            diversion
              ? `${diversion.recycling_organics_streams} of ${diversion.total_streams} streams`
              : "loading..."
          }
        />
        <KpiCard
          label="Neighbourhoods covered"
          value={new Set(schedules.map((s) => s.neighbourhood_id)).size}
          hint="with at least one scheduled pickup"
        />
      </div>

      <div className="card">
        <div className="mb-4 flex flex-wrap gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder='Try: "Glenora" or "Wednesday"'
            className="min-w-[220px] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
          />
          <div className="flex flex-wrap gap-1">
            <FilterChip
              label="All"
              active={typeFilter === "all"}
              onClick={() => setTypeFilter("all")}
            />
            {types.map((t) => (
              <FilterChip
                key={t}
                label={t}
                active={typeFilter === t}
                onClick={() => setTypeFilter(t)}
              />
            ))}
          </div>
        </div>

        {loading ? (
          <p className="py-12 text-center text-slate-400">Grabbing pickup schedules...</p>
        ) : rows.length === 0 ? (
          <p className="py-12 text-center text-slate-400">
            Nothing matched that. Try a different neighbourhood or clear the filter.
          </p>
        ) : (
          <div className="max-h-[60vh] overflow-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-50">
                <tr className="text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2 font-semibold">Neighbourhood</th>
                  <th className="px-4 py-2 font-semibold">Pickup day</th>
                  <th className="px-4 py-2 font-semibold">What&apos;s collected</th>
                  <th className="px-4 py-2 font-semibold">Cycle</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.schedule_id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-2 text-slate-800">{s.neighbourhood_name}</td>
                    <td className="px-4 py-2 text-slate-700">{s.pickup_day ?? "-"}</td>
                    <td className="px-4 py-2">
                      <span
                        className={clsx(
                          "rounded-full px-2 py-0.5 text-xs font-medium",
                          TYPE_COLORS[s.waste_type ?? ""] ?? "bg-slate-100 text-slate-700",
                        )}
                      >
                        {s.waste_type ?? "unknown"}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-600">
                      {s.biweekly ? "Every other week" : "Weekly"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="card">
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "rounded-full border px-3 py-1 text-xs font-medium transition",
        active
          ? "border-brand bg-brand text-white"
          : "border-slate-200 text-slate-600 hover:border-brand hover:text-brand",
      )}
    >
      {label}
    </button>
  );
}
