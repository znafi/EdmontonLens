"use client";

import { useEffect, useRef, useState } from "react";
import { client } from "@/lib/api";
import type { AgentResponse } from "@/types";

interface Message {
  role: "user" | "bot";
  text: string;
  sql?: string;
  rows?: Record<string, unknown>[];
}

const EXAMPLES = [
  "Which bus is always late on Monday mornings?",
  "Does Glenora have more parks than Bonnie Doon?",
  "When does recycling get picked up in Highlands?",
  "Which 5 stops have the worst average delays?",
];

export default function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(question: string) {
    const q = question.trim();
    if (!q || loading) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setLoading(true);
    try {
      const res: AgentResponse = await client.agentQuery(q);
      setMessages((m) => [
        ...m,
        { role: "bot", text: res.answer, sql: res.sql_used, rows: res.rows },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "bot", text: "Something went wrong reaching the database. Try refreshing." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] flex-col rounded-xl border border-slate-200 bg-white">
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div className="grid h-full place-items-center text-center text-slate-400">
            <div>
              <p className="text-lg font-medium">Ask anything about Edmonton.</p>
              <p className="text-sm">Try one of the questions below to get started.</p>
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={
                m.role === "user"
                  ? "max-w-[80%] rounded-2xl rounded-br-sm bg-brand px-4 py-2 text-white"
                  : "max-w-[85%] rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-3 text-slate-800"
              }
            >
              <p className="whitespace-pre-wrap text-sm">{m.text}</p>
              {m.rows && m.rows.length > 0 && <ResultTable rows={m.rows} />}
              {m.sql && <SqlBlock sql={m.sql} />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="flex gap-1 rounded-2xl bg-slate-100 px-4 py-3">
              <Dot /> <Dot delay="150ms" /> <Dot delay="300ms" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="border-t border-slate-200 p-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => send(ex)}
              disabled={loading}
              className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-brand hover:text-brand disabled:opacity-50"
            >
              {ex}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='Try: "Which bus route had the most delays last week?"'
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}

function Dot({ delay = "0ms" }: { delay?: string }) {
  return (
    <span
      className="h-2 w-2 animate-bounce rounded-full bg-slate-400"
      style={{ animationDelay: delay }}
    />
  );
}

function SqlBlock({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-xs font-medium text-brand underline"
      >
        {open ? "Hide the SQL" : "See the SQL it ran"}
      </button>
      {open && (
        <pre className="mt-2 overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
          {sql}
        </pre>
      )}
    </div>
  );
}

function prettyHeader(col: string): string {
  return col
    .replace(/_/g, " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  let num: number | null = null;
  if (typeof value === "number") num = value;
  else if (typeof value === "string" && value.trim() !== "" && !isNaN(Number(value))) {
    num = Number(value);
  }
  if (num !== null && !Number.isInteger(num)) {
    return String(Number(num.toFixed(2)));
  }
  return String(value);
}

function ResultTable({ rows }: { rows: Record<string, unknown>[] }) {
  const cols = Object.keys(rows[0] ?? {});
  return (
    <div className="mt-3 max-h-60 overflow-auto rounded-md border border-slate-200">
      <table className="w-full text-left text-xs">
        <thead className="bg-slate-50">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-2 py-1 font-semibold text-slate-600">
                {prettyHeader(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 25).map((row, i) => (
            <tr key={i} className="border-t border-slate-100">
              {cols.map((c) => (
                <td key={c} className="px-2 py-1 text-slate-700">
                  {formatCell(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
