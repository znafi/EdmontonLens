import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const kind = req.nextUrl.searchParams.get("kind") ?? "performance";
  let path = "/api/transit/performance";

  if (kind === "delays") {
    const limit = req.nextUrl.searchParams.get("limit") ?? "10";
    path = `/api/transit/delays?limit=${limit}`;
  } else if (kind === "routes") {
    path = "/api/transit/routes";
  } else if (kind === "predict") {
    const routeId = req.nextUrl.searchParams.get("route_id") ?? "";
    const hour = req.nextUrl.searchParams.get("hour") ?? "8";
    const day = req.nextUrl.searchParams.get("day") ?? "0";
    path = `/api/transit/predict?route_id=${encodeURIComponent(routeId)}&hour=${hour}&day=${day}`;
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
  }
}
