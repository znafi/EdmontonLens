// Typed fetch wrappers for the EdmontonLens backend.
// Requests go through the Next.js route handlers under /app/api which proxy
// to FastAPI, keeping the backend URL server-side.

import type {
  AgentResponse,
  DiversionRate,
  GeoJSONFeatureCollection,
  Neighbourhood,
  NeighbourhoodSnapshot,
  Park,
  PerformancePoint,
  StopDelay,
  TransitRoute,
  TrendPoint,
  WasteSchedule,
} from "@/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Request to ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

// --- Direct backend calls (used by server components / route handlers) ---
export const backend = {
  routes: () => getJSON<TransitRoute[]>(`${API_BASE}/api/transit/routes`),
  performance: () => getJSON<PerformancePoint[]>(`${API_BASE}/api/transit/performance`),
  topDelays: (limit = 10) =>
    getJSON<StopDelay[]>(`${API_BASE}/api/transit/delays?limit=${limit}`),
  predict: (routeId: string, hour = 8, day = 0) =>
    getJSON<{ route_id: string; delay_probability: number }>(
      `${API_BASE}/api/transit/predict?route_id=${encodeURIComponent(routeId)}&hour=${hour}&day=${day}`,
    ),
  parks: () => getJSON<Park[]>(`${API_BASE}/api/parks/list`),
  wasteSchedule: () => getJSON<WasteSchedule[]>(`${API_BASE}/api/waste/schedule`),
  diversionRate: () => getJSON<DiversionRate>(`${API_BASE}/api/waste/diversion-rate`),
  neighbourhoods: () => getJSON<Neighbourhood[]>(`${API_BASE}/api/neighbourhoods/list`),
  geojson: () => getJSON<GeoJSONFeatureCollection>(`${API_BASE}/api/neighbourhoods/geojson`),
  snapshot: (id: string) =>
    getJSON<NeighbourhoodSnapshot>(`${API_BASE}/api/neighbourhoods/${id}/snapshot`),
  trend: (id: string) =>
    getJSON<TrendPoint[]>(`${API_BASE}/api/neighbourhoods/${id}/trend`),
  agentQuery: (question: string) =>
    getJSON<AgentResponse>(`${API_BASE}/api/agent/query`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};

// --- Client-side calls (used by client components via Next.js proxy routes) ---
export const client = {
  transit: () => getJSON<PerformancePoint[]>(`/api/transit`),
  delays: () => getJSON<StopDelay[]>(`/api/transit?kind=delays`),
  routes: () => getJSON<TransitRoute[]>(`/api/transit?kind=routes`),
  predict: (routeId: string, hour = 8, day = 0) =>
    getJSON<{ route_id: string; delay_probability: number }>(
      `/api/transit?kind=predict&route_id=${encodeURIComponent(routeId)}&hour=${hour}&day=${day}`,
    ),
  parks: () => getJSON<Park[]>(`/api/parks`),
  waste: () => getJSON<WasteSchedule[]>(`/api/waste`),
  neighbourhoods: () => getJSON<Neighbourhood[]>(`/api/neighbourhoods`),
  geojson: () => getJSON<GeoJSONFeatureCollection>(`/api/neighbourhoods?kind=geojson`),
  snapshot: (id: string) =>
    getJSON<NeighbourhoodSnapshot>(`/api/neighbourhoods?kind=snapshot&id=${id}`),
  trend: (id: string) =>
    getJSON<TrendPoint[]>(`/api/neighbourhoods?kind=trend&id=${id}`),
  agentQuery: (question: string) =>
    getJSON<AgentResponse>(`/api/agent`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};

export function clsx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
