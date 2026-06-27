import { NextRequest, NextResponse } from "next/server";

// Allow up to 60s so the request can wait through a free-tier backend cold start.
export const maxDuration = 60;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${API_BASE}/api/agent/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { answer: "The assistant is unavailable right now.", sql_used: "", rows: [] },
      { status: 502 },
    );
  }
}
