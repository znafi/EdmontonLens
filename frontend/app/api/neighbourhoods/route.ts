import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const kind = req.nextUrl.searchParams.get("kind") ?? "list";
  const id = req.nextUrl.searchParams.get("id") ?? "";
  let path = "/api/neighbourhoods/list";

  if (kind === "geojson") {
    path = "/api/neighbourhoods/geojson";
  } else if (kind === "snapshot" && id) {
    path = `/api/neighbourhoods/${id}/snapshot`;
  } else if (kind === "trend" && id) {
    path = `/api/neighbourhoods/${id}/trend`;
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
  }
}
