import Link from "next/link";
import { Bus, MessageSquare, MapPin, Trash2 } from "lucide-react";

const FEATURES = [
  {
    href: "/transit",
    title: "Transit",
    description:
      "See which routes are running late today, which stops are worst for delays, and what the model thinks will happen tomorrow morning.",
    icon: Bus,
    accent: "bg-blue-50 text-blue-600",
  },
  {
    href: "/waste",
    title: "Waste",
    description:
      "Find out when garbage, recycling, and organics get picked up in any neighbourhood. Searchable, no PDF schedules needed.",
    icon: Trash2,
    accent: "bg-amber-50 text-amber-600",
  },
  {
    href: "/ask",
    title: "Ask",
    description:
      "Type a question in plain English. It'll write the SQL, run it, and tell you what it found. No filters, no dropdowns.",
    icon: MessageSquare,
    accent: "bg-emerald-50 text-emerald-600",
  },
  {
    href: "/neighbourhood",
    title: "Map",
    description:
      "Click any neighbourhood on the map. You'll get a breakdown of its transit stops, parks, waste pickup schedule, and a score out of 10.",
    icon: MapPin,
    accent: "bg-orange-50 text-orange-600",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="rounded-2xl bg-gradient-to-br from-brand-dark to-brand px-8 py-16 text-white">
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-blue-200">
          Edmonton open data
        </p>
        <h1 className="max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">
          What's actually going on in your city.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-blue-100">
          EdmontonLens pulls the city's open data on transit, parks, and waste
          into one place. You can read charts, ask questions in plain English,
          or browse a neighbourhood-by-neighbourhood breakdown.
        </p>
        <div className="mt-8 flex gap-3">
          <Link
            href="/transit"
            className="rounded-lg bg-white px-5 py-3 font-semibold text-brand transition hover:bg-blue-50"
          >
            Check transit
          </Link>
          <Link
            href="/ask"
            className="rounded-lg border border-white/40 px-5 py-3 font-semibold text-white transition hover:bg-white/10"
          >
            Ask a question
          </Link>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => {
          const Icon = f.icon;
          return (
            <Link
              key={f.href}
              href={f.href}
              className="group rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-1 hover:shadow-lg"
            >
              <span className={`grid h-12 w-12 place-items-center rounded-xl ${f.accent}`}>
                <Icon className="h-6 w-6" />
              </span>
              <h2 className="mt-4 text-xl font-semibold text-slate-900">{f.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{f.description}</p>
              <span className="mt-4 inline-block text-sm font-semibold text-brand group-hover:underline">
                Go there
              </span>
            </Link>
          );
        })}
      </section>
    </div>
  );
}
