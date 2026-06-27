import { NextRequest, NextResponse } from "next/server";

// Allow up to 60s so the request can wait through a free-tier backend cold start.
export const maxDuration = 60;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const neighbourhoodId = req.nextUrl.searchParams.get("neighbourhood_id");
  const path = neighbourhoodId
    ? `/api/parks/neighbourhood/${neighbourhoodId}`
    : "/api/parks/list";
  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
  }
}
